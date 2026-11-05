#!/usr/bin/env python3
import os
import re
import sys
import json
import math
import uuid
import time
import shutil
import urllib.parse
import urllib.request
import subprocess
import threading
import webview
import tempfile


from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from video_mcp import VideoControl
from media_runtime import media_job, run_media, run_bokeh, encoder_args

from build_version import __version__

# 1. Ép hệ thống nhận diện thư mục cài đặt mặc định của Homebrew chứa FFmpeg
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin:/usr/local/bin"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# 2. Trỏ thư mục TEMP ra ngoài gói .app để tránh lỗi Permission Denied của macOS
TEMP_DIR = os.path.join(tempfile.gettempdir(), "VideoStudioPro_Temp")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
APP_NAME = "VideoCompressAutocut"
GITHUB_RELEASE_API = "https://api.github.com/repos/anhdn611/video_compress_autocut/releases/latest"

# Quản lý trạng thái các tác vụ
TASKS = {}
TASKS_LOCK = threading.Lock()


def version_key(version):
    """Convert a v-prefixed semantic version into a comparable tuple."""
    base_version = version.lstrip("v").split("-", 1)[0]
    parts = []
    for part in base_version.split("."):
        match = re.match(r"\\d+", part)
        parts.append(int(match.group()) if match else 0)
    return tuple((parts + [0, 0, 0])[:3])


def latest_release():
    """Return the latest release version and its DMG URL, or None on failure."""
    request = urllib.request.Request(
        GITHUB_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": APP_NAME},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            release = json.load(response)
    except Exception:
        return None

    version = release.get("tag_name", "")
    for asset in release.get("assets", []):
        if asset.get("name") == f"{APP_NAME}.dmg":
            return version, asset.get("browser_download_url")
    return None


def download_update(dmg_url, version):
    """Download a release DMG atomically into Downloads, then return its path."""
    destination = os.path.join(DOWNLOADS_DIR, f"{APP_NAME}-{version.lstrip('v')}.dmg")
    temporary_destination = f"{destination}.part"
    request = urllib.request.Request(dmg_url, headers={"User-Agent": APP_NAME})
    with urllib.request.urlopen(request, timeout=30) as response, open(temporary_destination, "wb") as output:
        shutil.copyfileobj(response, output)
    os.replace(temporary_destination, destination)
    return destination


def check_for_updates():
    """Prompt for a newer signed GitHub Release after the app window is ready."""
    # Builds run from source and manually dispatched test artifacts use this
    # version, so they never prompt users to replace them with a release.
    if "dev" in __version__:
        return

    release = latest_release()
    if not release:
        return
    latest_version, dmg_url = release
    if not dmg_url or version_key(latest_version) <= version_key(__version__):
        return

    window = webview.windows[0]
    should_download = window.create_confirmation_dialog(
        "Update available",
        f"Version {latest_version.lstrip('v')} is available. Download and install it now?",
    )
    if not should_download:
        return

    try:
        dmg_path = download_update(dmg_url, latest_version)
        subprocess.Popen(["open", dmg_path])
        window.create_confirmation_dialog(
            "Installer opened",
            "The new installer is open. Drag the app to Applications, then reopen it to finish updating.",
        )
    except Exception as error:
        window.create_confirmation_dialog(
            "Update download failed",
            f"Could not download version {latest_version.lstrip('v')}: {error}",
        )


class AppWindowApi:
    """Small native bridge used to fit the window to the current workflow."""

    STAGE_SIZES = {
        "upload": (860, 560),
        "configure": (1080, 780),
        "export": (920, 700),
    }

    def resize_for_stage(self, stage):
        size = self.STAGE_SIZES.get(stage)
        if not size or not webview.windows:
            return False
        webview.windows[0].resize(*size)
        return True

def get_video_info(file_path):
    """Trích xuất thông số video bằng ffprobe"""
    info = {
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "size_bytes": os.path.getsize(file_path),
        "size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
        "has_audio": False,
        "audio_stream_index": None
    }
    
    # 1. Thời lượng
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        info["duration"] = float(res.stdout.strip())
    except Exception:
        pass

    # 2. Dimensions
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", file_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        dims = res.stdout.strip().split("x")
        if len(dims) == 2:
            info["width"] = int(dims[0])
            info["height"] = int(dims[1])
    except Exception:
        pass

    # 3. Audio stream (bỏ qua apple_apac nếu không hỗ trợ giải mã)
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,codec_name", "-of", "csv=p=0", file_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        for line in res.stdout.strip().splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2 and parts[1] != "apple_apac":
                info["has_audio"] = True
                info["audio_stream_index"] = parts[0]
                break
    except Exception:
        pass

    return info

def generate_thumbnail(file_path, thumb_path, duration):
    """Tạo ảnh thumbnail xem trước tại mốc 1 giây hoặc 10% video"""
    seek_time = "1"
    if duration > 2:
        seek_time = str(round(min(duration * 0.1, 5.0), 2))
    cmd = [
        "ffmpeg", "-y", "-ss", seek_time, "-i", file_path,
        "-vframes", "1", "-vf", "scale=-2:360", "-q:v", "3", thumb_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def analyze_audio_silences(file_path, audio_idx, duration, noise_db=-30, min_duration=1.2, pad=0.28, merge_gap=0.6):
    """Phân tích các khoảng im lặng thông minh với đệm an toàn và gộp khoảng dừng tự nhiên để video không bị giật"""
    if audio_idx is None:
        return {
            "has_audio": False,
            "silence_count": 0,
            "total_silence": 0.0,
            "estimated_duration": duration,
            "saved_percent": 0.0,
            "intro_silence": 0.0,
            "outro_silence": 0.0,
            "speech_segments": [(0.0, duration)]
        }

    cmd = [
        "ffmpeg", "-i", file_path,
        "-map", f"0:{audio_idx}",
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    
    silences = []
    cur_start = None
    for line in res.stderr.splitlines():
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([0-9.]+)", line)
            if m: cur_start = float(m.group(1))
        elif "silence_end:" in line and cur_start is not None:
            m = re.search(r"silence_end:\s*([0-9.]+)", line)
            if m:
                silences.append((cur_start, float(m.group(1))))
                cur_start = None

    intro_silence = 0.0
    if silences and silences[0][0] <= 0.1:
        intro_silence = round(silences[0][1], 2)

    outro_silence = 0.0
    if silences and silences[-1][1] >= duration - 0.5:
        outro_silence = round(duration - silences[-1][0], 2)

    # Đảo ngược khoảng im lặng thành các khoảng có tiếng (Speech intervals)
    # Tăng pad từ 0.15 lên 0.28s để giữ trọn hơi thở đầu câu và âm vang đuôi câu
    raw_speech = []
    prev_end = 0.0
    for s_start, s_end in silences:
        seg_start = max(0.0, prev_end - pad)
        seg_end = min(duration, s_start + pad)
        if seg_end - seg_start > 0.3:
            raw_speech.append((round(seg_start, 2), round(seg_end, 2)))
        prev_end = s_end

    if prev_end < duration:
        seg_start = max(0.0, prev_end - pad)
        if duration - seg_start > 0.3:
            raw_speech.append((round(seg_start, 2), round(duration, 2)))

    # Gộp các khoảng rất gần nhau (< merge_gap) để tránh cắt vụn nhịp nói thông thường
    merged_speech = []
    for s, e in raw_speech:
        if not merged_speech:
            merged_speech.append([s, e])
        else:
            if s <= merged_speech[-1][1] + merge_gap:
                merged_speech[-1][1] = max(merged_speech[-1][1], e)
            else:
                merged_speech.append([s, e])

    if not merged_speech:
        merged_speech = [(0.0, duration)]

    total_speech = sum(e - s for s, e in merged_speech)
    total_silence = max(0.0, duration - total_speech)
    saved_pct = round((total_silence / duration) * 100, 1) if duration > 0 else 0

    return {
        "has_audio": True,
        "silence_count": len(silences),
        "speech_segments_count": len(merged_speech),
        "total_silence": round(total_silence, 2),
        "estimated_duration": round(total_speech, 2),
        "saved_percent": saved_pct,
        "intro_silence": intro_silence,
        "outro_silence": outro_silence,
        "speech_segments": [tuple(m) for m in merged_speech]
    }

def do_encode_step(input_file, output_file, target_mb, duration, audio_stream_idx, task_dict, is_retry=False, prog_start=45.0, prog_range=50.0, hardware_encode=False):
    """Mã hóa nén video bằng Apple Silicon VideoToolbox"""
    audio_bitrate_kbps = 128 if audio_stream_idx is not None else 0
    total_bitrate_kbps = math.floor((target_mb * 8 * 1024) / duration)
    video_bitrate_kbps = max(total_bitrate_kbps - audio_bitrate_kbps, 40)
    
    if video_bitrate_kbps < 250:
        scale_filter = "scale=-2:360"
    elif video_bitrate_kbps < 500:
        scale_filter = "scale=-2:480"
    elif video_bitrate_kbps < 1000:
        scale_filter = "scale=-2:720"
    else:
        scale_filter = "scale='min(1920,iw)':-2"

    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-threads", "2", "-hwaccel", "none", "-filter_threads", "1", "-i", input_file, "-map", "0:v:0"]

    if audio_stream_idx is not None:
        cmd.extend(["-map", f"0:{audio_stream_idx}", "-c:a", "aac", "-b:a", f"{audio_bitrate_kbps}k"])
    else:
        cmd.append("-an")

    cmd.extend(encoder_args(hardware_encode))
    cmd.extend([
        "-b:v", f"{video_bitrate_kbps}k",
        "-vf", scale_filter,
        "-progress", "pipe:1",
        output_file
    ])

    with TASKS_LOCK:
        stage_name = ("Đang nén bằng phần cứng, giải mã CPU…" if hardware_encode else "Đang nén bằng CPU (chế độ an toàn)…") if not is_retry else "Đang nén lại (Auto-Retry)…"
        task_dict["stage"] = stage_name
        task_dict["video_bitrate_kbps"] = video_bitrate_kbps

    def on_progress(line):
        if line.startswith("out_time_us="):
            try:
                out_time_s = float(line.split("=")[1]) / 1000000.0
                pct = min(round((out_time_s / duration) * 100, 1), 99.0)
                if not is_retry:
                    display_pct = round(prog_start + (pct / 100.0) * prog_range, 1)
                else:
                    display_pct = round(prog_start + prog_range * 0.5 + (pct / 100.0) * (prog_range * 0.5), 1)
                with TASKS_LOCK:
                    task_dict["progress"] = min(display_pct, 99.0)
            except Exception:
                pass
        elif line.startswith("speed="):
            speed_val = line.split("=")[1].strip()
            with TASKS_LOCK:
                task_dict["speed"] = speed_val

    run_media(cmd, on_progress)
    return True


def run_trim_and_compress_worker(task_id, params):
    try:
        with media_job():
            _run_trim_and_compress_worker(task_id, params)
        with TASKS_LOCK:
            if TASKS[task_id]["status"] == "finishing":
                TASKS[task_id]["status"] = "completed"
    except Exception as exc:
        with TASKS_LOCK:
            TASKS[task_id].update(status="error", error=str(exc))


def _run_trim_and_compress_worker(task_id, params):
    """Worker thực thi phối hợp linh hoạt Cắt đoạn thừa, Xóa phông AI và Nén video"""
    with TASKS_LOCK:
        task = TASKS[task_id]
        task["status"] = "processing"
        task["progress"] = 5
        task["stage"] = "Đang chuẩn bị xử lý video..."

    input_file = params.get("_source_path", task["input_path"])
    info = params.get("_source_info", task["info"])
    duration = info["duration"]
    audio_idx = info.get("audio_stream_index")
    mode = params.get("mode", "auto_silence") # auto_silence | intro_outro | manual | none
    enable_bokeh = params.get("enable_bokeh", False)
    then_compress = params.get("then_compress", False)
    target_mb = float(params.get("target_mb", 18.0))

    has_trim = (mode in ("auto_silence", "intro_outro", "manual", "keep_segments"))

    run_id = str(uuid.uuid4())[:12]
    trimmed_file = os.path.join(TEMP_DIR, f"{task_id}_{run_id}_trimmed.mp4")
    final_output = os.path.join(TEMP_DIR, f"{task_id}_{run_id}_final.mp4")
    intermediates = [trimmed_file]

    try:
        # BƯỚC 1: XỬ LÝ CẮT ĐOẠN THỪA (NẾU CÓ)
        source_for_next = input_file
        
        if mode in ("auto_silence", "keep_segments"):
            with TASKS_LOCK:
                task["stage"] = "Đang dò tìm và lọc bỏ các khoảng im lặng..."
                task["progress"] = 12

            noise_db = int(params.get("noise_db", -30))
            min_silence = float(params.get("min_silence", 1.2))
            pad = float(params.get("pad", 0.28))
            merge_gap = float(params.get("merge_gap", 0.6))
            if mode == "keep_segments":
                segments = params["segments"]
            else:
                silence_res = analyze_audio_silences(input_file, audio_idx, duration, noise_db, min_silence, pad, merge_gap)
                segments = silence_res["speech_segments"]

            if segments:
                with TASKS_LOCK:
                    task["stage"] = f"Đang ghép {len(segments)} đoạn có tiếng nói (Jump-cut)..."
                    task["progress"] = 20

                from low_memory_render import render_segments
                def report_segment(done, total):
                    with TASKS_LOCK:
                        task["stage"] = f"Đang xuất tuần tự đoạn {done}/{total} (tiết kiệm RAM)…"
                        task["progress"] = round(20 + 5 * done / total, 1)
                render_segments(input_file, trimmed_file, segments, audio_idx,
                                smooth=bool(params.get("_smooth")), progress=report_segment, hardware_encode=params.get("hardware_encode") is True)
                source_for_next = trimmed_file
            
        elif mode == "intro_outro":
            with TASKS_LOCK:
                task["stage"] = "Đang tự động cắt bỏ khoảng thừa đầu & đuôi..."
                task["progress"] = 15

            silence_res = analyze_audio_silences(input_file, audio_idx, duration)
            start_s = silence_res.get("intro_silence", 0.0)
            end_s = max(0.0, duration - silence_res.get("outro_silence", 0.0))
            if end_s > start_s + 1.0:
                cut_cmd = [
                    "ffmpeg", "-v", "error", "-nostdin", "-y", "-threads", "2", "-hwaccel", "none", "-filter_threads", "1", "-ss", str(start_s), "-to", str(end_s),
                    "-i", input_file,
                    "-map", "0:v:0"
                ]
                if audio_idx is not None:
                    cut_cmd.extend(["-map", f"0:{audio_idx}", "-c:a", "copy"])
                cut_cmd.extend(["-c:v", "copy", trimmed_file])
                run_media(cut_cmd)
                if os.path.exists(trimmed_file):
                    source_for_next = trimmed_file

        elif mode == "manual":
            start_s = float(params.get("start_time", 0.0))
            end_s = float(params.get("end_time", duration))
            with TASKS_LOCK:
                task["stage"] = f"Đang cắt đoạn từ {start_s}s đến {end_s}s..."
                task["progress"] = 15

            cut_cmd = [
                "ffmpeg", "-v", "error", "-nostdin", "-y", "-threads", "2", "-hwaccel", "none", "-filter_threads", "1", "-ss", str(start_s), "-to", str(end_s),
                "-i", input_file,
                "-map", "0:v:0"
            ]
            if audio_idx is not None:
                cut_cmd.extend(["-map", f"0:{audio_idx}", "-c:a", "aac", "-b:a", "128k"])
            cut_cmd.extend(encoder_args(params.get("hardware_encode") is True) + ["-b:v", "3500k", trimmed_file])
            run_media(cut_cmd)
            if os.path.exists(trimmed_file):
                source_for_next = trimmed_file

        # BƯỚC 2: LÀM MỜ HẬU CẢNH BẰNG APPLE VISION AI (BOKEH)
        if enable_bokeh:
            if has_trim and then_compress:
                bokeh_start, bokeh_range = 25.0, 45.0
            elif has_trim:
                bokeh_start, bokeh_range = 25.0, 70.0
            elif then_compress:
                bokeh_start, bokeh_range = 5.0, 60.0
            else:
                bokeh_start, bokeh_range = 5.0, 90.0

            with TASKS_LOCK:
                task["stage"] = "Đang tách người và làm mờ phông nền bằng Apple Vision AI..."
                task["progress"] = round(bokeh_start, 1)

            blur_radius = float(params.get("blur_radius", 25.0))
            quality = params.get("bokeh_quality", "balanced")
            blurred_raw_video = os.path.join(TEMP_DIR, f"{task_id}_{run_id}_bokeh_raw.mp4")
            blurred_with_audio = os.path.join(TEMP_DIR, f"{task_id}_{run_id}_bokeh.mp4")

            blur_bin = os.path.join(BASE_DIR, "cinematic_blur")
            intermediates.extend([blurred_raw_video, blurred_with_audio])
            def on_bokeh_progress(line):
                if line.startswith("PROGRESS:"):
                    pct_val = float(line.replace("PROGRESS:", "").replace("%", "").strip())
                    with TASKS_LOCK:
                        task["progress"] = round(bokeh_start + pct_val / 100 * bokeh_range, 1)
            with TASKS_LOCK:
                task["stage"] = "Đang xóa phông an toàn: giải mã CPU, tối đa 1080p, giải phóng từng frame…"
            run_bokeh(source_for_next, blurred_raw_video, get_video_info(source_for_next),
                      blur_bin, blur_radius, quality, on_bokeh_progress)
            temp_audio_idx = get_video_info(source_for_next).get("audio_stream_index")
            mux_cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", blurred_raw_video, "-i", source_for_next, "-map", "0:v:0"]
            if temp_audio_idx is not None:
                mux_cmd.extend(["-map", f"1:{temp_audio_idx}", "-c:a", "aac", "-b:a", "128k"])
            mux_cmd.extend(["-c:v", "copy", "-shortest", blurred_with_audio])
            run_media(mux_cmd)
            source_for_next = blurred_with_audio

        # Cập nhật thông số sau khi cắt và/hoặc xóa phông
        new_info = get_video_info(source_for_next)
        new_duration = new_info["duration"] if new_info["duration"] > 0 else duration
        new_audio_idx = new_info.get("audio_stream_index")

        # BƯỚC 3: NÉN (NẾU ĐƯỢC CHỌN) HOẶC XUẤT THẲNG
        if then_compress:
            if has_trim and enable_bokeh:
                comp_start, comp_range = 70.0, 27.0
            elif has_trim or enable_bokeh:
                comp_start, comp_range = 35.0, 62.0
            else:
                comp_start, comp_range = 5.0, 92.0

            with TASKS_LOCK:
                task["stage"] = "Đang nén video xuống dưới mức dung lượng mục tiêu..."
                task["progress"] = round(comp_start, 1)

            success = do_encode_step(source_for_next, final_output, target_mb, new_duration, new_audio_idx, task, prog_start=comp_start, prog_range=comp_range, hardware_encode=params.get("hardware_encode") is True)
            if not success or not os.path.exists(final_output):
                with TASKS_LOCK:
                    task["status"] = "error"
                    task["error"] = "Quá trình nén video gặp sự cố."
                return

            out_size_bytes = os.path.getsize(final_output)
            out_size_mb = round(out_size_bytes / (1024 * 1024), 2)
            max_allowed = max(target_mb, 20.0) if target_mb <= 20 else target_mb + 1.0

            # Auto-retry nếu vượt quá mục tiêu
            if out_size_mb > max_allowed:
                retry_target = round(target_mb * (target_mb / out_size_mb) * 0.95, 1)
                do_encode_step(source_for_next, final_output, retry_target, new_duration, new_audio_idx, task, is_retry=True, prog_start=comp_start, prog_range=comp_range, hardware_encode=params.get("hardware_encode") is True)
                out_size_bytes = os.path.getsize(final_output)
                out_size_mb = round(out_size_bytes / (1024 * 1024), 2)
        else:
            # Không cần nén -> Chỉ cần sao chép file kết quả cuối
            if os.path.exists(source_for_next) and source_for_next != final_output:
                shutil.copyfile(source_for_next, final_output)
            out_size_bytes = os.path.getsize(final_output)
            out_size_mb = round(out_size_bytes / (1024 * 1024), 2)

        # Lấy thông số kết quả cuối
        final_info = get_video_info(final_output)
        orig_size_mb = task["info"]["size_mb"]
        orig_dur = task["info"]["duration"]
        final_dur = final_info["duration"]

        saved_size_pct = round(((orig_size_mb - out_size_mb) / orig_size_mb) * 100, 1) if orig_size_mb > 0 else 0
        saved_time_sec = round(max(0.0, orig_dur - final_dur), 1)

        # Tạo tên file mô tả đầy đủ các tính năng đã áp dụng
        parts = []
        if has_trim and mode != "none":
            if mode == "auto_silence": parts.append("silence_cut")
            elif mode == "intro_outro": parts.append("trimmed")
            elif mode in ("manual", "keep_segments"): parts.append("cut")
        if params.get("_smooth"):
            parts.append("ai_refined")
        if enable_bokeh:
            parts.append("bokeh")
        if then_compress:
            parts.append(f"under{int(target_mb)}mb")
        if not parts:
            parts.append("processed")

        clean_base = os.path.splitext(task['filename'])[0]
        final_filename = f"{clean_base}_{'_'.join(parts)}.mp4"

        with TASKS_LOCK:
            task["output_path"] = final_output
            task["output_revision"] = run_id
            task["output_info"] = final_info
            task["status"] = "finishing"
            task["progress"] = 100
            task["stage"] = "Xử lý hoàn tất!"
            task["result"] = {
                "output_size_mb": out_size_mb,
                "output_size_bytes": out_size_bytes,
                "duration": round(final_dur, 1),
                "width": final_info["width"],
                "height": final_info["height"],
                "saved_percent": saved_size_pct,
                "saved_time_sec": saved_time_sec,
                "output_filename": final_filename
            }

    except Exception as e:
        with TASKS_LOCK:
            task["status"] = "error"
            task["error"] = str(e)
    finally:
        for temporary_path in intermediates:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
        if task.get("output_path") != final_output:
            try:
                os.unlink(final_output)
            except FileNotFoundError:
                pass


CONTROL = VideoControl(TASKS, TASKS_LOCK, run_trim_and_compress_worker, analyze_audio_silences)

class VideoCompressorHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-File-Name")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        query = urllib.parse.parse_qs(url.query)

        # Trang chủ
        if path == "/" or path == "/index.html":
            index_file = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_file):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                with open(index_file, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Index file not found")
            return

        # Static assets
        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = os.path.join(STATIC_DIR, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                ctype = "text/plain"
                if ext == ".css": ctype = "text/css"
                elif ext == ".js": ctype = "application/javascript"
                elif ext == ".png": ctype = "image/png"
                elif ext in (".jpg", ".jpeg"): ctype = "image/jpeg"
                elif ext == ".svg": ctype = "image/svg+xml"

                self.send_response(200)
                self.send_header("Content-Type", ctype)
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # Bokeh Preview Image
        if path == "/api/bokeh-preview-image":
            task_id = query.get("id", [""])[0]
            bokeh_path = os.path.join(TEMP_DIR, f"{task_id}_bokeh_preview.jpg")
            if os.path.exists(bokeh_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                with open(bokeh_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Bokeh preview not found")
            return

        # Thumbnail
        if path == "/api/thumbnail":
            task_id = query.get("id", [""])[0]
            thumb_path = os.path.join(TEMP_DIR, f"{task_id}_thumb.jpg")
            if os.path.exists(thumb_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                with open(thumb_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "Thumbnail not found")
            return

        # Progress query
        if path == "/api/progress":
            task_id = query.get("id", [""])[0]
            with TASKS_LOCK:
                task = TASKS.get(task_id)
                if not task:
                    self.send_json({"error": "Task not found"}, 404)
                    return
                data = {
                    "status": task["status"],
                    "progress": task.get("progress", 0),
                    "stage": task.get("stage", ""),
                    "speed": task.get("speed", ""),
                    "error": task.get("error", None),
                    "mcp_job_id": task.get("mcp_job_id"),
                    "ai_stage": task.get("ai_stage", ""),
                    "result": task.get("result", None)
                }
            self.send_json(data)
            return

        # Download video
        if path == "/api/download":
            task_id = query.get("id", [""])[0]
            with TASKS_LOCK:
                task = TASKS.get(task_id)
            if not task or not task.get("output_path") or not os.path.exists(task["output_path"]):
                self.send_error(404, "Output file not found")
                return

            filename = (task.get("result") or {}).get("output_filename", f"{task_id}.mp4")
            file_size = os.path.getsize(task["output_path"])
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Content-Disposition", f'attachment; filename="{urllib.parse.quote(filename)}"')
            self.end_headers()

            with open(task["output_path"], "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return

        if path == "/api/review-source":
            job_id = query.get("job_id", [""])[0]
            with TASKS_LOCK:
                pending = CONTROL.pending_reviews.get(job_id)
                record = CONTROL.transcripts.get(pending["transcript_id"]) if pending else None
                file_path = record["path"] if record else None
            if not file_path or not os.path.isfile(file_path):
                self.send_error(404, "Review source unavailable")
                return
            size = os.path.getsize(file_path)
            start, end, status = 0, size - 1, 200
            byte_range = self.headers.get("Range")
            if byte_range:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", byte_range)
                try:
                    if not match or not any(match.groups()):
                        raise ValueError()
                    left, right = match.groups()
                    if left:
                        start, end = int(left), min(int(right), size - 1) if right else size - 1
                    else:
                        start = max(0, size - int(right))
                    if start < 0 or start > end or start >= size:
                        raise ValueError()
                    status = 206
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
            self.send_response(status)
            self.send_header("Content-Type", "video/quicktime" if file_path.lower().endswith(".mov") else "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(end - start + 1))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if self.command == "HEAD":
                return
            try:
                with open(file_path, "rb") as source:
                    source.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        # Stream / preview video
        if path == "/api/preview":
            task_id = query.get("id", [""])[0]
            with TASKS_LOCK:
                task = TASKS.get(task_id)
            if not task or not task.get("output_path") or not os.path.exists(task["output_path"]):
                self.send_error(404, "Output file not found")
                return

            file_size = os.path.getsize(task["output_path"])
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(file_size))
            self.end_headers()

            with open(task["output_path"], "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        origin = self.headers.get("Origin")
        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
        if origin and origin != expected_origin:
            self.send_json({"error": "invalid_origin"}, 403)
            return

        if path.startswith("/api/ai/"):
            # Settings and keys are accepted only from this app's own page.
            if origin != expected_origin:
                self.send_json({"error": "invalid_origin"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 65536:
                    raise ValueError("invalid_request_size")
                data = json.loads(self.rfile.read(length))
                import cloud_models
                if path == "/api/ai/settings":
                    result = cloud_models.profiles()
                    result["selected_video"] = CONTROL.snapshot()
                    with TASKS_LOCK:
                        result["active_jobs"] = [dict(job_id=j["job_id"], status=j["status"]) for j in CONTROL.cloud_runs.values() if j["status"] in ("running", "awaiting_review")]
                elif path == "/api/ai/save":
                    result = cloud_models.save_profile(data)
                elif path == "/api/ai/select":
                    result = cloud_models.select_profile(data.get("id"))
                elif path == "/api/ai/delete":
                    result = cloud_models.delete_profile(data.get("id"))
                elif path == "/api/ai/models":
                    result = {"models": cloud_models.preview_models(data)}
                elif path == "/api/ai/start":
                    snapshot = CONTROL.snapshot()
                    args = {k: snapshot[k] for k in ("instance_id", "video_id", "selection_revision")}
                    result = CONTROL.start_cloud(dict(args, profile_id=data.get("profile_id"), request_id=data.get("request_id"), target_mb=data.get("target_mb", 24), then_compress=data.get("then_compress", True), hardware_encode=data.get("hardware_encode", False)))
                elif path == "/api/ai/approve":
                    result = CONTROL.approve_review(data)
                elif path == "/api/ai/cancel":
                    result = CONTROL.cancel_review(data.get("job_id"))
                elif path == "/api/ai/job":
                    result = CONTROL.call("get_job", {"job_id": data.get("job_id")})
                else:
                    raise ValueError("unknown_action")
                self.send_json(result)
            except (ValueError, KeyError, TypeError) as e:
                self.send_json({"error": str(e)}, 400)
            return

        if path == "/api/mcp":
            import secrets
            if not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + CONTROL.token):
                self.send_json({"error": "unauthorized"}, 401)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 65536:
                    raise ValueError("invalid_request_size")
                data = json.loads(self.rfile.read(length))
                self.send_json(CONTROL.call(data["action"], data.get("args", {})))
            except (ValueError, KeyError, TypeError) as e:
                self.send_json({"error": str(e)}, 400)
            return

        if path == "/api/selection":
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                with TASKS_LOCK:
                    # A delayed reset must not clear a more recently uploaded video.
                    if data.get("previous_id") == CONTROL.selected:
                        CONTROL.select(None)
                self.send_json({"success": True})
            except (ValueError, TypeError) as e:
                self.send_json({"error": str(e)}, 400)
            return

        # Upload video directly
        if path == "/api/upload":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                raw_filename = self.headers.get("X-File-Name", "uploaded_video.mp4")
                filename = urllib.parse.unquote(raw_filename)

                task_id = str(uuid.uuid4())[:8]
                ext = os.path.splitext(filename)[1] or ".mp4"
                saved_path = os.path.join(TEMP_DIR, f"{task_id}_input{ext}")

                # 1. Ghi file an toàn
                bytes_read = 0
                chunk_size = 1024 * 1024
                with open(saved_path, "wb") as f:
                    while bytes_read < content_length:
                        to_read = min(chunk_size, content_length - bytes_read)
                        chunk = self.rfile.read(to_read)
                        if not chunk: break
                        f.write(chunk)
                        bytes_read += len(chunk)

                # 2. Lấy thông tin và tạo thumbnail (có bắt lỗi nếu thiếu FFmpeg)
                try:
                    info = get_video_info(saved_path)
                    thumb_path = os.path.join(TEMP_DIR, f"{task_id}_thumb.jpg")
                    generate_thumbnail(saved_path, thumb_path, info["duration"])
                except FileNotFoundError:
                    raise Exception("Không tìm thấy FFmpeg/FFprobe trên máy. Vui lòng chạy lệnh 'brew install ffmpeg' trên Terminal.")
                except Exception as e:
                    raise Exception(f"Lỗi xử lý video: {str(e)}")

                with TASKS_LOCK:
                    TASKS[task_id] = {
                        "id": task_id,
                        "filename": filename,
                        "input_path": saved_path,
                        "info": info,
                        "status": "ready",
                        "created_at": time.time()
                    }
                    CONTROL.select(task_id)

                self.send_json({
                    "id": task_id,
                    "filename": filename,
                    "info": info,
                    "thumbnail_url": f"/api/thumbnail?id={task_id}"
                })
            except Exception as e:
                print(f"Upload error: {str(e)}")
                self.send_json({"error": str(e)}, 500)
            return

        # Tạo ảnh xem trước xóa phông (Bokeh)
        if path == "/api/preview-bokeh":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            task_id = data.get("id")
            blur_radius = float(data.get("blur_radius", 25.0))

            with TASKS_LOCK:
                task = TASKS.get(task_id)

            if not task:
                self.send_json({"error": "Task not found"}, 404)
                return

            input_path = task["input_path"]
            preview_out = os.path.join(TEMP_DIR, f"{task_id}_bokeh_preview.jpg")
            blur_bin = os.path.join(BASE_DIR, "cinematic_blur")
            try:
                with media_job():
                    run_bokeh(input_path, preview_out, task["info"], blur_bin, blur_radius, preview=True)
            except Exception as exc:
                self.send_json({"error": str(exc)}, 409)
                return

            self.send_json({"preview_url": f"/api/bokeh-preview-image?id={task_id}&t={int(time.time())}"})
            return

        # Phân tích khoảng im lặng
        if path == "/api/analyze-silence":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            task_id = data.get("id")
            noise_db = int(data.get("noise_db", -30))
            min_silence = float(data.get("min_silence", 1.2))
            pad = float(data.get("pad", 0.28))
            merge_gap = float(data.get("merge_gap", 0.6))

            with TASKS_LOCK:
                task = TASKS.get(task_id)

            if not task:
                self.send_json({"error": "Task not found"}, 404)
                return

            res = analyze_audio_silences(
                task["input_path"],
                task["info"].get("audio_stream_index"),
                task["info"]["duration"],
                noise_db=noise_db,
                min_duration=min_silence,
                pad=pad,
                merge_gap=merge_gap
            )
            self.send_json(res)
            return

        # Bắt đầu xử lý (Cắt hoặc Nén hoặc Cả hai)
        if path == "/api/process":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            params = json.loads(body)
            params = {k: v for k, v in params.items() if not k.startswith("_")}
            task_id = params.get("id")
            if params.get("mode") == "keep_segments":
                self.send_json({"error": "Use validated MCP process_video for keep_segments"}, 400)
                return

            with TASKS_LOCK:
                if task_id not in TASKS:
                    self.send_json({"error": "Task not found"}, 404)
                    return

                if any(p["base"]["video_id"] == task_id for p in CONTROL.pending_reviews.values()):
                    self.send_json({"error": "Duyệt hoặc hủy đề xuất AI trước khi xuất."}, 409)
                    return
                if any(t["status"] in ("processing", "finishing") for t in TASKS.values()):
                    self.send_json({"error": "busy"}, 409)
                    return
                TASKS[task_id].update(status="processing", progress=0, result=None, error=None)

            t = threading.Thread(target=run_trim_and_compress_worker, args=(task_id, params), daemon=True)
            t.start()

            self.send_json({"success": True, "id": task_id})
            return

        # Lưu thẳng vào Downloads của máy Mac và mở Finder
        if path == "/api/save-downloads":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            task_id = data.get("id")

            with TASKS_LOCK:
                task = TASKS.get(task_id)

            if not task or not task.get("output_path") or not os.path.exists(task["output_path"]):
                self.send_json({"error": "File not found"}, 404)
                return

            out_filename = (task.get("result") or {}).get("output_filename", f"processed_{task_id}.mp4")
            dest_path = os.path.join(DOWNLOADS_DIR, out_filename)

            base, ext = os.path.splitext(dest_path)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = f"{base}_{counter}{ext}"
                counter += 1

            shutil.copyfile(task["output_path"], dest_path)
            subprocess.run(["open", "-R", dest_path])

            self.send_json({"success": True, "saved_path": dest_path})
            return

        self.send_error(404, "Not Found")

def start_server(port=8765):
    ThreadingHTTPServer.allow_reuse_address = True
    # Never terminate another process merely because it happens to use the
    # default port. This also makes side-by-side preview builds safe to run.
    for candidate_port in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate_port), VideoCompressorHandler)
            port = candidate_port
            break
        except OSError as error:
            if error.errno != 48:  # Address already in use
                raise
    else:
        raise OSError(f"Không thể mở cổng từ {port} đến {port + 19}.")
    url = f"http://127.0.0.1:{port}"
    CONTROL.publish(port)
    print(f"🚀 Video Studio Pro đang chạy tại: {url}")
    return server, url

if __name__ == "__main__":
    import webview
    
    port = 8765
    server, url = start_server(port)

    # Đẩy HTTP server sang một luồng riêng biệt để không block giao diện cửa sổ
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"🖥️ Mở giao diện Desktop App tại: {url}")

    # Tạo và hiển thị cửa sổ Desktop độc lập
    webview.create_window(
        title="Video Studio Pro — Safe Export",
        url=url,
        width=860,
        height=560,
        min_size=(720, 520),
        js_api=AppWindowApi(),
        background_color='#090d16' # Đồng bộ với --bg-main trong style.css để tránh chớp trắng khi load
    )
    
    # Bắt đầu vòng lặp sự kiện của giao diện native (chặn luồng chính tại đây)
    webview.start(check_for_updates)

    # Khi người dùng bấm X để đóng cửa sổ, tiến hành dọn dẹp process
    print("\nĐã đóng giao diện, đang dừng hệ thống...")
    server.shutdown()
    server.server_close()
    CONTROL.close()
