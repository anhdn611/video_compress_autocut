import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import cloud_models as cloud
from video_mcp import VideoControl


class CloudModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = patch.object(cloud, 'CONFIG', Path(self.tmp.name) / 'models.json')
        self.config.start()
        self.keys = patch.object(cloud, '_SESSION_KEYS', {})
        self.keys.start()
        self.data = dict(name='Review', model='test-chat', base_url='https://example.test/v1', api_key='private-key-never-in-file')
        self.units = [dict(id='a', start=0, end=1, text='Xin chào bạn.', needs_review=False), dict(id='b', start=2, end=3, text='Xin chào bạn.', needs_review=False)]
        self.decision = dict(remove_ids=['a'], replacement_ids=['b'], reason_type='duplicate', reason='Lặp câu chào, giữ câu b đầy đủ.')

    def tearDown(self):
        self.keys.stop(); self.config.stop(); self.tmp.cleanup()

    def test_keys_are_not_in_config_or_public_listing(self):
        saved = cloud.save_profile(self.data)
        self.assertNotIn(self.data['api_key'], cloud.CONFIG.read_text())
        self.assertNotIn(self.data['api_key'], json.dumps(saved))
        profile, key = cloud.credentials(saved['selected_id'])
        self.assertEqual(key, self.data['api_key'])
        self.assertTrue(saved['profiles'][0]['has_key'])
        cloud.delete_profile(profile['id'])
        self.assertEqual(cloud.profiles()['profiles'], [])

    def test_cannot_reuse_credentials_at_different_endpoint(self):
        saved = cloud.save_profile(self.data)
        with self.assertRaises(ValueError):
            cloud.save_profile(dict(self.data, id=saved['selected_id'], base_url='https://different.test'))

    def test_only_allowlisted_text_fields_leave_machine(self):
        def request(profile, key, endpoint, body):
            self.assertEqual(endpoint, '/chat/completions')
            sent = json.loads(body['messages'][1]['content'])
            self.assertEqual(set(sent), {'language', 'units'})
            self.assertNotIn('private.mov', json.dumps(body))
            self.assertNotIn('GPS', json.dumps(body))
            self.assertEqual(set(sent['units'][0]), {'id', 'start', 'end', 'text', 'needs_review'})
            return dict(choices=[dict(finish_reason='stop', message=dict(content=json.dumps(dict(decisions=[self.decision], summary='Bỏ câu lặp.'))))])
        transcript = dict(language='vi', units=[dict(u, path='/private.mov', GPS='secret') for u in self.units], video=b'private')
        with patch.object(cloud, 'request_json', side_effect=request):
            reviewed = cloud.evaluate(dict(model='test', name='Test'), 'key', transcript)
        self.assertEqual(reviewed['decisions'], [self.decision])

    def test_invented_ids_and_partial_response_are_rejected(self):
        for choice in [dict(finish_reason='length', message=dict(content='{}')),
                       dict(finish_reason='stop', message=dict(content=json.dumps(dict(decisions=[dict(self.decision, remove_ids=['invented'])]))))]:
            with patch.object(cloud, 'request_json', return_value=dict(choices=[choice])):
                with self.assertRaises(ValueError):
                    cloud.evaluate(dict(model='test', name='Test'), 'key', dict(units=self.units))

    def test_end_to_end_orchestration_without_real_provider(self):
        saved = cloud.save_profile(self.data)
        tasks = {'v': dict(filename='source.mov', input_path='source.mov', info=dict(duration=4, audio_stream_index=0), status='ready')}
        calls = []
        def worker(tid, params):
            calls.append(params)
            tasks[tid].update(status='completed', output_revision='new', result={'duration': 2})
        control = VideoControl(tasks, threading.Lock(), worker, lambda *a: {})
        control.select('v')
        args = dict(instance_id=control.instance_id, video_id='v', selection_revision=1, request_id='cloud-one', profile_id=saved['selected_id'])
        fixture = dict(language='vi', units=self.units, repeat_candidates=[])
        with patch('speech_edit.prepare_review', return_value=(fixture, [[0, 4]], 4)), patch.object(cloud, 'evaluate', return_value=dict(decisions=[self.decision], summary='Bỏ lặp.', model='test', profile_name='Review')):
            run = control.start_cloud(args)
            self.assertEqual(control.start_cloud(args), run)
            for _ in range(200):
                state = control.call('get_job', run)
                if state['status'] != 'running': break
                time.sleep(.01)
            self.assertEqual(state['status'], 'awaiting_review', state)
            self.assertEqual(calls, [])
            with self.assertRaisesRegex(ValueError, 'review_pending'):
                control.call('process_video', dict(args, request_id='bypass-review'))
            self.assertFalse(tasks['v'].get('output_revision'))
            control.approve_review(dict(job_id=run['job_id'], decision_indexes=[0]))
            for _ in range(200):
                state = control.call('get_job', run)
                if state['status'] != 'running': break
                time.sleep(.01)
        self.assertEqual(state['status'], 'completed', state)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['segments'], [[1.5, 4]])

    def test_cancel_and_stale_review_never_render(self):
        tasks = {'v': dict(filename='v', input_path='v', info={'duration': 4}, status='ready')}
        calls = []
        c = VideoControl(tasks, threading.Lock(), lambda *a: calls.append(a), lambda *a: {})
        c.select('v')
        c.cloud_runs['review'] = dict(job_id='review', video_id='v', status='awaiting_review')
        c.pending_reviews['review'] = dict(base=dict(instance_id=c.instance_id, video_id='v', selection_revision=1), transcript_id='t', decisions=[], target_mb=24, then_compress=False)
        c.select(None)
        with self.assertRaisesRegex(ValueError, 'stale_selection'):
            c.approve_review(dict(job_id='review', decision_indexes=[]))
        self.assertEqual(c.cloud_runs['review']['status'], 'awaiting_review')
        c.cancel_review('review')
        self.assertEqual(c.cloud_runs['review']['status'], 'cancelled')
        self.assertEqual(calls, [])
        with self.assertRaises(ValueError):
            c.approve_review(dict(job_id='review', decision_indexes=[]))


if __name__ == '__main__':
    unittest.main()
