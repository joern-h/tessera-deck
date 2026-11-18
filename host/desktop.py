"""The input and window functions of the system the host runs on.

Windows: platform_windows/input.py. Linux: platform_linux, which picks the backend of the desktop session (X11 today;
Wayland has a place in platform_linux/wayland.py). The rest of the host imports these names from here. The key names, the
operation lists and the rest of the shared vocabulary are in input_common.
"""
import sys

if sys.platform.startswith('linux'):
    from platform_linux.input import (bring_to_front, focus_existing_process, foreground_context,  # noqa: F401
                                      is_neutral_window, matches_foreground, process_window, send_hotkey, send_mouse,
                                      send_text, set_clipboard, window_action)
else:
    from platform_windows.input import (bring_to_front, focus_existing_process, foreground_context,  # noqa: F401
                                        is_neutral_window, matches_foreground, process_window, send_hotkey, send_mouse,
                                        send_text, set_clipboard, window_action)


def open_path(path) -> None:
    """Open a file or folder with the program the system has for it (Windows: os.startfile; Linux: xdg-open)."""
    if sys.platform.startswith('linux'):
        from platform_linux.programs import launch
        launch(str(path))
    else:
        import os
        os.startfile(path)  # noqa: S606 - the user's own file or folder


def script_command(script: str):
    """The command that runs a script file: Windows picks by extension (py launcher, cmd, AutoHotkey ...), Linux
    uses the interpreters it has (python3, bash, node, pwsh)."""
    if sys.platform.startswith('linux'):
        from platform_linux import scripts
        return scripts.command(script)
    from platform_windows.programs import script_command as windows_script_command
    return windows_script_command(script)
