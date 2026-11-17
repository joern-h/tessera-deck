"""How the host names programs: one rule for Windows and Linux.

Windows names carry `.exe` (spotify.exe). On Linux a program is its executable name (spotify) and `.exe` is accepted
and ignored, so a profile written on Windows keeps working. `plain()` is the shared form for comparing; `SUFFIX` goes
into the patterns that check a name.
"""
import os

SUFFIX = r'\.exe' if os.name == 'nt' else r'(?:\.exe)?'


def plain(name: str) -> str:
    name = (name or '').strip().lower()
    return name[:-4] if name.endswith('.exe') else name
