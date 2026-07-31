"""
main.py — Entry point for the Industriility Device Security Agent.

macOS:  Tkinter window (main thread). Scheduler runs in background.
        Window hides to Dock on close; scheduler keeps running.
Windows: Tkinter window + pystray system-tray icon.
         pystray runs detached (background thread).
         Minimize button hides to tray; tray icon shows the window.
"""

import json
import logging
import os
import sys
import threading

from . import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── Startup registration ───────────────────────────────────────────────────────

def _register_startup_windows(exe_path: str):
    """Add to Windows startup via HKCU Run registry key."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, config.APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        logger.info("Registered in Windows startup.")
    except Exception as e:
        logger.warning(f"Could not register Windows startup: {e}")


def _register_startup_mac(exe_path: str):
    """Install macOS LaunchAgent plist."""
    try:
        from pathlib import Path
        plist_dir  = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path = plist_dir / f"{config.BUNDLE_ID}.plist"
        plist_path.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{config.BUNDLE_ID}</string>
  <key>ProgramArguments</key>
  <array><string>{exe_path}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict></plist>
""")
        logger.info(f"LaunchAgent installed: {plist_path}")
    except Exception as e:
        logger.warning(f"Could not install LaunchAgent: {e}")


# ── Windows tray icon ──────────────────────────────────────────────────────────

def _setup_windows_tray(root):
    """
    Create a pystray system-tray icon for Windows.
    Uses icon.run_detached() so it runs in its own thread.
    The tray's Show/Quit commands post back to tkinter via root.after().
    """
    try:
        import pystray
        from PIL import Image, ImageDraw

        # Build tray icon image (gold shield on dark background)
        size = 64
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([0, 0, size, size], fill=(26, 26, 26))
        cx, cy = size // 2, size // 2
        pts = [
            (cx, 6), (cx+18, 14), (cx+18, 34),
            (cx, 52), (cx-18, 34), (cx-18, 14),
        ]
        draw.polygon(pts, fill=(245, 197, 24))   # Industriility gold

        def _show(icon=None, item=None):
            root.after(0, root.deiconify)
            root.after(0, root.lift)

        def _quit(icon=None, item=None):
            icon.stop()
            root.after(0, root.destroy)

        icon = pystray.Icon(
            name=config.APP_NAME,
            icon=img,
            title=f"{config.COMPANY_NAME} — Device Security Agent",
            menu=pystray.Menu(
                pystray.MenuItem("Show",  _show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit",  _quit),
            ),
        )

        # Minimize to tray instead of taskbar
        def _on_minimize(event=None):
            if root.state() == "iconic":
                root.withdraw()

        root.bind("<Unmap>", _on_minimize)

        # Override close button: hide to tray
        def _on_close():
            root.withdraw()

        root.protocol("WM_DELETE_WINDOW", _on_close)

        icon.run_detached()
        logger.info("Windows tray icon active.")
        return icon

    except Exception as e:
        logger.warning(f"Could not create tray icon: {e}")
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    logger.info(f"=== {config.APP_NAME} v{config.APP_VERSION} starting ===")

    # Register OS startup
    exe = sys.executable if not getattr(sys, "frozen", False) else sys.argv[0]
    if sys.platform == "win32":
        _register_startup_windows(exe)
    elif sys.platform == "darwin":
        _register_startup_mac(exe)

    # Launch main UI (blocks until window closed)
    from .app_window import launch

    if sys.platform == "win32":
        # We need access to root before mainloop starts.
        # Patch: launch_with_tray sets up tray after root is created.
        _launch_windows_with_tray()
    else:
        launch()


def _launch_windows_with_tray():
    """Windows-specific launch: create root, attach tray, start mainloop."""
    import tkinter as tk
    from . import auth, registration
    from .app_window import DeviceSecurityApp

    app = DeviceSecurityApp()
    _setup_windows_tray(app.root)
    app.start()


if __name__ == "__main__":
    main()
