"""Windows desktop entry point for the existing local editor and export service."""

import os
import json
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn

from clipper.server import create_app


STARTUP_HTML = """<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YouTube Clipper</title><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#101728;
color:#f3f5ff;font:15px 'Segoe UI',sans-serif}main{text-align:center}
h1{font-size:24px;margin:0 0 12px}p{margin:0;color:#bbc5dc}
.dot{display:inline-block;width:8px;height:8px;margin-right:8px;border-radius:50%;background:#8b82ea}
</style><main><h1>YouTube Clipper</h1><p><span class="dot"></span>Uruchamianie aplikacji…</p></main></html>"""

STARTUP_ERROR_HTML = """<!doctype html><html lang="pl"><meta charset="utf-8">
<title>YouTube Clipper</title><style>body{margin:0;min-height:100vh;display:grid;
place-items:center;background:#101728;color:#f3f5ff;font:15px 'Segoe UI',sans-serif}
main{text-align:center;max-width:36rem;padding:2rem}p{color:#bbc5dc}</style>
<main><h1>Nie udało się uruchomić aplikacji</h1>
<p>Zamknij to okno i uruchom YouTube Clipper ponownie.</p></main></html>"""


def app_data_dir():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "YouTube Clipper"


class DesktopApi:
    def __init__(self, queue, settings_path, window=None):
        self._queue = queue
        self._settings_path = settings_path
        self._window = window

    def choose_output_folder(self):
        import webview

        selection = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=str(self._queue.root))
        if not selection:
            return {"changed": False, "path": str(self._queue.root)}
        selected = Path(selection[0]).resolve()
        if not selected.is_dir():
            raise ValueError("Wybrany folder nie istnieje lub jest niedostępny.")
        previous = self._queue.root
        self._queue.change_root(selected)
        try:
            self._settings_path.parent.mkdir(parents=True, exist_ok=True)
            staged = self._settings_path.with_suffix(".tmp")
            staged.write_text(json.dumps({"clips_dir": str(selected)}, ensure_ascii=False), encoding="utf-8")
            staged.replace(self._settings_path)
        except OSError:
            self._queue.change_root(previous)
            raise
        return {"changed": selected != previous, "path": str(selected)}


def configure_runtime():
    # The installer directory is replaced on updates; clips belong to the user.
    app_data = app_data_dir().parent
    old_clips = app_data / "Kadr" / "clips"
    clips = app_data / "YouTube Clipper" / "clips"
    settings = app_data / "YouTube Clipper" / "settings.json"
    if settings.is_file():
        try:
            saved = Path(json.loads(settings.read_text(encoding="utf-8"))["clips_dir"])
            if saved.is_absolute() and saved.is_dir():
                clips = saved
        except (OSError, ValueError, KeyError, TypeError):
            pass
    if old_clips.is_dir():
        clips.parent.mkdir(parents=True, exist_ok=True)
        if not clips.exists():
            old_clips.rename(clips)
        else:
            for manifest in old_clips.glob("*.json"):
                try:
                    filename = json.loads(manifest.read_text(encoding="utf-8")).get("filename")
                except (OSError, ValueError):
                    continue
                if not filename or Path(filename).name != filename:
                    continue
                old_video = old_clips / filename
                new_video = clips / filename
                new_manifest = clips / manifest.name
                if not old_video.is_file() or new_video.exists() or new_manifest.exists():
                    continue
                old_video.replace(new_video)
                try:
                    manifest.replace(new_manifest)
                except OSError:
                    new_video.replace(old_video)
                    raise
    os.environ["CLIPS_DIR"] = str(clips)
    os.environ.pop("WORKER_SECRET", None)
    if getattr(sys, "frozen", False):
        tools = Path(sys._MEIPASS) / "tools"
        os.environ["PATH"] = str(tools) + os.pathsep + os.environ.get("PATH", "")


def show_when_ready(window, url, thread):
    for _ in range(100):
        if not thread.is_alive():
            window.load_html(STARTUP_ERROR_HTML)
            return
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=0.5):
                window.load_url(url)
                return
        except OSError:
            time.sleep(0.1)
    window.load_html(STARTUP_ERROR_HTML)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--yt-dlp":
        import yt_dlp

        yt_dlp.main(sys.argv[2:])
        return

    configure_runtime()
    import webview

    # Each launch gets its own loopback port, even if the older browser version
    # is still running on 8765.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    app = create_app(desktop_mode=True)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        bridge = DesktopApi(app.state.queue, app_data_dir() / "settings.json")
        bridge._window = webview.create_window("YouTube Clipper", html=STARTUP_HTML, js_api=bridge,
                                              width=1280, height=850, min_size=(850, 600),
                                              background_color="#101728")
        webview.start(show_when_ready, (bridge._window, url, thread), gui="edgechromium")
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()


if __name__ == "__main__":
    main()
