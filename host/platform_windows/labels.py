"""What the shared setup and tray code says about Windows: names in messages and the Python modules the host needs."""
MODULE_PROBE = 'import serial, psutil, PIL, webview, win32pdh, pystray, comtypes, esptool'
AUTOSTART_NAME = 'Windows'  # "Start with Windows"
SHORTCUT_NAME = 'Desktop shortcut'
LAUNCHER = 'Tessera.cmd'
ASKS_ABOUT_AUTOSTART = True  # the tray asks once, at the first panel connection, whether to start with the system
