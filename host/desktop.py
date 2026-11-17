"""The input and window functions of the system the host runs on.

Windows: win_input. Linux: platform_linux, which picks the backend of the desktop session (X11 today; Wayland has a
place in platform_linux/wayland.py). The rest of the host imports these names from here. The key names, the
operation lists and the rest of the shared vocabulary stay in win_input.
"""
import sys

if sys.platform.startswith('linux'):
    from platform_linux.input import (bring_to_front, focus_existing_process, foreground_context,  # noqa: F401
                                      is_neutral_window, matches_foreground, process_window, send_hotkey, send_mouse,
                                      send_text, set_clipboard, window_action)
else:
    from win_input import (bring_to_front, focus_existing_process, foreground_context,  # noqa: F401
                           is_neutral_window, matches_foreground, process_window, send_hotkey, send_mouse, send_text,
                           set_clipboard, window_action)
