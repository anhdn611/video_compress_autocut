"""Regression: two consecutive exports incl. CPU decode, bokeh and compression.
Only tiny synthetic sources are used; never reproduces a system OOM deliberately.
"""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import media_runtime

with tempfile.TemporaryDirectory(prefix='video-repeat-') as tmp:
    app.TEMP_DIR = tmp
    processes = []
    real_popen = subprocess.Popen
    def spawn(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        processes.append((proc, args[0]))
        return proc
    for n in (1, 2):
        source = str(Path(tmp) / f'source-{n}.mp4')
        real_source = os.environ.get('VIDEO_REPEAT_REAL_SOURCE')
        if real_source:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-threads', '2', '-hwaccel', 'none', '-ss', str((n-1)*3), '-i', real_source, '-t', '0.8', '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-c:a', 'aac', source], check=True)
        else:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '0.8', '-c:v', 'libx264', '-threads', '2', '-c:a', 'aac', source], check=True)
        info = app.get_video_info(source)
        tid = f'repeat-{n}'
        app.TASKS[tid] = dict(id=tid, filename=f'source-{n}.mp4', input_path=source, info=info, status='ready')
        hardware = os.environ.get('VIDEO_REPEAT_HARDWARE') == '1'
        with patch.object(media_runtime.subprocess, 'Popen', side_effect=spawn):
            app.run_trim_and_compress_worker(tid, dict(mode='keep_segments', segments=[[0, .3], [.4, .8]], enable_bokeh=True, then_compress=True, target_mb=1, hardware_encode=hardware))
        task = app.TASKS[tid]
        assert task['status'] == 'completed', task
        out = task['output_path']
        subprocess.run(['ffmpeg', '-v', 'error', '-i', out, '-f', 'null', '-'], check=True, capture_output=True)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,duration,width,height', '-of', 'json', out], check=True, capture_output=True, text=True)
        streams = json.loads(probe.stdout)['streams']
        video = next(s for s in streams if s['codec_type'] == 'video')
        audio = next(s for s in streams if s['codec_type'] == 'audio')
        ratio = min(1., 1920 / max(info['width'], info['height']))
        expected = tuple(max(2, int(info[k] * ratio) // 2 * 2) for k in ('width', 'height'))
        assert (video['width'], video['height']) == expected
        assert abs(float(video['duration']) - float(audio['duration'])) < .1
        assert all(p.poll() is not None for p, _ in processes)
        print(f'PASS export {n}: bokeh + compression, valid audio/video, all children reaped.', flush=True)
    assert sum('--raw' in command for _, command in processes) == 2
    assert any('h264_videotoolbox' in command for _, command in processes) == hardware
    assert not list(Path(tmp).glob('*_trimmed.mp4'))
    assert not list(Path(tmp).glob('*_bokeh*.mp4'))
    print('PASS: raw CPU decoder path, serialized jobs, no temporary clip leaks, peak child RSS MiB:', round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024**2, 1), flush=True)
