import os
import mimetypes
import secrets
import shutil
import hmac
import hashlib
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.concurrency import run_in_threadpool

from .jobs import ExportQueue
from .media import MediaError, MediaSource, canonical_url, public_info, validate_range

ROOT = Path(__file__).resolve().parent.parent
mimetypes.add_type("application/javascript", ".mjs")


class VideoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def youtube_only(cls, value):
        return canonical_url(value)[1]


class ClipRequest(VideoRequest):
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    mute_audio: bool = False
    quality: Literal[360, 720, 1080, 1440, 2160] = 1080

    @model_validator(mode="after")
    def valid_range(self):
        validate_range(self.start, self.end)
        return self


def create_app(output_dir=None, source=None, worker_secret=None, desktop_mode=False):
    source = source or MediaSource()
    queue = ExportQueue(Path(output_dir) if output_dir else Path(os.environ.get("CLIPS_DIR", ROOT / "clips")), source)
    token = secrets.token_urlsafe(32)
    worker_secret = worker_secret if worker_secret is not None else os.environ.get("WORKER_SECRET")

    def signed_download(job_id: str, expires: str, signature: str) -> bool:
        try:
            valid_time = int(expires) >= time.time() and int(expires) <= time.time() + 300
        except (TypeError, ValueError):
            return False
        expected = hmac.new(worker_secret.encode(), f"{job_id}:{expires}".encode(), hashlib.sha256).hexdigest()
        return valid_time and hmac.compare_digest(expected, signature)

    @asynccontextmanager
    async def lifespan(app):
        yield
        queue.shutdown()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.queue = queue
    app.state.token = token
    public_host = urlsplit(os.environ.get("PUBLIC_WORKER_URL", "")).hostname
    extra_hosts = [host.strip() for host in os.environ.get("WORKER_ALLOWED_HOSTS", "").split(",") if host.strip()]
    allowed_hosts = ["127.0.0.1", "localhost", "testserver", *extra_hosts]
    if public_host:
        allowed_hosts.append(public_host)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if worker_secret and request.url.path.startswith("/api/"):
            public_file = request.method in {"GET", "HEAD"} and request.url.path.endswith("/file")
            signed = public_file and signed_download(request.path_params.get("job_id", request.url.path.split("/")[-2]),
                                                      request.query_params.get("expires"), request.query_params.get("signature", ""))
            if not signed and not secrets.compare_digest(request.headers.get("x-worker-secret", ""), worker_secret):
                return JSONResponse({"detail": "Brak dostępu."}, status_code=403)
        elif not worker_secret and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not secrets.compare_digest(request.headers.get("x-clipper-token", ""), token):
                return JSONResponse({"detail": "Odśwież stronę i spróbuj ponownie."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index():
        if worker_secret:
            raise HTTPException(404, "Nie znaleziono strony.")
        return (ROOT / "web" / "index.html").read_text(encoding="utf-8").replace("__CLIPPER_TOKEN__", token)

    @app.get("/api/health")
    def health():
        return {"app": "youtube-clipper", "ready": bool(shutil.which("ffmpeg") and shutil.which("node")),
                "ffmpeg": bool(shutil.which("ffmpeg")), "node": bool(shutil.which("node")),
                "output_dir": str(queue.root), "features": {"delete_clip": True, "cloud_worker": bool(worker_secret),
                                                              "choose_folder": desktop_mode}}

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.post("/api/video")
    async def video(body: VideoRequest):
        try:
            return public_info(await run_in_threadpool(source.extract, body.url, True))
        except MediaError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/clips")
    def list_clips():
        return queue.list()

    @app.post("/api/clips", status_code=202)
    def create_clip(body: ClipRequest):
        try:
            return queue.enqueue(body.url, body.start, body.end, body.mute_audio, body.quality)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc

    @app.post("/api/clips/{job_id}/cancel")
    def cancel(job_id: str):
        try:
            return queue.cancel(job_id)
        except KeyError as exc:
            raise HTTPException(404, "Nie znaleziono klipu.") from exc

    @app.delete("/api/clips/{job_id}")
    def delete_clip(job_id: str):
        try:
            queue.delete(job_id)
            return {"deleted": True}
        except KeyError as exc:
            raise HTTPException(404, "Nie znaleziono klipu.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(500, "Nie można usunąć pliku z dysku. Zamknij otwarty plik i spróbuj ponownie.") from exc

    @app.get("/api/clips/{job_id}/file")
    def download(job_id: str):
        try:
            job = queue.get(job_id)
        except KeyError as exc:
            raise HTTPException(404, "Nie znaleziono klipu.") from exc
        if job["status"] != "done" or not job.get("filename"):
            raise HTTPException(409, "Plik nie jest jeszcze gotowy.")
        path = queue.root / job["filename"]
        if not path.is_file():
            raise HTTPException(404, "Plik został przeniesiony lub usunięty.")
        return FileResponse(path, media_type="video/mp4", filename=job["filename"])

    @app.get("/api/clips/{job_id}/download-link")
    def download_link(job_id: str):
        if not worker_secret:
            raise HTTPException(404, "Link jest dostępny tylko w trybie chmurowym.")
        public_url = os.environ.get("PUBLIC_WORKER_URL", "").rstrip("/")
        if not public_url:
            raise HTTPException(503, "Brak publicznego adresu workera.")
        try:
            job = queue.get(job_id)
        except KeyError as exc:
            raise HTTPException(404, "Nie znaleziono klipu.") from exc
        if job["status"] != "done" or not job.get("filename"):
            raise HTTPException(409, "Plik nie jest jeszcze gotowy.")
        expires = str(int(time.time()) + 300)
        signature = hmac.new(worker_secret.encode(), f"{job_id}:{expires}".encode(), hashlib.sha256).hexdigest()
        return {"url": f"{public_url}/api/clips/{job_id}/file?{urlencode({'expires': expires, 'signature': signature})}"}

    @app.post("/api/folder")
    def open_folder():
        if worker_secret:
            raise HTTPException(409, "Folder klipów jest dostępny tylko w wersji lokalnej.")
        if os.name == "nt":
            os.startfile(str(queue.root))
        return {"path": str(queue.root)}

    if not worker_secret:
        app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
    return app
