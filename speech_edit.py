"""Local speech recognition and validated, transcript-bound refinement plans."""
import difflib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

MODEL_DIR = Path(__file__).resolve().parent / 'models'


def engine_status():
    binary = os.environ.get('VIDEO_WHISPER_BIN') or shutil.which('whisper-cli')
    candidates = [Path(os.environ.get('VIDEO_WHISPER_MODEL', '')),
                  MODEL_DIR / 'ggml-large-v3-turbo-q5_0.bin',
                  MODEL_DIR / 'ggml-small.bin',
                  Path.home() / 'Library/Application Support/VideoCompressAutocut/models/ggml-small.bin']
    model = next((p for p in candidates if p.is_file() and p.stat().st_size > 1000000), None)
    return dict(available=bool(binary and model), binary=binary, model=str(model) if model else None)


def normalize_transcript(raw, duration):
    units = []
    last_end = 0.0
    for row in raw.get('transcription', []):
        text = row.get('text', '').strip()
        start, end = float(row['offsets']['from']) / 1000, float(row['offsets']['to']) / 1000
        if not text or not all(math.isfinite(t) for t in (start, end)):
            continue
        start, end = max(last_end, 0, start), min(duration, end)
        if end <= start:
            continue
        tokens = [t for t in row.get('tokens', []) if not t.get('text', '').startswith('[_')]
        # Whisper tokens are subwords. Group punctuation-delimited phrases using
        # actual token times; never divide a coarse segment evenly by word count.
        groups, group = [], []
        timed = tokens and all('offsets' in t and 0 <= t['offsets']['from'] <= t['offsets']['to'] for t in tokens)
        if timed:
            for token in tokens:
                group.append(token)
                if re.search(r'[,.;!?…]$', token.get('text', '').strip()):
                    groups.append(group)
                    group = []
            if group:
                groups.append(group)
        else:
            groups = [tokens]
        for group in groups:
            phrase = ''.join(t.get('text', '') for t in group).strip() if timed else text
            gs = max(last_end, start, group[0]['offsets']['from'] / 1000) if timed else start
            ge = min(end, group[-1]['offsets']['to'] / 1000) if timed else end
            if not phrase or ge <= gs:
                continue
            probability = sum(t.get('p', 0) for t in group) / len(group) if group else None
            units.append(dict(id=f'u{len(units)+1:04d}', start=gs, end=ge, text=phrase,
                              recognition_probability=probability,
                              needs_review=probability is None or probability < .65 or '\ufffd' in phrase))
            last_end = ge
    return units


def repeat_candidates(units):
    """Search hints only. The Codex agent must assess meaning and unique details."""
    result = []
    for i, a in enumerate(units):
        left = re.sub(r'[^\w\s]', '', a['text'].casefold())
        if len(left.split()) < 4:
            continue
        for b in units[i+1:i+9]:
            if b['start'] - a['end'] > 90:
                break
            right = re.sub(r'[^\w\s]', '', b['text'].casefold())
            score = difflib.SequenceMatcher(None, left, right).ratio()
            if score >= .65:
                result.append(dict(first_id=a['id'], second_id=b['id'], text_similarity=round(score, 3)))
    return result


def transcribe(path, info, language='vi'):
    config = engine_status()
    if not config['available']:
        raise ValueError('speech_model_missing: install whisper.cpp and a multilingual ggml-small.bin model')
    if language not in ('vi', 'en', 'auto'):
        raise ValueError('unsupported_language')
    if info.get('audio_stream_index') is None:
        raise ValueError('no_audio')
    with tempfile.TemporaryDirectory(prefix='video-speech-') as tmp:
        wav = str(Path(tmp) / 'audio.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-map', f"0:{info['audio_stream_index']}", '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', wav], capture_output=True, check=True, timeout=600)
        prefix = str(Path(tmp) / 'transcript')
        proc = subprocess.run([config['binary'], '-m', config['model'], '-f', wav, '-l', language,
                               '-ojf', '-of', prefix, '-ml', '100', '-sow', '-np'], capture_output=True, timeout=3600)
        if proc.returncode or not Path(prefix + '.json').is_file():
            raise RuntimeError('speech_recognition_failed: ' + proc.stderr.decode('utf-8', 'replace')[-500:])
        raw = json.loads(Path(prefix + '.json').read_text(encoding='utf-8', errors='replace'))
    units = normalize_transcript(raw, info['duration'])
    if not units:
        raise ValueError('no_recognized_speech: nothing will be removed')
    return dict(language=raw.get('result', {}).get('language', language), units=units,
                repeat_candidates=repeat_candidates(units), engine='whisper.cpp', model=Path(config['model']).name)


def refinement_ranges(transcript, decisions, duration):
    """Remove only explicit, grounded IDs; preserve all other content and order."""
    units = transcript['units']
    by_id = {u['id']: u for u in units}
    removed = set()
    if not isinstance(decisions, list) or not 1 <= len(decisions) <= 100:
        raise ValueError('decisions_required')
    for decision in decisions:
        ids = decision.get('remove_ids')
        replacements = decision.get('replacement_ids', [])
        if not isinstance(ids, list) or not ids or not isinstance(replacements, list):
            raise ValueError('invalid_decision')
        if decision.get('reason_type') not in ('duplicate', 'retake', 'false_start') or not isinstance(decision.get('reason'), str) or not 4 <= len(decision['reason']) <= 2000:
            raise ValueError('decision_reason_required')
        if any(i not in by_id for i in ids + replacements):
            raise ValueError('unknown_transcript_id')
        if any(by_id[i]['needs_review'] for i in ids):
            raise ValueError('uncertain_recognition: preserve these units for manual review')
        if decision['reason_type'] in ('duplicate', 'retake') and not replacements:
            raise ValueError('replacement_ids_required')
        removed.update(ids)
    if any(i in removed for d in decisions for i in d.get('replacement_ids', [])):
        raise ValueError('replacement_is_also_removed')
    if len(removed) == len(units):
        raise ValueError('cannot_remove_all_speech')
    cuts = []
    i = 0
    while i < len(units):
        if units[i]['id'] not in removed:
            i += 1
            continue
        first = i
        while i + 1 < len(units) and units[i+1]['id'] in removed:
            i += 1
        last = i
        # Midpoints in gaps protect the preceding/following recognized speech.
        start = (units[first-1]['end'] + units[first]['start']) / 2 if first else 0
        end = (units[last]['end'] + units[last+1]['start']) / 2 if last+1 < len(units) else duration
        cuts.append([start, end])
        i += 1
    keeps, cursor = [], 0.0
    for start, end in cuts:
        if start - cursor >= .1:
            keeps.append([cursor, start])
        cursor = end
    if duration - cursor >= .1:
        keeps.append([cursor, duration])
    if not keeps:
        raise ValueError('empty_edit')
    return keeps


def map_draft_ranges(ranges, source_segments):
    """Map a silence-cut audio timeline back to its unchanged video source."""
    mapped = []
    offset = 0.0
    for source_start, source_end in source_segments:
        length = source_end - source_start
        for start, end in ranges:
            a, b = max(start, offset), min(end, offset + length)
            if b - a >= .01:
                interval = [source_start + a - offset, source_start + b - offset]
                if mapped and abs(mapped[-1][1] - interval[0]) < .001:
                    mapped[-1][1] = interval[1]
                else:
                    mapped.append(interval)
        offset += length
    if not mapped:
        raise ValueError('empty_edit')
    return mapped


def prepare_review(path, info, analyze, language='vi', pre_cut=True):
    """Cut only temporary audio for ASR. Video is rendered once after AI review."""
    if info.get('audio_stream_index') is None:
        raise ValueError('no_audio')
    if not engine_status()['available']:
        raise ValueError('speech_model_missing')
    segments = analyze(path, info['audio_stream_index'], info['duration'])['speech_segments'] if pre_cut else [[0, info['duration']]]
    if not segments or len(segments) > 200:
        raise ValueError('too_many_segments: use a shorter clip for AI review')
    duration = sum(e - s for s, e in segments)
    with tempfile.TemporaryDirectory(prefix='video-ai-draft-') as tmp:
        wav = str(Path(tmp) / 'draft.wav')
        filters = [f"[0:{info['audio_stream_index']}]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]" for i, (s, e) in enumerate(segments)]
        filters.append(''.join(f'[a{i}]' for i in range(len(segments))) + f'concat=n={len(segments)}:v=0:a=1[out]')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-filter_complex', ';'.join(filters), '-map', '[out]', '-ac', '1', '-ar', '16000', wav], capture_output=True, check=True, timeout=600)
        transcript = transcribe(wav, dict(duration=duration, audio_stream_index=0), language)
    return transcript, [list(pair) for pair in segments], duration
