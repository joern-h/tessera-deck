"""Which system the host runs on: the one place that reads `sys.platform`.

Tessera supports Windows (`platform_windows`) and Linux (`platform_linux`). On any other system the import of this
module fails with `UnsupportedPlatform`, so a macOS or BSD start stops with a clear message and never falls into the
Windows code by accident. Shared modules import `IS_WINDOWS` / `IS_LINUX` from here.
"""
import sys


class UnsupportedPlatform(OSError):
    """Tessera has no support for this operating system."""


def detect(platform: str | None = None) -> str:
    """'windows' or 'linux' for a `sys.platform` value (this system's by default); anything else raises."""
    name = sys.platform if platform is None else platform
    if name == 'win32':
        return 'windows'
    if name.startswith('linux'):
        return 'linux'
    raise UnsupportedPlatform(f"Tessera runs on Windows and Linux, not on '{name}'")


NAME = detect()
IS_WINDOWS = NAME == 'windows'
IS_LINUX = NAME == 'linux'
