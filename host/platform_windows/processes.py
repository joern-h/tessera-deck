"""Processes and files on Windows: ending a command's whole tree, opening a script in its editor."""
import os
import subprocess


def kill_tree(pid: int) -> None:
    """End a process and everything it started (taskkill /T), without a console window."""
    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def edit_script(path: str) -> None:
    """Open a script in the user's editor: the file type's edit verb, else Notepad."""
    try:
        os.startfile(path, 'edit')
    except OSError:
        subprocess.Popen(['notepad.exe', path])


def open_target(expanded: str, locate) -> None:
    """Open a file, folder, address or program the way the shell does. `locate` finds a program that moved."""
    os.startfile(expanded if os.path.exists(expanded) else locate(expanded) or expanded)


def notification_beep() -> None:
    """The system "asterisk" sound, for a timer that ran out."""
    import winsound
    winsound.MessageBeep(winsound.MB_ICONASTERISK)
