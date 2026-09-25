import json
import subprocess
import time
import threading

import pytest
from fastapi.testclient import TestClient

from clipper.media import MediaSource, canonical_url, export_command, validate_range
from clipper.jobs import export_timeout_seconds
from clipper.server import create_app


@pytest.mark.parametrize("url", [
    "https://youtu.be/jNQXAC9IVRw?t=3", "youtube.com/watch?v=jNQXAC9IVRw&list=anything",
    "https://m.youtube.com/shorts/jNQXAC9IVRw", "https://www.youtube.com/embed/jNQXAC9IVRw",
])
def test_canonical_video_urls(url):
    assert canonical_url(url) == ("jNQXAC9IVRw", "https://www.youtube.com/watch?v=jNQXAC9IVRw")


@pytest.mark.parametrize("url", [
    "https://youtube.com.evil.test/watch?v=jNQXAC9IVRw", "http://127.0.0.1/video", "file:///etc/passwd",
    "https://youtube.com/playlist?list=hello", "https://youtube.com@evil.test/watch?v=jNQXAC9IVRw",
    "https://youtube.com:8080/watch?v=jNQXAC9IVRw", "https://youtu.be/invalid",
])
def test_reject_non_video_and_external_urls(url):
    with pytest.raises(ValueError):
        canonical_url(url)


@pytest.mark.parametrize("start,end,duration", [(-1, 2, 20), (3, 2, 20), (0, 601, 900), (5, 21, 20), (0, float('nan'), 20), (0, 0.01, 20)])
def test_invalid_ranges(start, end, duration):
    with pytest.raises(ValueError):
        validate_range(start, end, duration)


def test_tenth_of_a_second_is_valid():
    validate_range(2.2, 2.3, 20)


def test_http_boundaries_and_validation(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.post('/api/clips', json={'url':'https://youtu.be/jNQXAC9IVRw','start':0,'end':3}).status_code == 403
        headers = {'X-Clipper-Token': app.state.token}
        assert client.post('/api/video', json={'url':'http://127.0.0.1'}, headers=headers).status_code == 422
        assert client.post('/api/clips', json={'url':'https://youtu.be/jNQXAC9IVRw','start':3,'end':2}, headers=headers).status_code == 422
        assert client.get('/api/clips/missing/file').status_code == 404
        assert client.get('/', headers={'Host':'evil.test'}).status_code == 400
        assert app.state.token in client.get('/').text
        assert client.get('/api/health').json()['features']['delete_clip'] is True
        for path in ['/static/app.js','/static/core.mjs']:
            assert client.get(path).headers['content-type'].startswith(('text/javascript','application/javascript'))


@pytest.fixture
def sample_source(tmp_path):
    source = tmp_path / 'synthetic.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=duration=5:size=160x90:rate=30',
                    '-f','lavfi','-i','sine=frequency=440:duration=5','-c:v','libx264','-g','90',
                    '-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(source)], check=True)
    return {'id':'jNQXAC9IVRw','title':'Synthetic integration fixture','duration':5,
            'vcodec':'h264','acodec':'aac','url':str(source)}


def test_actual_ffmpeg_precise_cut_with_audio(sample_source, tmp_path):
    output = tmp_path / 'excerpt.mp4'
    result = subprocess.run(export_command(sample_source, 1.23, 3.73, output), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)],capture_output=True,text=True,check=True)
    probe = json.loads(result.stdout)
    assert abs(float(probe['format']['duration']) - 2.5) < 0.1
    assert {s['codec_name'] for s in probe['streams']} == {'h264','aac'}
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    assert abs(float(video['start_time'])) < .04


def test_higher_quality_never_upscales_source(sample_source, tmp_path):
    output = tmp_path / 'unchanged-resolution.mp4'
    subprocess.run(export_command(sample_source, 0, 1, output, quality=2160),
                   capture_output=True, text=True, check=True)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-show_entries', 'stream=height', '-of', 'json', str(output)],
                           capture_output=True, text=True, check=True)
    assert json.loads(probe.stdout)['streams'][0]['height'] == 90


def test_media_source_selects_and_caches_each_quality(monkeypatch):
    commands = []
    def fake_run(command, **_kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps({
            'id': 'jNQXAC9IVRw', 'duration': 10,
        }), '')
    monkeypatch.setattr('clipper.media.shutil.which', lambda _name: 'node')
    monkeypatch.setattr('clipper.media.subprocess.run', fake_run)
    source = MediaSource()
    url = 'https://youtu.be/jNQXAC9IVRw'

    source.extract(url, quality=2160)
    source.extract(url, quality=360)
    source.extract(url, quality=2160)

    assert len(commands) == 2
    assert 'height<=2160' in commands[0][commands[0].index('-f') + 1]
    assert 'height<=360' in commands[1][commands[1].index('-f') + 1]
    assert commands[0][commands[0].index('-S') + 1].startswith('res,')


def test_higher_quality_allows_more_encoding_time():
    assert export_timeout_seconds(1080) == 600
    assert export_timeout_seconds(1440) == 1800
    assert export_timeout_seconds(2160) == 3600


def test_queue_export_download_and_restore(sample_source, tmp_path):
    class Source:
        def extract(self, *_args):
            return sample_source
    root = tmp_path/'clips'
    app = create_app(root, Source())
    with TestClient(app) as client:
        response = client.post('/api/clips',json={'url':'https://youtu.be/jNQXAC9IVRw','start':1.23,'end':3.73},headers={'X-Clipper-Token':app.state.token})
        assert response.status_code == 202
        job_id = response.json()['id']
        deadline = time.monotonic()+15
        while time.monotonic()<deadline:
            job = app.state.queue.get(job_id)
            if job['status'] in {'done','error'}:
                break
            time.sleep(.05)
        assert job['status']=='done', job
        assert job['mute_audio'] is False
        assert job['quality'] == 1080
        result = client.get(f'/api/clips/{job_id}/file')
        assert result.status_code==200
        assert result.content[4:8]==b'ftyp'
        assert not list((root/'.work').glob('*.mp4'))
    restored = create_app(root, Source())
    with TestClient(restored) as client:
        assert client.get('/api/clips').json()[0]['id']==job_id


def test_queue_exports_video_without_audio_when_requested(sample_source, tmp_path):
    class Source:
        def extract(self, *_args):
            return sample_source

    root = tmp_path / 'silent-clips'
    app = create_app(root, Source())
    with TestClient(app) as client:
        response = client.post('/api/clips', json={
            'url': 'https://youtu.be/jNQXAC9IVRw', 'start': 1, 'end': 2,
            'mute_audio': True,
        }, headers={'X-Clipper-Token': app.state.token})
        assert response.status_code == 202
        job_id = response.json()['id']
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            job = app.state.queue.get(job_id)
            if job['status'] in {'done', 'error'}:
                break
            time.sleep(.05)
        assert job['status'] == 'done', job
        assert job['mute_audio'] is True
        probe = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type',
            '-of', 'json', str(root / job['filename']),
        ], capture_output=True, text=True, check=True)
        assert [stream['codec_type'] for stream in json.loads(probe.stdout)['streams']] == ['video']

    with TestClient(create_app(root)) as client:
        assert client.get('/api/clips').json()[0]['mute_audio'] is True


def test_selected_quality_downscales_and_persists(tmp_path):
    source_file = tmp_path / 'source.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'testsrc2=duration=2:size=640x480:rate=15', '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p', str(source_file)], check=True)
    requested = []
    class Source:
        def extract(self, _url, _refresh=False, quality=1080):
            requested.append(quality)
            return {'id': 'jNQXAC9IVRw', 'title': 'Quality test', 'duration': 2,
                    'vcodec': 'h264', 'acodec': 'none', 'url': str(source_file)}

    root = tmp_path / 'clips'
    app = create_app(root, Source())
    headers = {'X-Clipper-Token': app.state.token}
    with TestClient(app) as client:
        invalid = client.post('/api/clips', json={
            'url': 'https://youtu.be/jNQXAC9IVRw', 'start': 0, 'end': 1,
            'quality': 480,
        }, headers=headers)
        assert invalid.status_code == 422
        response = client.post('/api/clips', json={
            'url': 'https://youtu.be/jNQXAC9IVRw', 'start': 0, 'end': 1,
            'quality': 360,
        }, headers=headers)
        assert response.status_code == 202
        job_id = response.json()['id']
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            job = app.state.queue.get(job_id)
            if job['status'] in {'done', 'error'}:
                break
            time.sleep(.05)
        assert job['status'] == 'done', job
        assert job['quality'] == 360
        assert requested == [360]
        probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                '-show_entries', 'stream=height', '-of', 'json',
                                str(root / job['filename'])], capture_output=True, text=True, check=True)
        assert json.loads(probe.stdout)['streams'][0]['height'] == 360

    with TestClient(create_app(root)) as client:
        assert client.get('/api/clips').json()[0]['quality'] == 360


def test_delete_clip_removes_file_and_persisted_history(tmp_path):
    root = tmp_path / 'clips'
    root.mkdir()
    job_id = 'a' * 32
    filename = 'sample.mp4'
    video = root / filename
    manifest = root / f'{job_id}.json'
    video.write_bytes(b'video')
    manifest.write_text(json.dumps({
        'id': job_id, 'filename': filename, 'status': 'done', 'created': '2026-01-01T00:00:00Z',
        'title': 'sample', 'start': 0, 'end': 1, 'duration': 1,
    }), encoding='utf-8')
    app = create_app(root)
    with TestClient(app) as client:
        url = f'/api/clips/{job_id}'
        assert client.delete(url).status_code == 403
        assert video.is_file() and manifest.is_file()
        assert client.delete(url, headers={'X-Clipper-Token': app.state.token}).json() == {'deleted': True}
        assert not video.exists() and not manifest.exists()
        assert client.get('/api/clips').json() == []
        assert client.get(f'{url}/file').status_code == 404
        assert client.delete(url, headers={'X-Clipper-Token': app.state.token}).status_code == 404
    with TestClient(create_app(root)) as client:
        assert client.get('/api/clips').json() == []


def test_change_clip_folder_preserves_existing_clips(tmp_path):
    old = tmp_path / 'old'
    new = tmp_path / 'new'
    old.mkdir()
    job_id = 'c' * 32
    (old / 'sample.mp4').write_bytes(b'video')
    (old / f'{job_id}.json').write_text(json.dumps({
        'id': job_id, 'filename': 'sample.mp4', 'status': 'done',
        'created': '2026-01-01T00:00:00Z', 'title': 'sample',
    }), encoding='utf-8')
    app = create_app(old)
    queue = app.state.queue
    queue.change_root(new)
    assert queue.root == new
    assert (new / 'sample.mp4').read_bytes() == b'video'
    assert (new / f'{job_id}.json').is_file()
    assert not (old / 'sample.mp4').exists()
    with TestClient(create_app(new)) as client:
        assert client.get('/api/clips').json()[0]['id'] == job_id


def test_change_clip_folder_rejects_collisions(tmp_path):
    old = tmp_path / 'old'
    new = tmp_path / 'new'
    old.mkdir()
    new.mkdir()
    job_id = 'd' * 32
    (old / 'sample.mp4').write_bytes(b'old')
    (old / f'{job_id}.json').write_text(json.dumps({
        'id': job_id, 'filename': 'sample.mp4', 'status': 'done',
        'created': '2026-01-01T00:00:00Z', 'title': 'sample',
    }), encoding='utf-8')
    (new / 'sample.mp4').write_bytes(b'other')
    queue = create_app(old).state.queue
    with pytest.raises(FileExistsError):
        queue.change_root(new)
    assert queue.root == old
    assert (old / 'sample.mp4').read_bytes() == b'old'
    assert (new / 'sample.mp4').read_bytes() == b'other'


def test_delete_rejects_active_export(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        app.state.queue.jobs['active'] = {'id': 'active', 'created': '2026-01-01T00:00:00Z', 'status': 'queued', 'filename': None}
        response = client.delete('/api/clips/active', headers={'X-Clipper-Token': app.state.token})
        assert response.status_code == 409
        assert 'active' in app.state.queue.jobs


def test_cloud_worker_auth_and_signed_download(tmp_path, monkeypatch):
    import urllib.parse

    job_id = 'b' * 32
    video = tmp_path / 'cloud.mp4'
    video.write_bytes(b'video')
    (tmp_path / f'{job_id}.json').write_text(json.dumps({
        'id': job_id, 'filename': video.name, 'status': 'done',
        'created': '2026-01-01T00:00:00Z', 'title': 'cloud',
    }), encoding='utf-8')
    monkeypatch.setenv('PUBLIC_WORKER_URL', 'https://worker.example')
    app = create_app(tmp_path, worker_secret='test-worker-secret')
    headers = {'X-Worker-Secret': 'test-worker-secret'}
    with TestClient(app) as client:
        assert client.get('/').status_code == 404
        assert client.get('/api/clips').status_code == 403
        assert client.get('/api/clips', headers=headers).status_code == 200
        assert client.get('/api/clips', headers={**headers, 'Host': 'worker.example'}).status_code == 200
        assert client.get(f'/api/clips/{job_id}/file').status_code == 403
        link = client.get(f'/api/clips/{job_id}/download-link', headers=headers).json()['url']
        assert link.startswith(f'https://worker.example/api/clips/{job_id}/file?')
        signed_path = urllib.parse.urlsplit(link).path + '?' + urllib.parse.urlsplit(link).query
        assert client.get(signed_path).content == b'video'
        assert client.get(signed_path.replace('signature=', 'signature=x')).status_code == 403
        assert client.delete(f'/api/clips/{job_id}').status_code == 403
        assert client.delete(f'/api/clips/{job_id}', headers=headers).status_code == 200
        assert not video.exists()


def test_cancel_resolving_job(tmp_path):
    started = threading.Event()
    release = threading.Event()
    class Source:
        def extract(self, *_args):
            started.set()
            release.wait(5)
            return {'title':'cancelled'}
    app=create_app(tmp_path, Source())
    with TestClient(app):
        job=app.state.queue.enqueue('https://youtu.be/jNQXAC9IVRw',0,3)
        assert started.wait(2)
        assert app.state.queue.cancel(job['id'])['status']=='cancelled'
        release.set()
    assert app.state.queue.get(job['id'])['status']=='cancelled'
