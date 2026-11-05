"""Bounded-memory rendering: one decoded segment at a time, then stream-copy concat."""
import math
import os
from pathlib import Path
import subprocess
import tempfile


def checked(command):
    from media_runtime import run_media
    run_media(command)


def render_segments(input_file, output_file, segments, audio_idx=None, smooth=False, progress=None, hardware_encode=False):
    """RAM does not grow with the number/length of video segments.

    Files share codecs/timebase/resolution. Concat demuxer copies packets instead
    of opening a video filter branch for every retained segment. Use audio
    micro-fades rather than a full-resolution xfade graph that buffers frames.
    """
    if not segments:
        raise ValueError('empty_segments')
    output = Path(output_file).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='video-render-', dir=output.parent) as directory:
        root = Path(directory)
        names = []
        for i, (start, end) in enumerate(segments):
            if not all(math.isfinite(x) for x in (start, end)) or start < 0 or end <= start:
                raise ValueError('invalid_segment')
            length = end - start
            # Match audio and video endpoints on a 30fps grid; pad at most one
            # frame rather than clipping the tail of a retained word.
            duration = math.ceil(length * 30 - 1e-7) / 30
            clip = root / f'part-{i:04d}.mp4'
            command = ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-threads', '2',
                       '-hwaccel', 'none', '-filter_threads', '1', '-ss', str(start), '-t', str(length), '-i', str(Path(input_file).resolve()),
                       '-map', '0:v:0', '-vf',
                       f'fps=30,tpad=stop_mode=clone:stop_duration=0.04,trim=duration={duration:.9f},setpts=PTS-STARTPTS,format=yuv420p,setsar=1']
            if audio_idx is not None:
                fade = min(.02 if smooth else .01, duration / 4)
                af = f'asetpts=PTS-STARTPTS,aresample=48000,apad,atrim=duration={duration:.9f},afade=t=in:d={fade:.6f},afade=t=out:st={duration-fade:.9f}:d={fade:.6f}'
                command += ['-map', f'0:{audio_idx}', '-af', af, '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-b:a', '128k']
            else:
                command += ['-an']
            from media_runtime import encoder_args
            command += ['-t', f'{duration:.9f}'] + encoder_args(hardware_encode) + ['-b:v', '4000k', '-video_track_timescale', '15360', str(clip)]
            checked(command)
            names.append(clip.name)
            if progress:
                progress(i + 1, len(segments))
        manifest = root / 'parts.ffconcat'
        manifest.write_text('ffconcat version 1.0\n' + ''.join(f"file '{name}'\n" for name in names))
        merged = root / 'merged.mp4'
        checked(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-f', 'concat', '-safe', '1', '-i', str(manifest),
                 '-map', '0:v:0', '-map', '0:a?', '-c', 'copy', '-movflags', '+faststart', str(merged)])
        os.replace(merged, output)
