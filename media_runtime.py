"""Serial media jobs with bounded child memory, progress draining and process cleanup."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time

BUSY = 'Đang có tác vụ video khác. Chờ hoàn tất trước khi xuất hoặc xem trước.'
LOCK_PATH = Path(tempfile.gettempdir()) / 'VideoStudioPro_Temp' / 'media.lock'


def encoder_args(hardware=False):
    return ['-c:v', 'h264_videotoolbox'] if hardware else ['-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast']


@contextmanager
def media_job():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(BUSY) from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def stop_process(proc):
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()


def memory_problem(pids):
    """Only inspect managed children; do not enumerate or terminate other apps."""
    try:
        result = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', ','.join(map(str, pids))], capture_output=True, text=True, timeout=2)
        if any(int(x) > 1536 * 1024 for x in result.stdout.split()):
            return 'Tác vụ vượt giới hạn RAM 1.5 GB và đã được dừng để bảo vệ máy.'
        stat = subprocess.run(['/usr/bin/vm_stat'], capture_output=True, text=True, timeout=2).stdout
        page = re.search(r'page size of (\d+) bytes', stat)
        counts = {k: int(v) for k, v in re.findall(r'^([^:\n]+):\s+(\d+)\.', stat, re.M)}
        if page:
            page_size = int(page.group(1))
            compressed = counts.get('Pages occupied by compressor', 0) * page_size
            available = sum(counts.get(k, 0) for k in ('Pages free', 'Pages inactive', 'Pages speculative')) * page_size
            if compressed > 4 * 1024**3 and available < 1024**3:
                return 'Áp lực bộ nhớ hệ thống quá cao; tác vụ đã dừng. Đóng bớt ứng dụng trước khi thử lại.'
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def _supervise(processes, on_line=None):
    last_progress = [time.monotonic()]
    errors = []
    def drain():
        try:
            for line in processes[-1].stdout:
                last_progress[0] = time.monotonic()
                if on_line:
                    on_line(line.decode('utf-8', 'replace').strip())
        except Exception as exc:
            errors.append(exc)
    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    checked_at = 0
    try:
        while any(p.poll() is None for p in processes):
            if errors:
                raise errors[0]
            if any(p.poll() not in (None, 0) for p in processes):
                raise RuntimeError('Bộ xử lý video gặp lỗi; đã dừng các tiến trình liên quan.')
            now = time.monotonic()
            if now - checked_at >= 1:
                problem = memory_problem([p.pid for p in processes if p.poll() is None])
                if problem:
                    raise RuntimeError(problem)
                checked_at = now
            if on_line and now - last_progress[0] > 180:
                raise RuntimeError('Bộ xử lý không phản hồi trong 180 giây và đã được dừng.')
            time.sleep(.1)
        reader.join(timeout=3)
        if errors:
            raise errors[0]
        if any(p.returncode for p in processes):
            raise RuntimeError('Bộ xử lý video gặp lỗi.')
    finally:
        for p in reversed(processes):
            stop_process(p)
        reader.join(timeout=3)
        if processes[-1].stdout:
            processes[-1].stdout.close()


def run_media(command, on_line=None):
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=errors, start_new_session=True)
        try:
            _supervise([proc], on_line)
        except Exception as exc:
            errors.seek(0, os.SEEK_END)
            errors.seek(max(0, errors.tell() - 1200))
            detail = errors.read().decode('utf-8', 'replace')
            raise RuntimeError(str(exc) + ('\n' + detail if detail else '')) from None


def run_bokeh(input_file, output_file, info, binary, radius, quality='balanced', on_line=None, preview=False):
    """Software FFmpeg decoder -> bounded raw pipe -> Vision. No AVAssetReader.

    Long edge limited to 1920 for bokeh. Only one BGRA frame is read at a time.
    """
    width, height = int(info['width']), int(info['height'])
    ratio = min(1., 1920 / max(width, height))
    width, height = max(2, int(width * ratio) // 2 * 2), max(2, int(height * ratio) // 2 * 2)
    decode = ['ffmpeg', '-v', 'error', '-nostdin', '-threads', '2', '-hwaccel', 'none', '-i', input_file,
              '-map', '0:v:0', '-an', '-filter_threads', '1', '-vf', f'scale={width}:{height},fps=30',
              '-pix_fmt', 'bgra', '-f', 'rawvideo']
    if preview:
        decode += ['-frames:v', '1']
    decode += ['pipe:1']
    render = [binary, '--raw-preview' if preview else '--raw', str(width), str(height), str(info['duration']), output_file, str(radius), quality]
    with tempfile.TemporaryFile() as decode_errors, tempfile.TemporaryFile() as render_errors:
        decoder = subprocess.Popen(decode, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=decode_errors, start_new_session=True)
        helper = None
        try:
            helper = subprocess.Popen(render, stdin=decoder.stdout, stdout=subprocess.PIPE, stderr=render_errors, start_new_session=True)
            decoder.stdout.close()
            _supervise([decoder, helper], on_line)
        except Exception as exc:
            render_errors.seek(0, os.SEEK_END)
            render_errors.seek(max(0, render_errors.tell() - 1200))
            detail = render_errors.read().decode('utf-8', 'replace')
            raise RuntimeError(str(exc) + ('\n' + detail if detail else '')) from None
        finally:
            if helper:
                stop_process(helper)
            stop_process(decoder)
            if decoder.stdout and not decoder.stdout.closed:
                decoder.stdout.close()
