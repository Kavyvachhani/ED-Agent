"""
config.py — Central configuration for the Employee Device Security Agent.
"""

import os
import sys

# ─── Zoho API Configuration ───────────────────────────────────────────────────
# Self Client (created at https://api-console.zoho.com)
# Scopes used: WorkDrive.files.ALL,WorkDrive.workspace.ALL

ZOHO_CLIENT_ID     = "1000.9DT21VWZEXZKOISEJKUTWTDW8KYDFL"
ZOHO_CLIENT_SECRET = "4882c44aebeb1f9b01c071eb4d2929ead0d67f481b"
ZOHO_SCOPES        = "WorkDrive.files.ALL,WorkDrive.workspace.ALL"

ZOHO_GRANT_TOKEN   = ""
DEFAULT_REFRESH_TOKEN = "1000.488bc2a1023b471ae04a7a31047811b1.cd51cb78fd99b005810b3abf3b5807f8"

# US datacenter
ZOHO_ACCOUNTS_URL  = "https://accounts.zoho.com"
ZOHO_WORKDRIVE_API = "https://workdrive.zoho.com/api/v1"

# ─── WorkDrive Target Folder ──────────────────────────────────────────────────
# Extracted from: https://workdrive.zoho.com/folder/cc037469ff9423f25482382fd4f2e76724628
COMPANY_FOLDER_ID  = "cc037469ff9423f25482382fd4f2e76724628"

# ─── Application Metadata ─────────────────────────────────────────────────────
APP_NAME           = "IndustrilityAgent"
APP_DISPLAY_NAME   = "Industrility Agent"
APP_VERSION        = "1.0.0"
COMPANY_NAME       = "Industrility"
BUNDLE_ID          = "com.industrility.agent"

# OAuth callback port
OAUTH_PORT         = 8765

# ─── Scheduler (Monthly - Last Friday at 08:00 AM) ────────────────────────────
SCAN_SCHEDULE      = "monthly"
SCAN_DAY           = "last fri"
SCAN_HOUR          = 8
SCAN_MINUTE        = 0

# ─── Compliance Thresholds ────────────────────────────────────────────────────
MAX_SCREEN_LOCK_MINUTES = 15
MIN_PASSWORD_LENGTH     = 8
MAX_OS_PATCH_DAYS       = 30

# ─── File Paths ───────────────────────────────────────────────────────────────
def _app_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path

APP_DATA_DIR              = _app_data_dir()
PROFILE_FILE              = os.path.join(APP_DATA_DIR, "profile.json")
LAST_REPORT_FILE          = os.path.join(APP_DATA_DIR, "last_report.json")
LOG_FILE                  = os.path.join(APP_DATA_DIR, "agent.log")

# ─── Keychain Keys ────────────────────────────────────────────────────────────
KEYCHAIN_SERVICE          = "IndustrilitySecurity"
KEYCHAIN_ACCESS_TOKEN_KEY = "access_token"
KEYCHAIN_REFRESH_TOKEN_KEY= "refresh_token"
KEYCHAIN_TOKEN_EXPIRY_KEY = "token_expiry"
