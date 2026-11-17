"""The right-click menu of the Linux tray icon: what it lists, how clicks are routed, and a real Tk menu on Xvfb."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
try:
    import pystray
except ImportError:  # the host's venv has it; a bare system Python may not
    pystray = None
from platform_linux import tray_menu


class FakeIcon:
    def __init__(self, calls):
        self.calls = calls

    def __call__(self):  # the default action, as pystray's Icon is called on a left click
        self.calls.append('default')


def fake_icon(calls, has_menu=False):
    def action(name):
        return lambda icon, item=None: calls.append(name)

    def items():
        yield pystray.MenuItem('Status: connected', None, enabled=False)
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem('Open editor', action('open'), default=True)
        yield pystray.MenuItem('Stop host', action('stop'))
        yield pystray.MenuItem('Start with the desktop', action('auto'), checked=lambda item: True)
        yield pystray.MenuItem('Sub', pystray.Menu(pystray.MenuItem('A', action('a')),
                                                   pystray.MenuItem('B', action('b'), checked=lambda item: True, radio=True)))
        yield pystray.Menu.SEPARATOR
        yield pystray.MenuItem('Quit tray', action('quit'))
        yield pystray.MenuItem('Quit and stop host', action('quit-stop'))
    icon = FakeIcon(calls)
    icon.menu, icon.HAS_MENU, icon._message_handlers = pystray.Menu(items), has_menu, {}
    icon._log = types.SimpleNamespace(error=lambda *a, **k: calls.append('error'))
    return icon


@unittest.skipIf(pystray is None, 'needs pystray')
class DescribeTests(unittest.TestCase):
    def test_the_menu_is_read_as_plain_rows(self):
        rows = tray_menu.describe(fake_icon([]).menu, pystray.Menu.SEPARATOR)
        self.assertEqual([row.get('text', '---') for row in rows],
                         ['Status: connected', '---', 'Open editor', 'Stop host', 'Start with the desktop', 'Sub', '---',
                          'Quit tray', 'Quit and stop host'])
        self.assertFalse(rows[0]['enabled'])
        self.assertTrue(rows[2]['default'])
        self.assertEqual([row['text'] for row in rows[5]['submenu']], ['A', 'B'])

    def test_a_ticked_item_and_a_chosen_radio_item_are_marked(self):
        rows = tray_menu.describe(fake_icon([]).menu, pystray.Menu.SEPARATOR)
        self.assertTrue(tray_menu.label(rows[4]).startswith('✓ '))
        self.assertTrue(tray_menu.label(rows[5]['submenu'][1]).startswith('● '))
        self.assertEqual(tray_menu.label(rows[3]), 'Stop host')


@unittest.skipIf(pystray is None, 'needs pystray')
class ClickTests(unittest.TestCase):
    def test_left_opens_the_default_action_and_right_opens_the_menu(self):
        try:
            import Xlib.X
        except ImportError:
            self.skipTest('needs python-xlib')
        calls, opened = [], []
        icon = fake_icon(calls)
        self.assertTrue(tray_menu.attach(icon, pystray.Menu.SEPARATOR))
        icon.tray_menu.show = lambda x, y: opened.append((x, y))
        handler = icon._message_handlers[Xlib.X.ButtonPress]
        handler(types.SimpleNamespace(detail=1, root_x=5, root_y=6))
        handler(types.SimpleNamespace(detail=3, root_x=40, root_y=50))
        handler(types.SimpleNamespace(detail=2, root_x=1, root_y=1))
        self.assertEqual((calls, opened), (['default'], [(40, 50)]))

    def test_an_icon_that_has_a_menu_is_left_alone(self):
        self.assertFalse(tray_menu.attach(fake_icon([], has_menu=True), pystray.Menu.SEPARATOR))


@unittest.skipUnless(pystray is not None and sys.platform.startswith('linux')
                     and all(shutil.which(tool) for tool in ('Xvfb', 'xdotool')), 'needs pystray, Xvfb and xdotool')
class RealMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter  # noqa: F401
        except ImportError:
            raise unittest.SkipTest('needs tkinter')
        cls.server = subprocess.Popen(['Xvfb', '-displayfd', '1', '-screen', '0', '1024x768x24'], stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, text=True)
        cls.display = ':' + cls.server.stdout.readline().strip()
        cls.saved = os.environ.get('DISPLAY')
        os.environ['DISPLAY'] = cls.display

    @classmethod
    def tearDownClass(cls):
        if cls.saved is None:
            os.environ.pop('DISPLAY', None)
        else:
            os.environ['DISPLAY'] = cls.saved
        cls.server.terminate()
        cls.server.wait(5)

    def test_choosing_an_entry_with_the_keyboard_runs_its_action_and_only_one_menu_opens_at_a_time(self):
        calls = []
        tray = tray_menu.TrayMenu(fake_icon(calls), pystray.Menu.SEPARATOR)
        self.assertTrue(tray.show(200, 200))
        time.sleep(1.0)
        self.assertFalse(tray.show(1, 1))
        subprocess.run(['xdotool', 'key', '--delay', '150', 'Down', 'Down', 'Return'], check=True)  # Open editor, Stop host
        deadline = time.time() + 5
        while 'stop' not in calls and time.time() < deadline:
            time.sleep(0.1)
        self.assertEqual(calls, ['stop'])
        time.sleep(0.5)
        self.assertTrue(tray._open.acquire(blocking=False))  # the menu closed and can open again


if __name__ == '__main__':
    unittest.main()
