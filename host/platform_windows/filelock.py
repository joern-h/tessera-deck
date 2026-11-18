"""A one-byte exclusive lock on an open file, for the single-instance lock on Windows (the Linux side uses fcntl.flock)."""
import msvcrt


def lock(handle) -> None:
    """Lock the first byte; raises OSError when another process holds it."""
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)


def unlock(handle) -> None:
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
