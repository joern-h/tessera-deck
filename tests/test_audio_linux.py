"""Linux sound (pactl) and media (MPRIS): parsing and the commands built, with a fake sound server."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
from platform_linux import audio, media

STREAMS = [
    {'index': 7, 'mute': False, 'corked': False, 'volume': {'front-left': {'value_percent': '40%'}, 'front-right': {'value_percent': '60%'}},
     'properties': {'application.name': 'Spotify', 'application.process.binary': 'spotify'}},
    {'index': 9, 'mute': True, 'corked': True, 'volume': {'mono': {'value_percent': '100%'}},
     'properties': {'application.name': 'Firefox', 'application.process.binary': 'firefox'}},
    {'index': 11, 'mute': False, 'corked': False, 'volume': {'mono': {'value_percent': '10%'}},
     'properties': {'application.name': 'Spotify', 'application.process.binary': 'spotify'}}]


class Server:
    """Answers like pactl does and remembers what it was told."""

    def __init__(self, mic=True):
        self.calls, self.mic = [], mic

    def __call__(self, *args):
        self.calls.append(args)
        match args:
            case ('get-sink-volume', _):
                return 'Volume: front-left: 55706 /  85% / -4.23 dB,   front-right: 55706 /  85% / -4.23 dB\n        balance 0.00\n'
            case ('get-sink-mute', _):
                return 'Mute: no\n'
            case ('get-source-volume', _) | ('get-source-mute', _) if not self.mic:
                raise OSError('no audio device: no source')
            case ('get-source-volume', _):
                return 'Volume: mono: 34952 /  53% / -16.38 dB\n'
            case ('get-source-mute', _):
                return 'Mute: yes\n'
            case ('--format=json', 'list', 'sink-inputs'):
                return json.dumps(STREAMS)
        return ''

    def commands(self):
        return [call for call in self.calls if call[0].startswith('set-')]


class SpeakerAndMicTests(unittest.TestCase):
    def test_the_speaker_and_the_microphone_are_read(self):
        self.assertEqual(audio.read_audio(Server()), {'volume': 85, 'speaker_muted': False, 'mic_muted': True})

    def test_a_missing_microphone_does_not_stop_the_speaker(self):
        self.assertEqual(audio.read_audio(Server(mic=False)), {'volume': 85, 'speaker_muted': False, 'mic_muted': False})

    def test_operations_become_the_right_pactl_commands(self):
        for target, operation, value, expected in (
                ('speaker', 'toggle', None, ('set-sink-mute', '@DEFAULT_SINK@', 'toggle')),
                ('speaker', 'mute', None, ('set-sink-mute', '@DEFAULT_SINK@', '1')),
                ('speaker', 'unmute', None, ('set-sink-mute', '@DEFAULT_SINK@', '0')),
                ('speaker', 'volume', 30, ('set-sink-volume', '@DEFAULT_SINK@', '30%')),
                ('speaker', 'up', None, ('set-sink-volume', '@DEFAULT_SINK@', '90%')),
                ('speaker', 'down', None, ('set-sink-volume', '@DEFAULT_SINK@', '80%')),
                ('mic', 'toggle', None, ('set-source-mute', '@DEFAULT_SOURCE@', 'toggle')),
                ('mic', 'down', None, ('set-source-volume', '@DEFAULT_SOURCE@', '48%'))):
            server = Server()
            audio.control_audio(target, operation, value, run=server)
            self.assertEqual(server.commands(), [expected], (target, operation))

    def test_the_volume_stays_between_0_and_100(self):
        server = Server()
        audio.control_audio('speaker', 'up', step=50, run=server)
        self.assertEqual(server.commands(), [('set-sink-volume', '@DEFAULT_SINK@', '100%')])

    def test_a_missing_microphone_is_reported(self):
        with self.assertRaisesRegex(OSError, 'no microphone'):
            audio.control_audio('mic', 'up', run=Server(mic=False))


class ProgramTests(unittest.TestCase):
    def test_every_stream_of_a_program_is_controlled_and_exe_is_ignored(self):
        for name in ('app:spotify', 'app:Spotify.exe'):
            server = Server()
            audio.control_audio(name, 'mute', run=server)
            self.assertEqual(server.commands(), [('set-sink-input-mute', '7', '1'), ('set-sink-input-mute', '11', '1')], name)

    def test_toggle_unmutes_only_when_every_stream_is_muted(self):
        server = Server()
        audio.control_audio('app:firefox', 'toggle', run=server)  # its one stream is muted
        self.assertEqual(server.commands(), [('set-sink-input-mute', '9', '0')])
        server = Server()
        audio.control_audio('app:spotify', 'toggle', run=server)  # none muted
        self.assertEqual(server.commands(), [('set-sink-input-mute', '7', '1'), ('set-sink-input-mute', '11', '1')])

    def test_a_program_volume_moves_from_its_own_level(self):
        server = Server()
        audio.control_audio('app:spotify', 'up', step=5, run=server)
        self.assertEqual(server.commands(), [('set-sink-input-volume', '7', '65%'), ('set-sink-input-volume', '11', '15%')])

    def test_a_program_that_plays_nothing_is_reported(self):
        with self.assertRaisesRegex(OSError, 'ghost is not playing sound'):
            audio.control_audio('app:ghost', 'mute', run=Server())

    def test_the_mixer_lists_master_programs_and_the_microphone(self):
        faders = audio.read_mixer(None, True, run=Server())
        self.assertEqual([f['id'] for f in faders], ['speaker', 'app:firefox', 'app:spotify', 'mic'])
        spotify = next(f for f in faders if f['id'] == 'app:spotify')
        self.assertEqual((spotify['level'], spotify['muted'], spotify['name']), (60, False, 'Spotify'))
        self.assertEqual([f['id'] for f in audio.read_mixer(['spotify.exe'], False, run=Server())], ['speaker', 'app:spotify'])
        self.assertEqual([f['id'] for f in audio.read_mixer(None, True, run=Server(mic=False))][-1], 'app:spotify')


class MediaTests(unittest.TestCase):
    PLAYING = {'PlaybackStatus': ('s', 'Playing'), 'Position': ('x', 61_500_000),
               'Metadata': ('a{sv}', {'xesam:title': ('s', 'Song'), 'xesam:artist': ('as', ['A', 'B']),
                                      'mpris:length': ('x', 200_000_000)})}

    def test_a_player_is_described(self):
        self.assertEqual(media.describe(self.PLAYING), {'title': 'Song', 'artist': 'A, B', 'status': 'PLAYING',
                                                        'position': 61.5, 'duration': 200.0})

    def test_a_player_without_metadata_gives_empty_values(self):
        self.assertEqual(media.describe({'PlaybackStatus': ('s', 'Paused')}),
                         {'title': '', 'artist': '', 'status': 'PAUSED', 'position': 0.0, 'duration': 0.0})

    def test_the_player_that_plays_wins_over_a_paused_one(self):
        paused = dict(media.describe(self.PLAYING), status='PAUSED', title='Old')
        playing = media.describe(self.PLAYING)
        self.assertEqual(media.choose([paused, playing])['title'], 'Song')
        self.assertEqual(media.choose([paused])['title'], 'Old')
        self.assertEqual(media.choose([]), media.EMPTY)


if __name__ == '__main__':
    unittest.main()
