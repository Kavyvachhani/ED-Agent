"""
uninstaller.py — Programmatic complete uninstallation logic for macOS and Windows.
Triggered when the user clicks "Uninstall Agent" inside the application UI.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


def perform_uninstall():
    """Completely uninstall Industrility Agent from the system and exit."""
    logger.info("Performing full uninstallation...")

    # 1. Clear tokens & profile files
    try:
        if os.path.exists(config.APP_DATA_DIR):
            shutil.rmtree(config.APP_DATA_DIR, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Error removing app data dir: {e}")

    # 2. OS-specific cleanup
    if sys.platform == "darwin":
        # macOS Cleanup
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.industrility.agent.plist")
        try:
            subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        except Exception:
            pass
        try:
            if os.path.exists(plist_path):
                os.remove(plist_path)
        except Exception:
            pass

        # Package receipts
        try:
            subprocess.run(["pkgutil", "--forget", config.BUNDLE_ID], capture_output=True)
        except Exception:
            pass

        # Move app bundle to trash / delete from /Applications
        app_in_apps = "/Applications/IndustrilityAgent.app"
        cmd_in_apps = "/Applications/Uninstall Industrility Agent.command"
        try:
            if os.path.exists(app_in_apps):
                shutil.rmtree(app_in_apps, ignore_errors=True)
            if os.path.exists(cmd_in_apps):
                os.remove(cmd_in_apps)
        except Exception:
            pass

    elif sys.platform == "win32":
        # Windows Cleanup
        try:
            # Delete startup registry key
            subprocess.run([
                "reg", "delete",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
                "/v", config.APP_NAME, "/f"
            ], capture_output=True)
        except Exception:
            pass

        try:
            # Delete uninstall registry keys
            subprocess.run([
                "reg", "delete",
                rf"HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\{config.BUNDLE_ID}",
                "/f", "/reg:64"
            ], capture_output=True)
        except Exception:
            pass

    logger.info("Uninstallation complete. Terminating process.")
    sys.exit(0)
