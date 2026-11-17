"""Where the project's own Python lives: Windows keeps it in .venv/Scripts, Linux in .venv/bin."""
from pathlib import Path
import os

SCRIPTS = 'Scripts' if os.name == 'nt' else 'bin'


def venv_python(root: Path, windowless: bool = False) -> Path:
    """The venv's python; on Windows `windowless` picks pythonw.exe (no console window)."""
    if os.name == 'nt':
        return Path(root) / 'host/.venv/Scripts' / ('pythonw.exe' if windowless else 'python.exe')
    return Path(root) / 'host/.venv/bin/python'
