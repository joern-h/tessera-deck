"""Which default profile a first run starts from: the Linux one on Linux, the Windows one everywhere else."""
from pathlib import Path
import sys


def seed_path(folder) -> Path:
    folder = Path(folder)
    linux = folder / 'profiles.default.linux.json'
    if sys.platform.startswith('linux') and linux.is_file():
        return linux
    return folder / 'profiles.default.json'
