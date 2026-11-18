"""What the shared setup and tray code says about Linux: names in messages and the Python modules the host needs."""
MODULE_PROBE = 'import serial, psutil, PIL, webview, pystray, keyring, jeepney, esptool'
AUTOSTART_NAME = 'the desktop'  # "Start with the desktop"
SHORTCUT_NAME = 'application menu entry'  # it is also what a launcher bar or a search finds
LAUNCHER = 'Tessera.sh'
ASKS_ABOUT_AUTOSTART = False  # the tray menu has the entry; nothing is asked on the first connection
