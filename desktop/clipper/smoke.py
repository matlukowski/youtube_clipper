"""Opt-in installed-app check used on macOS release runners."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path

from .media import export_command


def check_window(window, url, thread):
    report = Path(sys.argv[2])
    result = {"ok": False}
    try:
        for _ in range(120):
            if not thread.is_alive():
                raise RuntimeError("Local service stopped")
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                    health = json.load(response)
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Local service did not start")
        assert health["ready"], health
        window.load_url(url)
        for _ in range(120):
            try:
                loaded = window.evaluate_js(
                    "document.querySelector('script[src]') !== null && "
                    "typeof window.pywebview?.api?.choose_output_folder === 'function'")
                if loaded:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Editor or native Python bridge failed to load")

        def run(command):
            return subprocess.run(command, check=True, capture_output=True, text=True, timeout=90)

        tools = Path(sys._MEIPASS) / "tools"
        for name in ("ffmpeg", "node"):
            assert Path(shutil.which(name)).resolve() == (tools / name).resolve()
        node = run([str(tools / "node"), "--version"]).stdout.strip()
        yt_dlp = run([sys.executable, "--yt-dlp", "--version"]).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="clipper-smoke-") as temp:
            source = Path(temp) / "source.mp4"
            run([str(tools / "ffmpeg"), "-y", "-f", "lavfi", "-i",
                 "testsrc2=size=320x240:rate=25", "-f", "lavfi", "-i",
                 "sine=frequency=440", "-t", "2", "-c:v", "libx264",
                 "-c:a", "aac", str(source)])
            info = {"duration": 2, "url": str(source), "vcodec": "h264", "acodec": "aac"}
            for mute in (False, True):
                output = Path(temp) / f"clip-{mute}.mp4"
                run(export_command(info, 0.4, 1.4, output, mute_audio=mute))
                probe = run([str(tools / "ffmpeg"), "-i", str(output), "-f", "null", "-"])
                assert output.stat().st_size > 1000
                assert ("Audio:" in probe.stderr) == (not mute)
        result = {"ok": True, "health": health, "node": node, "yt_dlp": yt_dlp,
                  "checks": ["native-window", "editor", "python-bridge", "bundled-tools",
                             "export-with-audio", "export-muted"]}
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")
        window.destroy()
