"""End-to-end STDIO -> authenticated HTTP -> real FFmpeg worker smoke test."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['VIDEO_MCP_RUNTIME_DIR'] = str(Path(tmp) / 'runtime')
        import app
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        sample = str(Path(tmp) / 'sample.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=30', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '2', '-c:v', 'libx264', '-c:a', 'aac', sample], check=True)
        app.TEMP_DIR = tmp
        server, url = app.start_server(18900)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            try:
                urllib.request.urlopen(urllib.request.Request(url + '/api/mcp', data=b'{}'))
                raise AssertionError('unauthenticated request accepted')
            except urllib.error.HTTPError as e:
                assert e.code == 401
            app.TASKS['smoke'] = dict(id='smoke', filename='sample.mp4', input_path=sample, info=app.get_video_info(sample), status='ready')
            with app.TASKS_LOCK:
                app.CONTROL.select('smoke')
            params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'mcp_bridge.py')], env=dict(os.environ))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    listed = await client.list_tools()
                    assert len(listed.tools) == 14
                    async def call(name, args):
                        r = await client.call_tool(name, args)
                        assert not r.isError, r
                        return json.loads(r.content[0].text)
                    snapshot = await call('get_selected_video', {})
                    assert snapshot['video_id'] == 'smoke'
                    a = {k: snapshot[k] for k in ('instance_id', 'video_id', 'selection_revision')}
                    # No prior export: prepare audio/transcript, then render only once.
                    from unittest.mock import patch
                    fixture = dict(language='en', units=[dict(id='draft-a', start=0, end=.6, text='Keep this speech.', needs_review=False)], repeat_candidates=[])
                    with patch('speech_edit.prepare_review', return_value=(fixture, [[.1, .8], [1.2, 1.9]], 1.4)):
                        prepared = await call('prepare_ai_edit', dict(a, request_id='prepare-first'))
                        for _ in range(100):
                            prep = await call('get_job', dict(instance_id=snapshot['instance_id'], job_id=prepared['job_id']))
                            if prep['status'] in ('completed', 'error'):
                                break
                            await asyncio.sleep(.05)
                        assert prep['status'] == 'completed', prep
                    assert not app.TASKS['smoke'].get('output_revision')
                    assert not app.TASKS['smoke'].get('output_path')
                    draft_page = await call('get_transcript', dict(a, transcript_id=prep['result']['transcript_id']))
                    assert draft_page['time_basis'] == 'audio_draft'
                    finish = await call('refine_video', dict(a, transcript_id=prep['result']['transcript_id'], request_id='finish-first', decisions=[], then_compress=False))
                    for _ in range(200):
                        finished = await call('get_job', dict(instance_id=snapshot['instance_id'], job_id=finish['job_id']))
                        if finished['status'] in ('completed', 'error'):
                            break
                        await asyncio.sleep(.05)
                    assert finished['status'] == 'completed', finished
                    assert 1.2 < app.get_video_info(app.TASKS['smoke']['output_path'])['duration'] < 1.5
                    print('PASS: select -> prepare (no video output) -> AI decisions=[] -> single final render.')

                    bad = await client.call_tool('process_video', dict(a, selection_revision=0, request_id='bad'))
                    assert bad.isError
                    a.update(request_id='render-one', mode='keep_segments', segments=[[.2, .7], [1, 1.5]], then_compress=False)
                    job = await call('process_video', a)
                    retry = await call('process_video', a)
                    assert job == retry
                    for _ in range(100):
                        state = await call('get_job', dict(instance_id=snapshot['instance_id'], job_id=job['job_id']))
                        if state['status'] in ('completed', 'error'):
                            break
                        await asyncio.sleep(.1)
                    assert state['status'] == 'completed', state
                    output = app.TASKS['smoke']['output_path']
                    info = app.get_video_info(output)
                    assert .8 < info['duration'] < 1.3, info
                    # Bind a deterministic transcript to the already cut output, not original.
                    from speech_edit import refinement_ranges
                    snapshot = await call('get_selected_video', {})
                    assert snapshot['has_processed_output']
                    original_output = output
                    app.CONTROL.transcripts['fixture'] = dict(video_id='smoke', source_revision=snapshot['source_revision'], path=output, info=info,
                        transcript=dict(units=[dict(id='a', start=0, end=.2, text='Giữ', needs_review=False),
                                               dict(id='b', start=.3, end=.6, text='Nói lại', needs_review=False),
                                               dict(id='c', start=.7, end=.95, text='Giữ câu đầy đủ', needs_review=False)], repeat_candidates=[]))
                    args = {k: snapshot[k] for k in ('instance_id', 'video_id', 'selection_revision')}
                    page = await call('get_transcript', dict(args, transcript_id='fixture'))
                    assert page['is_current']
                    decision = dict(remove_ids=['b'], replacement_ids=['c'], reason_type='retake', reason='Fixture retake replaced by complete unit c.')
                    job2 = await call('refine_video', dict(args, transcript_id='fixture', request_id='refine-one', decisions=[decision], then_compress=False))
                    for _ in range(200):
                        state2 = await call('get_job', dict(instance_id=snapshot['instance_id'], job_id=job2['job_id']))
                        if state2['status'] in ('completed', 'error'):
                            break
                        await asyncio.sleep(.1)
                    assert state2['status'] == 'completed', state2
                    refined = app.TASKS['smoke']['output_path']
                    assert refined != original_output and Path(original_output).exists()
                    refined_info = app.get_video_info(refined)
                    assert .4 < refined_info['duration'] < .75, refined_info
                    stale = await client.call_tool('refine_video', dict(args, transcript_id='fixture', request_id='stale-refine', decisions=[decision]))
                    assert stale.isError
                    # App settings HTTP + saved model + cloud orchestration + real render.
                    import cloud_models
                    def local_api(action, data, origin=url):
                        req = urllib.request.Request(url + '/api/ai/' + action, data=json.dumps(data).encode(), headers={'Origin': origin, 'Content-Type': 'application/json'})
                        with urllib.request.urlopen(req) as response:
                            return json.load(response)
                    with patch.object(cloud_models, 'CONFIG', Path(tmp) / 'ai-config.json'), patch.object(cloud_models, '_SESSION_KEYS', {}):
                        try:
                            local_api('settings', {}, 'https://untrusted.example')
                            raise AssertionError('foreign origin accepted')
                        except urllib.error.HTTPError as e:
                            assert e.code == 403
                        saved = local_api('save', dict(name='Mock provider', base_url='https://example.test/v1', model='test-chat', api_key='not-a-real-key'))
                        assert 'not-a-real-key' not in json.dumps(saved)
                        app.TASKS['cloud'] = dict(id='cloud', filename='cloud.mp4', input_path=sample, info=app.get_video_info(sample), status='ready')
                        with app.TASKS_LOCK:
                            app.CONTROL.select('cloud')
                        snap = await call('get_selected_video', {})
                        cloud_args = {k: snap[k] for k in ('instance_id', 'video_id', 'selection_revision')}
                        with patch('speech_edit.prepare_review', return_value=(fixture, [[.1, .8], [1.2, 1.9]], 1.4)), patch.object(cloud_models, 'evaluate', return_value=dict(decisions=[], summary='Không có câu thừa.', model='test-chat', profile_name='Mock provider')):
                            cloud_job = await call('auto_edit_with_model', dict(cloud_args, profile_id=saved['selected_id'], request_id='cloud-render', then_compress=False))
                            for _ in range(300):
                                cloud_state = await call('get_job', dict(instance_id=snap['instance_id'], job_id=cloud_job['job_id']))
                                if cloud_state['status'] != 'running':
                                    break
                                await asyncio.sleep(.1)
                            assert cloud_state['status'] == 'awaiting_review', cloud_state
                            assert not app.TASKS['cloud'].get('output_path')
                            req = urllib.request.Request(url + '/api/review-source?job_id=' + cloud_job['job_id'], headers={'Range':'bytes=0-31'})
                            with urllib.request.urlopen(req) as source_response:
                                assert source_response.status == 206
                                assert len(source_response.read()) == 32
                                assert source_response.headers['Accept-Ranges'] == 'bytes'
                            await call('approve_ai_review', dict(instance_id=snap['instance_id'], job_id=cloud_job['job_id'], decision_indexes=[]))
                            for _ in range(300):
                                cloud_state = await call('get_job', dict(instance_id=snap['instance_id'], job_id=cloud_job['job_id']))
                                if cloud_state['status'] != 'running': break
                                await asyncio.sleep(.1)
                            assert cloud_state['status'] == 'completed', cloud_state
                        assert Path(app.TASKS['cloud']['output_path']).exists()
                        assert cloud_state['review']['model'] == 'test-chat'
                        print('PASS: settings Origin protection, secret-free profile responses, chosen cloud model orchestration (mock API), review required, ranged source preview, approved local video render.')
                    asr_source = os.environ.get('VIDEO_ASR_SMOKE_SOURCE')
                    if asr_source:
                        app.TASKS['speech'] = dict(id='speech', filename=Path(asr_source).name, input_path=asr_source, info=app.get_video_info(asr_source), status='ready')
                        with app.TASKS_LOCK:
                            app.CONTROL.select('speech')
                        snap = await call('get_selected_video', {})
                        speech_args = {k: snap[k] for k in ('instance_id', 'video_id', 'selection_revision', 'source_revision')}
                        speech_args.pop('source_revision')
                        speech_job = await call('prepare_ai_edit', dict(speech_args, request_id='real-speech'))
                        for _ in range(600):
                            speech_state = await call('get_job', dict(instance_id=snap['instance_id'], job_id=speech_job['job_id']))
                            if speech_state['status'] in ('completed', 'error'):
                                break
                            await asyncio.sleep(.2)
                        assert speech_state['status'] == 'completed', speech_state
                        speech_page = await call('get_transcript', dict(instance_id=snap['instance_id'], video_id=snap['video_id'], selection_revision=snap['selection_revision'], transcript_id=speech_state['result']['transcript_id']))
                        assert speech_page['units'] and speech_page['is_current']
                        assert speech_page['time_basis'] == 'audio_draft'
                        assert not app.TASKS['speech'].get('output_path')
                        print('PASS: real offline Vietnamese ASR through MCP, transcript units:', speech_page['total'])
                    print('PASS: 14 MCP tools, authentication, stale selection, idempotent export, current-cut transcript, semantic decision validation, sequential rendering with audio fades, immutable previous output, stale transcript rejection.')
        finally:
            server.shutdown()
            server.server_close()
            app.CONTROL.close()


asyncio.run(main())
