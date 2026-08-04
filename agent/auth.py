"""
auth.py — Zoho Self Client authentication using secure local storage.

Flow:
  1. Admin generates a grant token once from api-console.zoho.com -> Generate Code
  2. First run: exchange grant token -> get access_token + refresh_token
     (stored securely in app data directory)
  3. Every subsequent run: use refresh_token -> get fresh access_token (1hr expiry)
"""

import json
import logging
import os
import requests
from datetime import datetime, timedelta, timezone

from . import config

logger = logging.getLogger(__name__)

TOKEN_URL = f"{config.ZOHO_ACCOUNTS_URL}/oauth/v2/token"
TOKEN_FILE = os.path.join(config._app_data_dir(), "tokens.json")


def _save_tokens(access_token: str, refresh_token: str, expires_in: int):
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)).isoformat()
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expiry": expiry,
    }
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        try:
            os.chmod(TOKEN_FILE, 0o600)
        except Exception:
            pass
        logger.info("Tokens stored securely.")
    except Exception as e:
        logger.error(f"Failed to store tokens: {e}")


def _load_tokens() -> dict:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                d = json.load(f)
                if d.get("refresh_token"):
                    return d
        except Exception as e:
            logger.warning(f"Could not read tokens file: {e}")
    if getattr(config, "DEFAULT_REFRESH_TOKEN", ""):
        return {"refresh_token": config.DEFAULT_REFRESH_TOKEN}
    return {}


def _exchange_grant_token(grant_token: str):
    """Exchange a one-time grant token for access + refresh tokens."""
    logger.info("Exchanging grant token for tokens...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "client_id":     config.ZOHO_CLIENT_ID,
        "client_secret": config.ZOHO_CLIENT_SECRET,
        "code":          grant_token.strip(),
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Zoho token exchange failed: {data['error']}")
    _save_tokens(data["access_token"], data["refresh_token"], data.get("expires_in", 3600))
    logger.info("Grant token exchanged successfully.")


def _refresh_access_token():
    """Use the stored refresh token to get a new access token."""
    tokens = _load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("No refresh token stored. Re-authenticate in API Console.")

    logger.info("Refreshing access token...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "client_id":     config.ZOHO_CLIENT_ID,
        "client_secret": config.ZOHO_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Token refresh failed: {data['error']}")

    new_access  = data["access_token"]
    new_refresh = data.get("refresh_token", refresh_token)
    _save_tokens(new_access, new_refresh, data.get("expires_in", 3600))
    return new_access


def bootstrap():
    """Call once at startup to verify tokens."""
    grant = config.ZOHO_GRANT_TOKEN.strip()
    tokens = _load_tokens()

    if grant and not tokens.get("refresh_token"):
        _exchange_grant_token(grant)
        return

def authenticate_with_grant_token(grant_token: str):
    """Manually exchange a grant token and store refresh token."""
    _exchange_grant_token(grant_token)


def is_authenticated() -> bool:
    """Returns True if a refresh token is stored."""
    tokens = _load_tokens()
    return bool(tokens.get("refresh_token"))


def get_valid_access_token() -> str:
    """Returns a valid access token, refreshing if expired."""
    tokens = _load_tokens()
    access = tokens.get("access_token")
    expiry_str = tokens.get("expiry")

    if access and expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now(timezone.utc) < expiry:
                return access  # Still valid
        except ValueError:
            pass

    return _refresh_access_token()


def clear_tokens():
    """Remove all stored tokens."""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
        except Exception:
            pass
    logger.info("Tokens cleared.")
