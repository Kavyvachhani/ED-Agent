"""
uploader.py — Zoho WorkDrive file upload (zoho.com US datacenter).

Folder layout:
  COMPANY_FOLDER_ID (from config)
    └── {Employee Full Name}/
          └── evidence_YYYY-MM-DD.json

On each call:
  1. List subfolders of COMPANY_FOLDER_ID
  2. Find or create subfolder named after the employee
  3. Upload the evidence JSON (overwrite same-day file if it exists)
"""

import json
import logging
import re
from datetime import date

import requests

from . import auth, config

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        "Authorization": f"Zoho-oauthtoken {auth.get_valid_access_token()}",
        "Accept":        "application/vnd.api+json",
    }


def _sanitise(name: str) -> str:
    return re.sub(r"[^\w\s\-.]", "", name).strip() or "Employee"


# ─── Folder Operations ────────────────────────────────────────────────────────

def _list_children(parent_id: str) -> list[dict]:
    url  = f"{config.ZOHO_WORKDRIVE_API}/files/{parent_id}/files"
    resp = requests.get(url, headers=_headers(),
                        params={"filter[type]": "folder"}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def _create_folder(parent_id: str, name: str) -> str:
    url     = f"{config.ZOHO_WORKDRIVE_API}/files"
    payload = {
        "data": {
            "attributes": {"name": name, "parent_id": parent_id},
            "type": "files",
        }
    }
    resp = requests.post(
        url,
        headers={**_headers(), "Content-Type": "application/vnd.api+json"},
        data=json.dumps(payload),
        timeout=30,
    )
    resp.raise_for_status()
    fid = resp.json()["data"]["id"]
    logger.info(f"Created folder '{name}' (id={fid})")
    return fid


def _get_or_create_employee_folder(employee_name: str) -> str:
    folder_name = _sanitise(employee_name)
    children    = _list_children(config.COMPANY_FOLDER_ID)
    for item in children:
        if item.get("attributes", {}).get("name", "").lower() == folder_name.lower():
            fid = item["id"]
            logger.info(f"Using existing folder '{folder_name}' (id={fid})")
            return fid
    return _create_folder(config.COMPANY_FOLDER_ID, folder_name)


# ─── Upload ───────────────────────────────────────────────────────────────────

def upload_evidence(report: dict) -> str:
    """
    Upload report JSON to WorkDrive.
    Returns a human-readable URL or confirmation string.
    """
    employee_name = report.get("employee_name", "Unknown")
    filename      = f"evidence_{date.today().isoformat()}.json"
    content       = json.dumps(report, indent=2).encode("utf-8")

    logger.info(f"Uploading '{filename}' for {employee_name}...")

    folder_id = _get_or_create_employee_folder(employee_name)

    # WorkDrive multipart upload endpoint
    token = auth.get_valid_access_token()
    resp  = requests.post(
        f"{config.ZOHO_WORKDRIVE_API}/upload",
        headers={"Authorization": f"Zoho-oauthtoken {token}"},
        data={
            "parent_id":             folder_id,
            "override-name-exist":   "true",   # overwrite same-day file
        },
        files={"content": (filename, content, "application/json")},
        timeout=60,
    )
    resp.raise_for_status()

    try:
        resource_id = resp.json()["data"][0]["attributes"]["resource_id"]
        url = f"https://workdrive.zoho.com/file/{resource_id}"
    except (KeyError, IndexError, TypeError):
        url = "Uploaded successfully"

    logger.info(f"Upload complete: {url}")
    return url


def check_monthly_submission(employee_name: str) -> tuple[bool, str]:
    """
    Check if evidence for the current month (YYYY-MM) has already been uploaded.
    Returns (already_uploaded: bool, upload_date_str: str).
    """
    current_month = date.today().strftime("%Y-%m")
    current_month_prefix = f"evidence_{current_month}"

    # 1. Fast local check
    if os.path.exists(config.LAST_REPORT_FILE):
        try:
            with open(config.LAST_REPORT_FILE, encoding="utf-8") as f:
                rep = json.load(f)
                ts = rep.get("scan_timestamp", "")
                if ts and ts.startswith(current_month) and rep.get("uploaded_url"):
                    dt_str = ts[:10]
                    return True, dt_str
        except Exception:
            pass

    # 2. Remote check via Zoho API
    try:
        folder_id = _get_or_create_employee_folder(employee_name)
        url = f"{config.ZOHO_WORKDRIVE_API}/files/{folder_id}/files"
        resp = requests.get(url, headers=_headers(), timeout=15)
        if resp.status_code == 200:
            files = resp.json().get("data", [])
            for item in files:
                name = item.get("attributes", {}).get("name", "")
                if name.startswith(current_month_prefix):
                    created = item.get("attributes", {}).get("created_time", "")[:10] or date.today().strftime("%Y-%m-%d")
                    return True, created
    except Exception as e:
        logger.debug(f"Remote folder check error: {e}")

    return False, ""

