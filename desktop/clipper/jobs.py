"""One export at a time, cancellable subprocesses, persistent finished clips."""

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .media import CREATE_FLAGS, MediaError, export_command, friendly_error, public_info


def export_timeout_seconds(quality):
    if quality >= 2160:
        return 3600
    if quality >= 1440:
        return 1800
    return 600


class ExportQueue:
    def __init__(self, root: Path, source):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.temp = root / ".work"
        self.temp.mkdir(exist_ok=True)
        self.source = source
        self.lock = threading.RLock()
        self.jobs = {}
        self.processes = {}
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="export")
        for entry in root.glob("*.json"):
            try:
                job = json.loads(entry.read_text(encoding="utf-8"))
                if job.get("id") != entry.stem or not re.fullmatch(r"[0-9a-f]{32}", entry.stem):
                    continue
                filename = job["filename"]
                if Path(filename).name == filename and (root / filename).is_file():
                    self.jobs[job["id"]] = job
            except (ValueError, KeyError, OSError):
                continue

    def update(self, job_id, **changes):
        with self.lock:
            self.jobs[job_id].update(changes)

    def list(self):
        with self.lock:
            return [dict(job) for job in sorted(self.jobs.values(), key=lambda j: j["created"], reverse=True)]

    def get(self, job_id):
        with self.lock:
            return dict(self.jobs[job_id])

    def change_root(self, root: Path):
        root = root.resolve()
        with self.lock:
            if root == self.root.resolve():
                return
            if any(job["status"] in {"queued", "resolving", "exporting"} for job in self.jobs.values()):
                raise ValueError("Poczekaj na zakończenie eksportów przed zmianą folderu.")
            root.mkdir(parents=True, exist_ok=True)
            files = []
            for job in self.jobs.values():
                if job["status"] == "done" and job.get("filename"):
                    files.extend((self.root / job["filename"], self.root / f"{job['id']}.json"))
            if any((root / file.name).exists() for file in files):
                raise FileExistsError("W wybranym folderze istnieje już plik o tej samej nazwie.")
            moved = []
            try:
                for file in files:
                    if file.is_file():
                        shutil.move(str(file), str(root / file.name))
                        moved.append(file)
                (root / ".work").mkdir(exist_ok=True)
            except Exception:
                for file in reversed(moved):
                    shutil.move(str(root / file.name), str(file))
                raise
            self.root = root
            self.temp = root / ".work"

    def delete(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job["status"] != "done" or not job.get("filename"):
                raise ValueError("Można usunąć tylko gotowy klip.")
            filename = job["filename"]
            if Path(filename).name != filename:
                raise ValueError("Nieprawidłowa nazwa pliku klipu.")
            (self.root / filename).unlink(missing_ok=True)
            (self.root / f"{job_id}.json").unlink(missing_ok=True)
            del self.jobs[job_id]

    def enqueue(self, url, start, end, mute_audio=False, quality=1080):
        with self.lock:
            if sum(j["status"] in {"queued", "resolving", "exporting"} for j in self.jobs.values()) >= 5:
                raise ValueError("Kolejka jest pełna. Poczekaj na ukończenie któregoś z klipów.")
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = {"id": job_id, "url": url, "start": start, "end": end,
                                 "status": "queued", "progress": 0, "title": "Nowy fragment",
                                 "created": datetime.now(timezone.utc).isoformat(), "filename": None,
                                 "message": "W kolejce", "duration": round(end-start, 3),
                                 "mute_audio": mute_audio, "quality": quality}
            self.pool.submit(self.run, job_id)
            return dict(self.jobs[job_id])

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job["status"] not in {"queued", "resolving", "exporting"}:
                return dict(job)
            job.update(status="cancelled", message="Anulowano eksport")
            process = self.processes.get(job_id)
            if process and process.poll() is None:
                process.terminate()
            return dict(job)

    def cancelled(self, job_id):
        return self.get(job_id)["status"] == "cancelled"

    def run(self, job_id):
        temporary = self.temp / f"{job_id}.mp4"
        errors = self.temp / f"{job_id}.log"
        process = None
        timer = None
        expired = threading.Event()
        try:
            with self.lock:
                if self.cancelled(job_id):
                    return
                self.update(job_id, status="resolving", message="Przygotowuję film…")
            job = self.get(job_id)
            info = self.source.extract(job["url"], False, job.get("quality", 1080))
            if self.cancelled(job_id):
                return
            self.update(job_id, title=info.get("title", "Film"))
            command = export_command(info, job["start"], job["end"], temporary,
                                     mute_audio=job.get("mute_audio", False),
                                     quality=job.get("quality", 1080))
            with errors.open("w", encoding="utf-8") as stderr:
                with self.lock:
                    if self.cancelled(job_id):
                        return
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=stderr,
                                               text=True, encoding="utf-8", errors="replace",
                                               creationflags=CREATE_FLAGS)
                    self.processes[job_id] = process
                    self.update(job_id, status="exporting", message="Pobieram i wycinam fragment…")

                def timeout():
                    expired.set()
                    if process.poll() is None:
                        process.kill()

                timer = threading.Timer(export_timeout_seconds(job.get("quality", 1080)), timeout)
                timer.daemon = True
                timer.start()
                for line in process.stdout:
                    if self.cancelled(job_id):
                        break
                    if line.startswith("out_time_us="):
                        try:
                            seconds = int(line.split("=", 1)[1]) / 1_000_000
                            self.update(job_id, progress=max(0, min(99, round(seconds / job["duration"] * 100))))
                        except ValueError:
                            pass
                process.wait()
            if self.cancelled(job_id):
                return
            if expired.is_set():
                raise MediaError("Eksport trwał zbyt długo. Spróbuj krótszego fragmentu lub ponów pobieranie.")
            if process.returncode or not temporary.is_file() or temporary.stat().st_size == 0:
                raise MediaError(friendly_error(errors.read_text(encoding="utf-8", errors="replace")))
            title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", info.get("title", "Film"))[:90].strip(" .") or "Film"
            filename = f"{title} [{job['start']:.2f}-{job['end']:.2f}] {job_id[:6]}.mp4"
            with self.lock:
                if self.cancelled(job_id):
                    return
                temporary.replace(self.root / filename)
                self.update(job_id, status="done", progress=100, filename=filename,
                            message="Zapisano MP4", size=(self.root / filename).stat().st_size)
                manifest = self.root / f"{job_id}.json"
                stage = self.temp / f"{job_id}.json"
                stage.write_text(json.dumps(self.get(job_id), ensure_ascii=False, indent=2), encoding="utf-8")
                stage.replace(manifest)
        except (MediaError, ValueError) as exc:
            if not self.cancelled(job_id):
                self.update(job_id, status="error", message=str(exc))
        except Exception:
            if not self.cancelled(job_id):
                self.update(job_id, status="error", message="Nie udało się zapisać pliku. Sprawdź wolne miejsce i ponów eksport.")
        finally:
            if timer:
                timer.cancel()
            if process and process.poll() is None:
                process.kill()
                process.wait()
            if process and process.stdout:
                process.stdout.close()
            with self.lock:
                self.processes.pop(job_id, None)
            temporary.unlink(missing_ok=True)
            errors.unlink(missing_ok=True)

    def shutdown(self):
        for job in self.list():
            self.cancel(job["id"])
        self.pool.shutdown(wait=False, cancel_futures=True)
