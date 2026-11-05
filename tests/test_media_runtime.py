import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import media_runtime as runtime


class MediaRuntimeTests(unittest.TestCase):
    def test_job_lock_blocks_other_job_and_releases_after_error(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runtime, 'LOCK_PATH', Path(tmp) / 'media.lock'):
            with self.assertRaisesRegex(ValueError, 'test'):
                with runtime.media_job():
                    with self.assertRaisesRegex(RuntimeError, 'tác vụ video khác'):
                        with runtime.media_job():
                            pass
                    raise ValueError('test')
            with runtime.media_job():
                pass

    def test_large_stderr_cannot_block_process_or_second_run(self):
        command = [sys.executable, '-c', 'import sys;sys.stderr.write("x"*200000);print("PROGRESS: 100")']
        with patch.object(runtime, 'memory_problem', return_value=None):
            for _ in range(2):
                lines = []
                runtime.run_media(command, lines.append)
                self.assertIn('PROGRESS: 100', lines)

    def test_pressure_guard_stops_and_reaps_child(self):
        created = []
        original = subprocess.Popen
        def spawn(*a, **kw):
            p = original(*a, **kw); created.append(p); return p
        with patch.object(runtime.subprocess, 'Popen', side_effect=spawn), patch.object(runtime, 'memory_problem', return_value='memory cutoff'):
            with self.assertRaisesRegex(RuntimeError, 'memory cutoff'):
                runtime.run_media([sys.executable, '-c', 'import time;time.sleep(30)'])
        self.assertTrue(created)
        self.assertTrue(all(p.poll() is not None for p in created))


if __name__ == '__main__':
    unittest.main()
