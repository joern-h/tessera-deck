"""A right-click menu for pystray's X11 tray icon.

pystray's X11 backend (the legacy system tray, which is what a panel without a StatusNotifier watcher shows) has no
menu: it only runs the default action on a left click. `attach(icon)` keeps that and shows the icon's own pystray menu
on a right click, drawn with tkinter, so the tray app needs no other change and no GTK or AppIndicator.

The menu is read from `icon.menu` each time it opens, so it shows the current status, the ticks and the enabled items.
"""
from __future__ import annotations

import threading

POPUP_SECONDS = 30  # an unanswered menu closes by itself


def describe(menu, separator) -> list[dict]:
    """The items of a pystray Menu as plain data: text, enabled, checked, radio, submenu, action, separator."""
    rows = []
    for item in menu.items:
        if item is separator or getattr(item, '_text', None) == '- - - -':
            rows.append({'separator': True})
            continue
        sub = item.submenu
        rows.append({'text': str(item.text), 'enabled': bool(item.enabled), 'checked': item.checked, 'radio': bool(item.radio),
                     'default': bool(item.default), 'submenu': describe(sub, separator) if sub else None, 'item': item})
    return rows


def label(row: dict) -> str:
    mark = ('● ' if row['radio'] else '✓ ') if row['checked'] else ('    ' if row['checked'] is not None else '')
    return mark + row['text']


def build(tk, parent, rows, run):
    """Fill a tk.Menu from `describe` rows; `run(item)` is called when an entry is chosen."""
    for row in rows:
        if row.get('separator'):
            parent.add_separator()
        elif row['submenu'] is not None:
            child = tk.Menu(parent, tearoff=0)
            build(tk, child, row['submenu'], run)
            parent.add_cascade(label=label(row), menu=child, state='normal' if row['enabled'] else 'disabled')
        else:
            parent.add_command(label=label(row), state='normal' if row['enabled'] else 'disabled',
                               command=lambda item=row['item']: run(item))


class TrayMenu:
    def __init__(self, icon, separator):
        self.icon, self.separator = icon, separator
        self._open = threading.Lock()

    def show(self, x: int, y: int) -> bool:
        """Open the menu at the pointer from its own thread; False when one is already open."""
        if not self._open.acquire(blocking=False):
            return False
        threading.Thread(target=self._run, args=(x, y), name='tray-menu', daemon=True).start()
        return True

    def _run(self, x, y):
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            menu = tk.Menu(root, tearoff=0)
            build(tk, menu, describe(self.icon.menu, self.separator),
                  lambda item: threading.Thread(target=item, args=(self.icon,), daemon=True).start())
            closing = []

            def close(*_):
                if not closing:
                    closing.append(True)
                    root.after(60, root.destroy)  # after the chosen entry has run its command

            menu.bind('<Unmap>', close)
            root.after(POPUP_SECONDS * 1000, close)
            root.update_idletasks()
            menu.tk_popup(x, y)
            menu.focus_force()
            root.mainloop()
        except Exception:  # no Tk, no display: the left click still works
            self.icon._log.error('The tray menu could not be shown', exc_info=True)
        finally:
            self._open.release()


def attach(icon, separator) -> bool:
    """Give an icon without menu support (pystray's X11 backend) a right-click menu. False if it already has one."""
    if getattr(icon, 'HAS_MENU', True):
        return False
    try:
        import Xlib.X
    except ImportError:
        return False
    tray = TrayMenu(icon, separator)

    def on_button_press(event):
        if event.detail == 1:
            icon()  # the default action, as pystray does
        elif event.detail == 3:
            tray.show(event.root_x, event.root_y)

    icon._message_handlers[Xlib.X.ButtonPress] = on_button_press
    icon.tray_menu = tray
    return True
