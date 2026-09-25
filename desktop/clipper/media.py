"""YouTube metadata and bounded, accurate FFmpeg exports."""

import json
import math
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
MAX_CLIP_SECONDS = 600
MIN_CLIP_SECONDS = 0.1


class MediaError(Exception):
    pass


def canonical_url(value: str) -> tuple[str, str]:
    value = value.strip()
    if not value.startswith(("https://", "http://")):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Wklej zwykły link do filmu na YouTube.")
    host = (parsed.hostname or "").lower()
    parts = parsed.path.strip("/").split("/")
    video_id = None
    if host in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
        video_id = parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
            video_id = parts[1]
    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Podaj link do konkretnego filmu, np. youtube.com/watch?v=…")
    return video_id, f"https://www.youtube.com/watch?v={video_id}"


def validate_range(start: float, end: float, duration: float | None = None):
    if not all(math.isfinite(v) for v in (start, end)) or start < 0:
        raise ValueError("Czas musi być dodatnią, skończoną liczbą.")
    length = end - start
    if length < MIN_CLIP_SECONDS - 1e-8:
        raise ValueError("Koniec musi wypadać co najmniej 0,1 s po początku.")
    if length > MAX_CLIP_SECONDS:
        raise ValueError("Jeden klip może mieć maksymalnie 10 minut.")
    if duration is not None and end > duration + 0.05:
        raise ValueError("Wybrany fragment wykracza poza długość filmu.")


def friendly_error(detail: str) -> str:
    lowered = detail.lower()
    if "sign in" in lowered or "bot" in lowered or "login" in lowered:
        return "YouTube wymaga zalogowania lub weryfikacji. Spróbuj innego publicznego filmu."
    if "private" in lowered or "unavailable" in lowered or "removed" in lowered:
        return "Ten film jest niedostępny lub prywatny. Sprawdź link w YouTube."
    if "403" in lowered or "forbidden" in lowered:
        return "YouTube odrzucił pobieranie. Wczytaj film ponownie; jeśli to nie pomoże, pobierz najnowszą wersję aplikacji."
    if "429" in lowered or "too many" in lowered:
        return "YouTube ograniczył liczbę zapytań. Odczekaj chwilę i spróbuj ponownie."
    if "format" in lowered or "challenge" in lowered:
        return "Nie udało się uzyskać strumienia filmu. Pobierz najnowszą wersję aplikacji i spróbuj ponownie."
    return "Nie udało się pobrać filmu. Sprawdź połączenie i dostępność filmu, a następnie spróbuj ponownie."


class MediaSource:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def extract(self, url: str, refresh: bool = False, quality: int = 1080) -> dict:
        video_id, url = canonical_url(url)
        cache_key = (video_id, quality)
        with self.lock:
            cached = self.cache.get(cache_key)
        if not refresh and cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        if not shutil.which("node"):
            raise MediaError("Brakuje Node.js. Zainstaluj Node.js 22 lub nowszy i uruchom aplikację ponownie.")
        launcher = [sys.executable, "--yt-dlp"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "yt_dlp"]
        command = [*launcher, "--ignore-config", "--no-playlist",
                   "--js-runtimes", "node", "--no-warnings", "--socket-timeout", "20",
                   "--retries", "1", "--extractor-retries", "1", "--skip-download",
                   "--dump-single-json", "-f",
                   f"bv*[height<={quality}]+ba/b[height<={quality}]/bv*+ba/b",
                   "-S", "res,vcodec:h264,acodec:aac", "--", url]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=100, creationflags=CREATE_FLAGS)
        except subprocess.TimeoutExpired as exc:
            raise MediaError("YouTube odpowiada zbyt długo. Spróbuj ponownie.") from exc
        if result.returncode:
            raise MediaError(friendly_error(result.stderr))
        try:
            info = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise MediaError("Otrzymano nieprawidłową odpowiedź z YouTube.") from exc
        if info.get("is_live") or not info.get("duration"):
            raise MediaError("Wybierz zakończony film. Transmisje na żywo nie są jeszcze obsługiwane.")
        with self.lock:
            self.cache[cache_key] = (time.monotonic(), info)
            if len(self.cache) > 24:
                oldest = min(self.cache, key=lambda key: self.cache[key][0])
                del self.cache[oldest]
        return info


def public_info(info: dict) -> dict:
    return {"id": info["id"], "url": f"https://www.youtube.com/watch?v={info['id']}",
            "title": info.get("title", "Film z YouTube"), "duration": info["duration"],
            "channel": info.get("uploader", "YouTube")}


def export_command(info: dict, start: float, end: float, output: Path,
                   mute_audio: bool = False, quality: int = 1080) -> list[str]:
    validate_range(start, end, float(info["duration"]))
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MediaError("Brakuje FFmpeg. Zainstaluj go i uruchom aplikację ponownie.")
    formats = info.get("requested_formats") or [info]
    if mute_audio:
        formats = [stream for stream in formats if stream.get("vcodec", "none") != "none"]
    command = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin", "-y"]
    for stream in formats:
        headers = {**info.get("http_headers", {}), **stream.get("http_headers", {})}
        safe_headers = "".join(f"{k}: {v}\r\n" for k, v in headers.items()
                               if k.lower() in {"user-agent", "referer", "origin"}
                               and "\r" not in str(v) and "\n" not in str(v))
        command += ["-rw_timeout", "20000000", "-ss", f"{start:.3f}"]
        if safe_headers:
            command += ["-headers", safe_headers]
        command += ["-i", stream["url"]]
    video_idx = next((i for i, f in enumerate(formats) if f.get("vcodec", "none") != "none"), None)
    audio_idx = next((i for i, f in enumerate(formats) if f.get("acodec", "none") != "none"), None)
    if video_idx is None:
        raise MediaError("Ten materiał nie ma dostępnego obrazu.")
    command += ["-map", f"{video_idx}:v:0"]
    if audio_idx is not None and not mute_audio:
        command += ["-map", f"{audio_idx}:a:0"]
    # Input seeking plus re-encoding discards preroll instead of cutting at a keyframe.
    command += ["-t", f"{end-start:.3f}", "-vf", f"scale=-2:trunc(min(ih\\,{quality})/2)*2",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    if mute_audio:
        command += ["-an"]
    elif audio_idx is not None:
        command += ["-c:a", "aac", "-b:a", "192k"]
    command += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(output)]
    return command
