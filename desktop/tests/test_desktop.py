import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from desktop import DesktopApi, configure_runtime, show_when_ready
from clipper.server import create_app


def test_desktop_renames_existing_clip_directory(tmp_path, monkeypatch):
    old = tmp_path / "Kadr" / "clips"
    old.mkdir(parents=True)
    (old / "sample.mp4").write_bytes(b"mp4")
    (old / "abc.json").write_text(json.dumps({"filename": "sample.mp4"}), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("desktop.app_data_dir", lambda: tmp_path / "YouTube Clipper")
    monkeypatch.setenv("CLIPS_DIR", "")
    monkeypatch.setenv("WORKER_SECRET", "must-not-enable-cloud-mode")

    configure_runtime()

    new = tmp_path / "YouTube Clipper" / "clips"
    assert os.environ["CLIPS_DIR"] == str(new)
    assert (new / "sample.mp4").read_bytes() == b"mp4"
    assert (new / "abc.json").is_file()
    assert not old.exists()
    assert "WORKER_SECRET" not in os.environ


def test_desktop_merges_older_clips_without_overwriting_newer_ones(tmp_path, monkeypatch):
    old = tmp_path / "Kadr" / "clips"
    new = tmp_path / "YouTube Clipper" / "clips"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    for root, content in [(old, b"old"), (new, b"new")]:
        (root / "same.mp4").write_bytes(content)
        (root / "same.json").write_text(json.dumps({"filename": "same.mp4"}), encoding="utf-8")
    (old / "other.mp4").write_bytes(b"other")
    (old / "other.json").write_text(json.dumps({"filename": "other.mp4"}), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("desktop.app_data_dir", lambda: tmp_path / "YouTube Clipper")
    monkeypatch.setenv("CLIPS_DIR", "")

    configure_runtime()

    assert (new / "same.mp4").read_bytes() == b"new"
    assert (old / "same.mp4").read_bytes() == b"old"
    assert (new / "other.mp4").read_bytes() == b"other"
    assert (new / "other.json").is_file()


def test_desktop_restores_selected_clip_folder(tmp_path, monkeypatch):
    selected = tmp_path / "My videos"
    selected.mkdir()
    settings = tmp_path / "YouTube Clipper" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"clips_dir": str(selected)}), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("desktop.app_data_dir", lambda: tmp_path / "YouTube Clipper")

    configure_runtime()

    assert os.environ["CLIPS_DIR"] == str(selected)


def test_folder_picker_persists_choice_and_moves_existing_clips(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    job_id = "e" * 32
    (old / "sample.mp4").write_bytes(b"video")
    (old / f"{job_id}.json").write_text(json.dumps({
        "id": job_id, "filename": "sample.mp4", "status": "done",
        "created": "2026-01-01T00:00:00Z", "title": "sample",
    }), encoding="utf-8")
    queue = create_app(old).state.queue
    class Window:
        def create_file_dialog(self, *_args, **_kwargs):
            return (str(new),)
    settings = tmp_path / "settings" / "settings.json"
    picker = DesktopApi(queue, settings, Window())

    assert picker.choose_output_folder() == {"changed": True, "path": str(new)}
    assert json.loads(settings.read_text(encoding="utf-8"))["clips_dir"] == str(new)
    assert (new / "sample.mp4").read_bytes() == b"video"


def test_startup_window_loads_editor_when_service_is_ready(monkeypatch):
    class Window:
        loaded_url = None
        def load_url(self, url):
            self.loaded_url = url
    class Thread:
        def is_alive(self):
            return True
    monkeypatch.setattr("desktop.urllib.request.urlopen", lambda *_args, **_kwargs: nullcontext())
    window = Window()

    show_when_ready(window, "http://127.0.0.1:12345", Thread())

    assert window.loaded_url == "http://127.0.0.1:12345"


def test_startup_window_shows_failure_when_service_exits():
    class Window:
        error_html = None
        def load_html(self, html):
            self.error_html = html
    class Thread:
        def is_alive(self):
            return False
    window = Window()

    show_when_ready(window, "http://127.0.0.1:12345", Thread())

    assert "Nie udało się uruchomić" in window.error_html


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_native_app_data_directory(platform, tmp_path, monkeypatch):
    from desktop import app_data_dir
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    expected = tmp_path / "Library" / "Application Support" if platform == "darwin" else tmp_path / "Local"
    assert app_data_dir() == expected / "YouTube Clipper"


def test_macos_open_folder_passes_path_as_single_argument(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("clipper.server.sys.platform", "darwin")
    monkeypatch.setattr("clipper.server.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    app = create_app(tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/folder", headers={"X-Clipper-Token": app.state.token})
    assert response.status_code == 200
    assert calls == [((["/usr/bin/open", str(tmp_path)],), {"check": True, "timeout": 10})]
