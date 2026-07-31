"""
registration.py — Employee profile persistence (data layer only).

The UI is in app_window.py (LoginScreen). This module handles:
  - Saving/loading profile.json
  - is_registered() check
"""

import json
import os

from . import config


def _save_profile(profile: dict):
    with open(config.PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def load_profile() -> dict | None:
    if not os.path.exists(config.PROFILE_FILE):
        return None
    try:
        with open(config.PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def is_registered() -> bool:
    return load_profile() is not None
