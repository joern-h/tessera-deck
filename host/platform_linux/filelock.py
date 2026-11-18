"""An exclusive lock on an open file, for the single-instance lock on Linux (flock; the Windows counterpart is
platform_windows/filelock.py). The kernel drops the lock when the process dies."""
import fcntl


def lock(handle) -> None:
    """Raises OSError when another process holds the lock."""
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)


def unlock(handle) -> None:
    fcntl.flock(handle, fcntl.LOCK_UN)
