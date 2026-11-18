"""The platform selector, and that the Windows and Linux packages offer the same functions to the shared code."""
import importlib
import inspect
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
import platform_support  # noqa: E402

# module -> the names the shared code calls on both systems
SHARED_FUNCTIONS = {
    'audio': ['control_audio', 'read_audio', 'read_mixer'],
    'media': ['MediaReader', 'control_media'],
    'session': ['locked'],
    'filelock': ['lock', 'unlock'],
    'input': ['bring_to_front', 'focus_existing_process', 'foreground_context', 'is_neutral_window', 'matches_foreground',
              'process_window', 'send_hotkey', 'send_mouse', 'send_text', 'set_clipboard', 'window_action'],
}
FCNTL = re.compile(r'^\s*(?:import fcntl|from fcntl\b)', re.MULTILINE)


class SelectorTests(unittest.TestCase):
    def test_the_system_names_map_to_one_platform(self):
        self.assertEqual(platform_support.detect('win32'), 'windows')
        self.assertEqual(platform_support.detect('linux'), 'linux')
        self.assertEqual(platform_support.detect('linux2'), 'linux')

    def test_other_systems_are_refused_with_their_name(self):
        for name in ('darwin', 'freebsd14', 'cygwin', 'aix'):
            with self.assertRaisesRegex(platform_support.UnsupportedPlatform, name):
                platform_support.detect(name)

    def test_this_system_has_exactly_one_flag(self):
        self.assertNotEqual(platform_support.IS_WINDOWS, platform_support.IS_LINUX)
        self.assertEqual(platform_support.NAME, 'windows' if platform_support.IS_WINDOWS else 'linux')

    def test_the_host_does_not_start_on_macos(self):
        code = ("import sys; sys.platform = 'darwin'; sys.path.insert(0, 'host'); import desktop")
        result = subprocess.run([sys.executable, '-I', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('UnsupportedPlatform', result.stderr)
        self.assertIn("not on 'darwin'", result.stderr)


class ParityTests(unittest.TestCase):
    """Both packages are imported on every system, so a change on one side that the other lacks fails on either."""

    def test_both_packages_offer_the_same_names_with_the_same_required_parameters(self):
        """The shared code passes the required parameters positionally. A side may add optional parameters (the Linux
        functions take `run`, `now` and `reader` so tests can replace a command) and may name them differently."""
        for module, names in SHARED_FUNCTIONS.items():
            windows = importlib.import_module(f'platform_windows.{module}')
            linux = importlib.import_module(f'platform_linux.{module}')
            for name in names:
                with self.subTest(module=module, name=name):
                    self.assertTrue(hasattr(windows, name), f'platform_windows.{module}.{name} is missing')
                    self.assertTrue(hasattr(linux, name), f'platform_linux.{module}.{name} is missing')
                    self.assertEqual(self.required(getattr(windows, name)), self.required(getattr(linux, name)))

    @staticmethod
    def required(item):
        """How many parameters have no default; for a class, those of its __init__."""
        target = item.__init__ if inspect.isclass(item) else item
        return sum(1 for p in inspect.signature(target).parameters.values()
                   if p.name != 'self' and p.default is p.empty and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD))

    def test_the_desktop_facade_exports_every_shared_input_name(self):
        import desktop
        for name in SHARED_FUNCTIONS['input']:
            self.assertTrue(hasattr(desktop, name), name)


class LayeringTests(unittest.TestCase):
    def test_shared_modules_do_not_import_fcntl(self):
        offenders = [path.name for path in sorted((ROOT / 'host').glob('*.py'))
                     if FCNTL.search(path.read_text(encoding='utf-8'))]
        self.assertEqual(offenders, [], 'the Linux file lock is platform_linux/filelock.py')

    def test_the_linux_package_imports_nothing_from_the_windows_package(self):
        offenders = [path.name for path in sorted((ROOT / 'host/platform_linux').glob('*.py'))
                     if 'platform_windows' in re.sub(r'#.*|""".*?"""', '', path.read_text(encoding='utf-8'), flags=re.S)]
        self.assertEqual(offenders, [])

    def test_the_windows_package_imports_nothing_from_the_linux_package(self):
        offenders = [path.name for path in sorted((ROOT / 'host/platform_windows').glob('*.py'))
                     if 'platform_linux' in re.sub(r'#.*|""".*?"""', '', path.read_text(encoding='utf-8'), flags=re.S)]
        self.assertEqual(offenders, [])


if __name__ == '__main__':
    unittest.main()
