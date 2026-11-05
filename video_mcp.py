"""Authenticated local control plane shared by the desktop app and MCP bridge."""
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
import uuid

RUNTIME_DIR = Path(os.environ.get('VIDEO_MCP_RUNTIME_DIR', Path.home() / 'Library/Application Support/VideoCompressAutocut/mcp'))


class VideoControl:
    def __init__(self, tasks, lock, worker, analyze):
        self.tasks, self.lock, self.worker, self.analyze = tasks, lock, worker, analyze
        self.instance_id = str(uuid.uuid4())
        self.token = secrets.token_urlsafe(32)
        self.selected = None
        self.revision = 0
        self.jobs = {}
        self.requests = {}
        self.transcripts = {}
        self.cloud_runs = {}
        self.cloud_requests = {}
        self.pending_reviews = {}
        self.cloud_lock = threading.Lock()
        self.descriptor = None

    def publish(self, port):
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.descriptor = RUNTIME_DIR / (self.instance_id + '.json')
        fd = os.open(self.descriptor, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(dict(port=port, instance_id=self.instance_id, token=self.token, pid=os.getpid()), f)

    def close(self):
        if self.descriptor:
            self.descriptor.unlink(missing_ok=True)

    def select(self, task_id):
        # Called while holding the application's task lock.
        if task_id is not None and task_id not in self.tasks:
            raise ValueError('unknown_video')
        self.selected = task_id
        self.revision += 1

    def snapshot(self):
        with self.lock:
            t = self.tasks.get(self.selected)
            return dict(instance_id=self.instance_id, video_id=self.selected,
                        selection_revision=self.revision,
                        filename=t['filename'] if t else None,
                        info=t['info'] if t else None,
                        status=t['status'] if t else 'no_selection',
                        source_revision=(t.get('output_revision') or 'original') if t else None,
                        has_processed_output=bool(t and t.get('output_revision')),
                        working_info=t.get('output_info', t['info']) if t else None)

    def call(self, action, args):
        if action == 'approve_ai_review':
            return self.approve_review(args)
        if action == 'cancel_ai_review':
            return self.cancel_review(args.get('job_id'))
        if action == 'list_ai_models':
            from cloud_models import profiles
            return profiles()
        if action == 'cloud_ai_edit':
            return self.start_cloud(args)
        if action == 'speech_status':
            from speech_edit import engine_status
            config = engine_status()
            return dict(available=config['available'], engine='whisper.cpp', model=Path(config['model']).name if config['model'] else None)
        if action == 'get_selected_video':
            return self.snapshot()
        with self.lock:
            if action == 'get_job':
                j = self.cloud_runs.get(args.get('job_id')) or self.jobs.get(args.get('job_id'))
                if not j:
                    raise ValueError('unknown_job')
                if j['kind'] == 'export' and j['status'] == 'running':
                    t = self.tasks[j['video_id']]
                    return dict(j, progress=t.get('progress', 0), stage=t.get('stage', ''))
                return dict(j)
            if args.get('instance_id') != self.instance_id or args.get('video_id') != self.selected or args.get('selection_revision') != self.revision:
                raise ValueError('stale_selection: call get_selected_video again')
            if self.selected is None:
                raise ValueError('no_selection')
            t = self.tasks[self.selected]
            if action == 'get_transcript':
                record = self.transcripts.get(args.get('transcript_id'))
                if not record or record['video_id'] != self.selected:
                    raise ValueError('unknown_transcript')
                offset, limit = int(args.get('offset', 0)), int(args.get('limit', 80))
                if offset < 0 or not 1 <= limit <= 100:
                    raise ValueError('invalid_page')
                units = record['transcript']['units']
                ids = {u['id'] for u in units[offset:offset+limit]}
                return dict(transcript_id=args['transcript_id'], source_revision=record['source_revision'],
                            is_current=record['source_revision'] == (t.get('output_revision') or 'original'),
                            time_basis='audio_draft' if record.get('draft_segments') else 'source_revision',
                            draft_duration=record.get('draft_duration'),
                            total=len(units), offset=offset, units=units[offset:offset+limit],
                            repeat_candidates=[c for c in record['transcript']['repeat_candidates'] if c['first_id'] in ids])
            request_id = args.get('request_id')
            if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
                raise ValueError('request_id_required')
            signature = json.dumps([action, args], sort_keys=True)
            if request_id in self.requests:
                old_sig, old_result = self.requests[request_id]
                if old_sig != signature:
                    raise ValueError('request_id_conflict')
                return old_result
            if action not in ('analyze_video', 'process_video', 'transcribe_video', 'refine_video', 'prepare_ai_edit'):
                raise ValueError('unknown_action')
            t = self.tasks[self.selected]
            if any(task['status'] in ('processing', 'finishing') for task in self.tasks.values()) or any(j['status'] == 'running' and (j['kind'] != 'export' or j['video_id'] == self.selected) for j in self.jobs.values()):
                raise ValueError('busy')
            for review_id, pending in self.pending_reviews.items():
                if pending['base']['video_id'] == self.selected and action in ('process_video', 'refine_video'):
                    if action != 'refine_video' or args.get('_approved_review') != review_id:
                        raise ValueError('review_pending: duyệt hoặc hủy đề xuất AI trước khi xuất.')
            params = dict(id=self.selected)
            path, info, source_revision = t['input_path'], dict(t['info']), 'original'
            if action in ('transcribe_video', 'process_video', 'prepare_ai_edit'):
                source_revision = args.get('source_revision', (t.get('output_revision') or 'original') if action == 'prepare_ai_edit' else 'original')
                if source_revision != 'original':
                    if source_revision != t.get('output_revision'):
                        raise ValueError('stale_source: read selected video again')
                    path, info = t['output_path'], dict(t['output_info'])
            if action == 'refine_video':
                from speech_edit import refinement_ranges
                record = self.transcripts.get(args.get('transcript_id'))
                if not record or record['video_id'] != self.selected:
                    raise ValueError('unknown_transcript')
                if record['source_revision'] != (t.get('output_revision') or 'original'):
                    raise ValueError('stale_transcript: transcribe the current output again')
                source_revision, path, info = record['source_revision'], record['path'], record['info']
                if not isinstance(args.get('decisions'), list):
                    raise ValueError('decisions_required')
                if record.get('draft_segments'):
                    from speech_edit import map_draft_ranges
                    draft_ranges = refinement_ranges(record['transcript'], args.get('decisions'), record['draft_duration']) if args.get('decisions') else [[0, record['draft_duration']]]
                    ranges = map_draft_ranges(draft_ranges, record['draft_segments'])
                else:
                    ranges = refinement_ranges(record['transcript'], args.get('decisions'), info['duration'])
                args = dict(args, mode='keep_segments', segments=ranges, enable_bokeh=False)
                params['_smooth'] = args.get('smooth', True) is True
                params['_decisions'] = args['decisions']
            if action in ('process_video', 'refine_video'):
                params.update(_source_path=path, _source_info=info)
                mode = args.get('mode', 'auto_silence')
                if mode not in ('auto_silence', 'intro_outro', 'manual', 'keep_segments', 'none'):
                    raise ValueError('invalid_mode')
                target = float(args.get('target_mb', 24))
                start, end = float(args.get('start_time', 0)), float(args.get('end_time', info['duration']))
                blur = float(args.get('blur_radius', 25))
                if not all(math.isfinite(v) for v in (target, start, end, blur)) or not 1 <= target <= 4096 or not 0 <= blur <= 100:
                    raise ValueError('invalid_parameters')
                if mode == 'manual' and not 0 <= start < end <= info['duration']:
                    raise ValueError('invalid_trim_range')
                if mode == 'keep_segments':
                    ranges = args.get('segments')
                    if not isinstance(ranges, list) or not 1 <= len(ranges) <= 200:
                        raise ValueError('invalid_segments')
                    previous = 0.0
                    clean = []
                    for pair in ranges:
                        if not isinstance(pair, list) or len(pair) != 2:
                            raise ValueError('invalid_segments')
                        a, b = map(float, pair)
                        if not (math.isfinite(a) and math.isfinite(b) and previous <= a < b <= info['duration'] and b-a >= 0.1):
                            raise ValueError('invalid_segments')
                        clean.append([a, b])
                        previous = b
                    params['segments'] = clean
                params.update(hardware_encode=args.get('hardware_encode', False) is True, mode=mode, target_mb=target, start_time=start, end_time=end,
                              blur_radius=blur, enable_bokeh=args.get('enable_bokeh', False) is True,
                              then_compress=args.get('then_compress', True) is True)
                t.update(status='processing', progress=0, stage='Khởi động từ Codex MCP', result=None, error=None)
            if action in ('transcribe_video', 'prepare_ai_edit'):
                t.update(ai_status='recognizing', ai_stage='Đang nhận dạng lời nói cục bộ từ bản video hiện tại…')
            jid = str(uuid.uuid4())
            if action in ('process_video', 'refine_video'):
                t['mcp_job_id'] = jid
            self.jobs[jid] = dict(job_id=jid, video_id=self.selected, kind='export' if action in ('process_video', 'refine_video') else 'analysis', status='running')
            result = dict(job_id=jid, video_id=self.selected)
            self.requests[request_id] = signature, result
            def run():
                if action in ('process_video', 'refine_video'):
                    try:
                        self.worker(params['id'], params)
                    except Exception as e:
                        with self.lock:
                            self.tasks[params['id']].update(status='error', error=str(e))
                    finally:
                        with self.lock:
                            task = self.tasks[params['id']]
                            self.jobs[jid].update(status=task['status'], progress=task.get('progress', 0), result=task.get('result'), error=task.get('error'), source_revision=source_revision, output_revision=task.get('output_revision'))
                            if action == 'refine_video' and task['status'] == 'completed':
                                self.jobs[jid]['edit_decisions'] = args['decisions']
                                task.update(ai_status='refined', ai_stage='Đã tạo bản AI chỉnh sửa; bản trước vẫn được giữ lại.')
                                task.setdefault('refinement_history', []).append(dict(job_id=jid, source_revision=source_revision, output_revision=task.get('output_revision'), decisions=args['decisions'], segments=params['segments']))
                    return
                try:
                    if action in ('transcribe_video', 'prepare_ai_edit'):
                        from speech_edit import transcribe, prepare_review
                        draft_segments, draft_duration = None, None
                        if action == 'prepare_ai_edit':
                            transcript, draft_segments, draft_duration = prepare_review(path, info, self.analyze, args.get('language', 'vi'), args.get('pre_cut', True) is True)
                        else:
                            transcript = transcribe(path, info, args.get('language', 'vi'))
                        with self.lock:
                            t.update(ai_status='awaiting_ai', ai_stage='Đã có transcript của bản hiện tại để Codex đánh giá câu lặp và điểm nối.')
                            self.transcripts[jid] = dict(video_id=params['id'], source_revision=source_revision, path=path, info=info, transcript=transcript, draft_segments=draft_segments, draft_duration=draft_duration)
                        value = dict(transcript_id=jid, source_revision=source_revision, unit_count=len(transcript['units']), language=transcript['language'], draft_duration=draft_duration, video_rendered=False, next_step='Read every transcript page with get_transcript, assess meaning, then call refine_video with remove_ids, replacement_ids and reasons. For an audio draft, pass decisions=[] if no justified semantic cuts; this still renders the preliminary silence cuts once. Similarity hints are not decisions.')
                    else:
                        from video_segments import read_segments
                        value = dict(recording_segments=read_segments(path), silence=self.analyze(path, info.get('audio_stream_index'), info['duration']))
                    with self.lock:
                        self.jobs[jid].update(status='completed', result=value)
                except Exception as e:
                    with self.lock:
                        if action in ('transcribe_video', 'prepare_ai_edit'):
                            t.update(ai_status='error', ai_stage='Nhận dạng lời nói gặp lỗi; nội dung được giữ nguyên.')
                        self.jobs[jid].update(status='error', error=str(e))
            threading.Thread(target=run, daemon=True).start()
            return result


    def start_cloud(self, args):
        """One selected-model run: local audio draft -> remote text review -> local render."""
        from cloud_models import credentials, evaluate
        request_id = args.get('request_id')
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100:
            raise ValueError('request_id_required')
        target = float(args.get('target_mb', 24))
        if not math.isfinite(target) or not 1 <= target <= 4096:
            raise ValueError('invalid_target_mb')
        signature = json.dumps(args, sort_keys=True)
        with self.cloud_lock:
            if request_id in self.cloud_requests:
                old, result = self.cloud_requests[request_id]
                if old != signature:
                    raise ValueError('request_id_conflict')
                return result
            if any(r['status'] in ('running', 'awaiting_review') for r in self.cloud_runs.values()):
                raise ValueError('Một lượt AI đang chạy hoặc chờ duyệt. Hoàn tất hoặc hủy đề xuất trước khi bắt đầu lượt mới.')
            profile, key = credentials(args.get('profile_id'))
            base = {k: args[k] for k in ('instance_id', 'video_id', 'selection_revision')}
            prepared = self.call('prepare_ai_edit', dict(base, request_id=request_id + ':prepare', language='vi'))
            jid = str(uuid.uuid4())
            result = dict(job_id=jid, video_id=base['video_id'])
            self.cloud_requests[request_id] = signature, result
            with self.lock:
                self.cloud_runs[jid] = dict(result, kind='cloud', status='running', stage='Đang chuẩn bị lời nói cục bộ', model=profile['model'])

        def wait_job(job_id):
            deadline = time.monotonic() + 7200
            while time.monotonic() < deadline:
                state = self.call('get_job', dict(job_id=job_id))
                if state['status'] == 'error':
                    raise ValueError(state.get('error') or 'Xử lý thất bại.')
                if state['status'] == 'completed':
                    return state
                time.sleep(.2)
            raise ValueError('Tác vụ quá thời gian chờ; kiểm tra trạng thái trong ứng dụng.')

        def run():
            try:
                preparation = wait_job(prepared['job_id'])
                transcript_id = preparation['result']['transcript_id']
                with self.lock:
                    record = self.transcripts[transcript_id]
                    if self.selected != base['video_id'] or self.revision != base['selection_revision']:
                        raise ValueError('Video đang chọn đã đổi. Chưa gửi transcript tới AI.')
                    self.cloud_runs[jid]['stage'] = 'Đang gửi transcript cho ' + profile['name']
                    self.tasks[base['video_id']].update(ai_stage='AI đang đánh giá transcript: ' + profile['name'])
                review = evaluate(profile, key, record['transcript'])
                from speech_edit import map_draft_ranges
                by_id = {u['id']: u for u in record['transcript']['units']}
                rows = []
                for index, decision in enumerate(review['decisions']):
                    removed = sorted((by_id[uid] for uid in decision['remove_ids']), key=lambda u: u['start'])
                    ranges = [[u['start'], u['end']] for u in removed]
                    source_ranges = map_draft_ranges(ranges, record['draft_segments']) if record.get('draft_segments') else ranges
                    rows.append(dict(index=index, removed_text=' '.join(u['text'] for u in removed),
                        replacement_text=' '.join(by_id[uid]['text'] for uid in decision.get('replacement_ids', [])),
                        reason=decision['reason'], source_ranges=source_ranges))
                with self.lock:
                    self.pending_reviews[jid] = dict(base=base, transcript_id=transcript_id,
                        decisions=review['decisions'], target_mb=args.get('target_mb', 24),
                        then_compress=args.get('then_compress', True), hardware_encode=args.get('hardware_encode', False) is True)
                    preliminary_cuts, cursor = [], 0.0
                    for s, e in record.get('draft_segments') or [[0, record['info']['duration']]]:
                        if s > cursor + .01:
                            preliminary_cuts.append([cursor, s])
                        cursor = e
                    if cursor < record['info']['duration'] - .01:
                        preliminary_cuts.append([cursor, record['info']['duration']])
                    self.cloud_runs[jid].update(preliminary_cuts=preliminary_cuts, status='awaiting_review', stage='Chờ bạn duyệt đề xuất trước khi xuất',
                        review=review, review_rows=rows, draft_duration=record.get('draft_duration'),
                        source_duration=record['info']['duration'])
                    self.tasks[base['video_id']].update(ai_stage='AI đã phân tích. Duyệt đề xuất rồi bấm Duyệt và xuất.')
            except Exception as e:
                with self.lock:
                    self.cloud_runs[jid].update(status='error', error=str(e))
                    self.tasks[base['video_id']].update(ai_stage='AI chưa hoàn tất; bản video trước được giữ nguyên.')
        threading.Thread(target=run, daemon=True).start()
        return result


    def approve_review(self, args):
        jid = args.get('job_id')
        with self.cloud_lock:
            with self.lock:
                run = self.cloud_runs.get(jid)
                if not run:
                    raise ValueError('unknown_review')
                indexes = args.get('decision_indexes')
                if not isinstance(indexes, list) or any(type(i) is not int for i in indexes) or len(indexes) != len(set(indexes)):
                    raise ValueError('invalid_review_selection')
                if run.get('export_job_id'):
                    if sorted(indexes) != run.get('approved_indexes'):
                        raise ValueError('review_already_submitted')
                    return dict(job_id=jid, export_job_id=run['export_job_id'])
                pending = self.pending_reviews.get(jid)
                if run['status'] != 'awaiting_review' or not pending:
                    raise ValueError('review_not_awaiting_approval')
                if any(i < 0 or i >= len(pending['decisions']) for i in indexes):
                    raise ValueError('invalid_review_selection')
                decisions = [pending['decisions'][i] for i in sorted(indexes)]
            export = self.call('refine_video', dict(pending['base'], transcript_id=pending['transcript_id'],
                request_id=jid + ':approved-render', decisions=decisions, smooth=True, _approved_review=jid,
                then_compress=pending['then_compress'], target_mb=pending['target_mb'], hardware_encode=args.get('hardware_encode', pending.get('hardware_encode', False)) is True))
            with self.lock:
                run.update(status='running', stage='Đang xuất các thay đổi bạn đã duyệt',
                           approved_indexes=sorted(indexes), export_job_id=export['job_id'])
                self.pending_reviews.pop(jid, None)
        def finish():
            try:
                while True:
                    state = self.call('get_job', dict(job_id=export['job_id']))
                    if state['status'] in ('completed', 'error'):
                        with self.lock:
                            run.update(status=state['status'], result=state.get('result'), error=state.get('error'),
                                       stage='Hoàn tất' if state['status'] == 'completed' else 'Xuất gặp lỗi')
                        return
                    time.sleep(.2)
            except Exception as e:
                with self.lock:
                    run.update(status='error', error=str(e))
        threading.Thread(target=finish, daemon=True).start()
        return dict(job_id=jid, export_job_id=export['job_id'])

    def cancel_review(self, jid):
        with self.cloud_lock:
            with self.lock:
                run = self.cloud_runs.get(jid)
                if not run or run['status'] != 'awaiting_review':
                    raise ValueError('review_not_awaiting_approval')
                self.pending_reviews.pop(jid, None)
                run.update(status='cancelled', stage='Đã hủy đề xuất, chưa xuất video')
                self.tasks[run['video_id']].update(ai_stage='Đã hủy đề xuất AI. Video được giữ nguyên.')
        return dict(job_id=jid, status='cancelled')
