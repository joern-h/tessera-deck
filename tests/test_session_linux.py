"""Linux session pieces: the screen lock state, and that a timed-out command takes its children with it."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
import action_runner
from platform_linux import session


def asking(answers):
    """A fake `run` that answers by the program and the screensaver service in the command."""
    calls = []

    def run(args):
        calls.append(args)
        text = ' '.join(args)
        for key, value in answers.items():
            if key in text:
                return value
        return ''
    run.calls = calls
    return run


class LockTests(unittest.TestCase):
    def setUp(self):
        session._cache = (0.0, False)

    def test_logind_locked_hint_means_locked(self):
        self.assertTrue(session.locked(run=asking({'loginctl': 'yes\n'})))

    def test_a_desktop_screensaver_that_is_active_means_locked(self):
        run = asking({'loginctl': 'no\n', 'ListNames': "(['org.cinnamon.ScreenSaver', ':1.5'],)", 'org.cinnamon.ScreenSaver.GetActive': '(true,)\n'})
        self.assertTrue(session.locked(run=run))

    def test_nothing_locked_and_missing_tools_count_as_unlocked(self):
        self.assertFalse(session.locked(run=asking({'loginctl': 'no\n', 'ListNames': "(['org.cinnamon.ScreenSaver'],)",
                                                    'GetActive': '(false,)\n'})))
        session._cache = (0.0, False)
        self.assertFalse(session.locked(run=asking({})))

    def test_the_answer_is_kept_for_a_moment(self):
        run = asking({'loginctl': 'yes\n'})
        clock = [100.0]
        session.locked(now=lambda: clock[0], run=run)
        asked = len(run.calls)
        clock[0] += 1.0
        self.assertTrue(session.locked(now=lambda: clock[0], run=run))
        self.assertEqual(len(run.calls), asked)
        clock[0] += 2.0
        session.locked(now=lambda: clock[0], run=run)
        self.assertGreater(len(run.calls), asked)


@unittest.skipUnless(os.name == 'posix', 'POSIX only')
class CommandTreeTests(unittest.TestCase):
    def test_a_command_that_times_out_is_killed_with_everything_it_started(self):
        with tempfile.TemporaryDirectory() as folder:
            pid_file = Path(folder, 'child.pid')
            command = f'sleep 30 & echo $! > {pid_file}; wait'
            with self.assertRaises(action_runner.CommandFailed):
                action_runner.run_command(command, 0.6, threading.Event())
            child = int(pid_file.read_text())
            time.sleep(0.3)
            with self.assertRaises(ProcessLookupError):
                os.kill(child, 0)


if __name__ == '__main__':
    unittest.main()
