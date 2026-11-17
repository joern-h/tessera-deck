"""The sound and media functions of the system the host runs on (Windows: pc_state; Linux: platform_linux).

The mixer is read through cockpit.read_mixer, which hands over to platform_linux.audio on Linux."""
import sys

if sys.platform.startswith('linux'):
    from platform_linux.audio import control_audio, read_audio  # noqa: F401
    from platform_linux.media import MediaReader, control_media  # noqa: F401
else:
    from pc_state import MediaReader, control_audio, control_media, read_audio  # noqa: F401
