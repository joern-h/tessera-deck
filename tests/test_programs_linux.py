"""Linux program list: .desktop parsing, process names from Exec lines, icon lookup and launching."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
from platform_linux import desktop_entries, programs


def write(folder, name, **fields):
    lines = ['[Desktop Entry]'] + [f'{key}={value}' for key, value in dict({'Type': 'Application'}, **fields).items()]
    path = Path(folder, 'applications', name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


class ScanTests(unittest.TestCase):
    def test_the_menu_is_scanned_with_the_users_entries_first_and_hidden_ones_left_out(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as system:
            write(home, 'mine.desktop', Name='Editor', Exec='myeditor %F')
            write(system, 'editor.desktop', Name='Editor', Exec='othereditor')
            write(system, 'hidden.desktop', Name='Helper', Exec='helper', NoDisplay='true')
            write(system, 'doc.desktop', Name='Editor Documentation', Exec='docs')
            write(system, 'link.desktop', Name='Site', Type='Link', URL='https://x')
            write(system, 'zeta.desktop', Name='Zeta', Exec='zeta')
            found = programs.scan({'XDG_DATA_HOME': home, 'XDG_DATA_DIRS': system})
        self.assertEqual([item['name'] for item in found], ['Editor', 'Zeta'])
        self.assertTrue(found[0]['target'].startswith(home))

    def test_a_broken_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as home:
            path = write(home, 'bad.desktop', Name='Bad', Exec='bad')
            path.write_bytes(b'\xff\xfe not a desktop file')
            self.assertEqual(programs.scan({'XDG_DATA_HOME': home, 'XDG_DATA_DIRS': '/nonexistent'}), [])

    def test_the_name_in_the_users_language_is_used(self):
        with tempfile.TemporaryDirectory() as home, patch.dict('os.environ', {'LANG': 'de_DE.UTF-8'}):
            write(home, 'a.desktop', Name='Files', **{'Name[de]': 'Dateien'}, Exec='nemo')
            self.assertEqual(programs.scan({'XDG_DATA_HOME': home, 'XDG_DATA_DIRS': '/nonexistent'})[0]['name'], 'Dateien')


class ProcessNameTests(unittest.TestCase):
    def test_the_program_behind_an_exec_line(self):
        for line, expected in (('firefox %u', 'firefox'), ('/usr/bin/nemo %U', 'nemo'), ('env GDK_BACKEND=x11 /opt/App/app --flag', 'app'),
                               ('sh -c "exec spotify"', 'spotify'),
                               ('flatpak run --branch=stable org.mozilla.firefox @@u %u @@', 'firefox'),
                               ('"/opt/My App/start" --x', 'start'), ('', ''), ('unterminated "quote', '')):
            self.assertEqual(programs.process_name(line), expected, line)


class IconTests(unittest.TestCase):
    def test_an_absolute_icon_path_is_used_as_it_is(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as icon:
            self.assertEqual(programs.icon_file(icon.name), Path(icon.name))
        self.assertIsNone(programs.icon_file('/no/such/icon.png'))
        self.assertIsNone(programs.icon_file(''))

    def test_a_theme_icon_prefers_the_largest_png(self):
        with tempfile.TemporaryDirectory() as home:
            for size in ('48x48', '256x256'):
                folder = Path(home, 'icons', 'hicolor', size, 'apps')
                folder.mkdir(parents=True)
                (folder / 'demo.png').write_bytes(b'png')
            scalable = Path(home, 'icons', 'hicolor', 'scalable', 'apps')
            scalable.mkdir(parents=True)
            (scalable / 'demo.svg').write_bytes(b'<svg/>')
            found = programs.icon_file('demo', {'XDG_DATA_HOME': home, 'XDG_DATA_DIRS': '/nonexistent'})
        self.assertEqual(found.parts[-3], '256x256')


class LaunchTests(unittest.TestCase):
    def test_a_menu_entry_is_started_with_gio_and_an_address_with_xdg_open(self):
        with tempfile.TemporaryDirectory() as home, patch('shutil.which', side_effect=lambda name: '/usr/bin/' + name), \
                patch('subprocess.Popen') as popen:
            entry = write(home, 'x.desktop', Name='X', Exec='x')
            programs.launch(str(entry))
            programs.launch('https://example.com/a b')
            programs.launch('~/notes.txt')
        commands = [call.args[0] for call in popen.call_args_list]
        self.assertEqual(commands[0], ['gio', 'launch', str(entry)])
        self.assertEqual(commands[1], ['xdg-open', 'https://example.com/a b'])
        self.assertEqual(commands[2][0], 'xdg-open')
        self.assertTrue(commands[2][1].endswith('/notes.txt') and not commands[2][1].startswith('~'))
        self.assertTrue(all(call.kwargs['start_new_session'] for call in popen.call_args_list))


class EntryTests(unittest.TestCase):
    def test_a_desktop_entry_quotes_its_command(self):
        text = desktop_entries.entry(['/home/a b/python', 'x"y.py'], Path('/work dir'))
        self.assertIn('Exec="/home/a b/python" "x\\"y.py"', text)
        self.assertIn('Path=/work dir', text)

    def test_the_paths_follow_the_xdg_directories(self):
        self.assertEqual(desktop_entries.autostart_path('/cfg'), Path('/cfg/autostart/tessera.desktop'))
        self.assertEqual(desktop_entries.launcher_path('/data'), Path('/data/applications/tessera.desktop'))
        self.assertEqual(desktop_entries.config_home({'XDG_CONFIG_HOME': '/c'}), Path('/c'))


if __name__ == '__main__':
    unittest.main()
