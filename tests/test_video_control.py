import threading
import unittest
from video_mcp import VideoControl


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.tasks = {'a': dict(filename='a.mov', input_path='unused', info={'duration': 10}, status='ready'),
                      'b': dict(filename='b.mov', input_path='unused', info={'duration': 20}, status='ready')}
        def worker(tid, params):
            self.calls.append((tid, params))
            self.tasks[tid]['status'] = 'completed'
        self.c = VideoControl(self.tasks, threading.Lock(), worker, lambda *a: {})
        self.c.select('a')
        self.args = dict(instance_id=self.c.instance_id, video_id='a', selection_revision=1, request_id='one', mode='keep_segments', segments=[[1, 3], [5, 8]])

    def test_changed_selection_rejects_old_command(self):
        self.c.select('b')
        with self.assertRaisesRegex(ValueError, 'stale_selection'):
            self.c.call('process_video', self.args)
        self.assertFalse(self.calls)

    def test_retry_does_not_duplicate_export(self):
        a = self.c.call('process_video', self.args)
        b = self.c.call('process_video', self.args)
        self.assertEqual(a, b)
        with self.assertRaisesRegex(ValueError, 'request_id_conflict'):
            self.c.call('process_video', dict(self.args, target_mb=10))

    def test_invalid_ranges_do_not_start_worker(self):
        for ranges in [[], [[5, 4]], [[0, 6], [5, 8]], [[0, 11]], [[0, float('nan')]]]:
            with self.assertRaises(ValueError):
                self.c.call('process_video', dict(self.args, segments=ranges))
        self.assertFalse(self.calls)

    def test_export_job_result_survives_next_export(self):
        first = self.c.call('process_video', self.args)
        import time
        for _ in range(100):
            if self.c.call('get_job', first)['status'] == 'completed':
                break
            time.sleep(.005)
        self.tasks['a']['status'] = 'processing'
        self.assertEqual(self.c.call('get_job', first)['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
