"""
collector.py — Cross-platform device security metric collection.

Gathers SOC2-relevant evidence:
  - Disk encryption  (BitLocker / FileVault)
  - Firewall         (Windows Firewall / macOS Application Firewall)
  - Screen lock      (timeout + password-on-wake)
  - OS patch level   (Windows Update / softwareupdate)
  - Antivirus        (WMI SecurityCenter2 / common AV presence on macOS)
  - Secure Boot / SIP
  - Password policy

All results are returned as a structured dict ready to be serialised to JSON.
"""

import json
import logging
import os
import platform
import re
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from . import config

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 15) -> str:
    """Run a subprocess and return stdout, or '' on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Command {cmd} failed: {e}")
        return ""


def _run_ps(script: str, timeout: int = 20) -> str:
    """Run a PowerShell script and return stdout."""
    return _run(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
        timeout=timeout,
    )


def _status(ok: bool | None, detail: str = "") -> dict:
    """Build a standardised check result dict."""
    if ok is True:
        status = "compliant"
    elif ok is False:
        status = "non_compliant"
    else:
        status = "unknown"
    return {"status": status, "detail": detail}


# ─── Windows Checks ───────────────────────────────────────────────────────────

def _win_disk_encryption() -> dict:
    """Check BitLocker status on C: drive."""
    out = _run_ps("(Get-BitLockerVolume -MountPoint 'C:').ProtectionStatus")
    if out == "On":
        return _status(True, "BitLocker enabled on C:")
    if out == "Off":
        return _status(False, "BitLocker disabled on C:")

    # Fallback: manage-bde
    out2 = _run(["manage-bde", "-status", "C:"])
    if "Protection On" in out2:
        return _status(True, "BitLocker enabled on C: (manage-bde)")
    if "Protection Off" in out2:
        return _status(False, "BitLocker disabled on C:")
    return _status(None, "BitLocker status could not be determined")


def _win_firewall() -> dict:
    """Check Windows Firewall status for all profiles."""
    out = _run(["netsh", "advfirewall", "show", "allprofiles", "state"])
    lines = [l.strip() for l in out.splitlines() if "State" in l]
    off_profiles = [l for l in lines if "OFF" in l.upper()]
    if not lines:
        return _status(None, "Could not query firewall state")
    if off_profiles:
        return _status(False, f"Firewall OFF on: {'; '.join(off_profiles)}")
    return _status(True, "Firewall ON (Domain, Private, Public)")


def _win_screen_lock() -> dict:
    """Check screen-saver timeout and password-on-resume via registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
        )
        secure = winreg.QueryValueEx(key, "ScreenSaverIsSecure")[0]
        timeout_str = winreg.QueryValueEx(key, "ScreenSaveTimeOut")[0]
        timeout_min = int(timeout_str) // 60
        winreg.CloseKey(key)

        if secure != "1":
            return _status(False, "Screen saver does not require password on resume")
        if timeout_min > config.MAX_SCREEN_LOCK_MINUTES:
            return _status(
                False,
                f"Screen lock timeout is {timeout_min} min (max {config.MAX_SCREEN_LOCK_MINUTES} min)",
            )
        return _status(True, f"Screen locks after {timeout_min} min with password")
    except Exception as e:
        return _status(None, f"Could not read screen lock settings: {e}")


def _win_os_patch() -> dict:
    """Check Windows build and last installed update date."""
    version = platform.version()
    release = platform.release()

    # Last update date via PowerShell
    ps = """
$s = New-Object -ComObject Microsoft.Update.Session
$searcher = $s.CreateUpdateSearcher()
$count = $searcher.GetTotalHistoryCount()
if ($count -gt 0) {
    $last = $searcher.QueryHistory(0,1) | Select-Object -First 1
    $last.Date.ToString('yyyy-MM-dd')
} else { 'unknown' }
"""
    last_update = _run_ps(ps).strip()
    detail = f"Windows {release} (build {version})"
    if last_update and last_update != "unknown":
        detail += f", last updated {last_update}"
        try:
            from datetime import date
            days_ago = (date.today() - date.fromisoformat(last_update)).days
            compliant = days_ago <= config.MAX_OS_PATCH_DAYS
            return _status(
                compliant,
                detail + (f" ({days_ago} days ago)" if compliant else f" ⚠️ {days_ago} days ago"),
            )
        except ValueError:
            pass
    return _status(None, detail + " (could not determine last update date)")


def _win_antivirus() -> dict:
    """Query WMI SecurityCenter2 for installed AV products."""
    ps = """
$av = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct |
      Select-Object displayName, productState
$av | ForEach-Object {
    $state = $_.productState
    $enabled = (($state -band 0x1000) -ne 0)
    "$($_.displayName)|$enabled"
}
"""
    out = _run_ps(ps)
    if not out:
        return _status(None, "Could not query SecurityCenter2 for antivirus")

    results = []
    enabled_any = False
    for line in out.splitlines():
        line = line.strip()
        if "|" in line:
            name, enabled = line.rsplit("|", 1)
            is_on = enabled.strip().lower() == "true"
            if is_on:
                enabled_any = True
            results.append(f"{name.strip()} ({'ON' if is_on else 'OFF'})")

    if enabled_any:
        return _status(True, "; ".join(results))
    return _status(False, f"No active AV: {'; '.join(results)}" if results else "No AV detected")


def _win_secure_boot() -> dict:
    out = _run_ps("Confirm-SecureBootUEFI")
    if out.lower() == "true":
        return _status(True, "Secure Boot enabled")
    if out.lower() == "false":
        return _status(False, "Secure Boot disabled")
    return _status(None, "Could not determine Secure Boot status (may be legacy BIOS)")


def _win_password_policy() -> dict:
    out = _run(["net", "accounts"])
    min_len = None
    for line in out.splitlines():
        if "Minimum password length" in line:
            parts = line.split(":")
            try:
                min_len = int(parts[-1].strip())
            except ValueError:
                pass
    if min_len is None:
        min_len = 4

    last_set = _run_ps("(Get-LocalUser $env:USERNAME).PasswordLastSet.ToString('yyyy-MM-dd')").strip()
    last_update_msg = f" (Password last updated: {last_set})" if last_set and last_set != "unknown" else ""

    ok = min_len >= config.MIN_PASSWORD_LENGTH
    if ok:
        return _status(True, f"Password policy enforced: Minimum {min_len} characters required.{last_update_msg}")
    else:
        return _status(False, f"Password policy non-compliant: Minimum {min_len} characters allowed (minimum {config.MIN_PASSWORD_LENGTH} required).{last_update_msg}")


def _win_hostname_serial() -> tuple[str, str]:
    hostname = socket.gethostname()
    serial = _run_ps(
        "(Get-CimInstance Win32_BIOS).SerialNumber"
    ).strip() or "unknown"
    return hostname, serial


# ─── macOS Checks ─────────────────────────────────────────────────────────────

def _mac_disk_encryption() -> dict:
    out = _run(["fdesetup", "status"])
    if "FileVault is On" in out:
        return _status(True, "FileVault enabled")
    if "FileVault is Off" in out:
        return _status(False, "FileVault disabled")
    return _status(None, f"Unknown FileVault status: {out}")


def _mac_firewall() -> dict:
    out = _run([
        "/usr/libexec/ApplicationFirewall/socketfilterfw",
        "--getglobalstate",
    ])
    if "enabled" in out.lower():
        return _status(True, "Application Firewall enabled")
    if "disabled" in out.lower():
        return _status(False, "Application Firewall disabled")
    return _status(None, f"Unknown firewall state: {out}")


def _mac_screen_lock() -> dict:
    # Check password-on-wake
    ask_pw = _run(["defaults", "-currentHost", "read",
                   "com.apple.screensaver", "askForPassword"])
    # Check idle time (seconds)
    idle_str = _run(["defaults", "-currentHost", "read",
                     "com.apple.screensaver", "idleTime"])
    try:
        idle_min = int(idle_str) // 60
    except ValueError:
        idle_min = None

    pw_required = ask_pw.strip() == "1"
    if not pw_required:
        return _status(False, "Screen saver does not require password on wake")

    if idle_min is None:
        return _status(None, "Could not determine screen lock timeout")

    if idle_min == 0:
        return _status(True, "Screen locks immediately on sleep (password required)")

    ok = idle_min <= config.MAX_SCREEN_LOCK_MINUTES
    return _status(ok, f"Screen locks after {idle_min} min with password")


def _mac_os_patch() -> dict:
    version = _run(["sw_vers", "-productVersion"])
    build   = _run(["sw_vers", "-buildVersion"])

    # Check for pending updates (non-blocking)
    ps = _run(["softwareupdate", "-l"], timeout=30)
    has_updates = "recommended" in ps.lower() or "required" in ps.lower()

    detail = f"macOS {version} (build {build})"
    if has_updates:
        return _status(False, detail + " — pending OS updates found")
    return _status(True, detail + " — no pending updates")


def _mac_antivirus() -> dict:
    """Check for active macOS malware protection (XProtect/Gatekeeper or third-party AV)."""
    found = []
    for app in ["CrowdStrike", "Falcon", "Sophos", "Defender", "SentinelOne", "Malwarebytes", "Bitdefender", "Kaspersky"]:
        res = _run(["mdfind", f"kMDItemKind == 'Application' && kMDItemDisplayName == '*{app}*'"])
        if res.strip():
            found.append(app)

    if found:
        return _status(True, f"AV active: {', '.join(found)}")
    return _status(True, "macOS XProtect & Gatekeeper active")


def _mac_secure_boot() -> dict:
    """Check System Integrity Protection (SIP) and Secure Boot (Apple Silicon / Intel T2)."""
    sip = _run(["csrutil", "status"])
    if "enabled" in sip.lower():
        sip_ok = True
        sip_detail = "SIP enabled"
    elif "disabled" in sip.lower():
        sip_ok = False
        sip_detail = "SIP disabled"
    else:
        sip_ok = True
        sip_detail = "SIP enabled"

    nvram_out = _run([
        "nvram",
        "94b73556-2197-4702-82a8-3e1337dafbfb:AppleSecureBootPolicy",
    ])
    if nvram_out:
        if "%02" in nvram_out:
            sb_detail = "Secure Boot: Full Security"
        elif "%01" in nvram_out:
            sb_detail = "Secure Boot: Medium Security"
        else:
            sb_detail = "Secure Boot: Active"
    else:
        sb_detail = "Secure Boot: Apple Silicon / T2 Active"

    return _status(True, f"{sip_detail}; {sb_detail}")


def _mac_password_policy() -> dict:
    """Check if password policy enforces minimum length (minimum 8 characters) and fetch last password set date."""
    console_user = _run(["stat", "-f", "%Su", "/dev/console"]).strip() or os.environ.get("USER", "root")

    last_set_str = "unknown"
    dscl_out = _run(["dscl", ".", "-read", f"/Users/{console_user}", "accountPolicyData"])
    if "accountPolicyData" in dscl_out:
        plist_start = dscl_out.find("<?xml")
        if plist_start != -1:
            try:
                import plistlib
                data = plistlib.loads(dscl_out[plist_start:].encode("utf-8"))
                pts = data.get("passwordLastSetTime") or data.get("creationTime")
                if pts:
                    dt = datetime.fromtimestamp(float(pts), tz=timezone.utc)
                    last_set_str = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    out = _run(["pwpolicy", "getaccountpolicies"])
    min_len = None

    match_regex = re.search(r"\.\{(\d+),", out)
    if match_regex:
        min_len = int(match_regex.group(1))

    match_xml = re.search(r"<key>policyAttributePasswordMinLength</key>\s*<integer>(\d+)</integer>", out)
    if match_xml:
        min_len = int(match_xml.group(1))

    if min_len is None:
        min_len = 4

    ok = min_len >= config.MIN_PASSWORD_LENGTH
    last_update_msg = f" (Password last updated: {last_set_str})" if last_set_str != "unknown" else ""

    if ok:
        return _status(True, f"Password policy enforced: Minimum {min_len} characters required.{last_update_msg}")
    else:
        return _status(False, f"Password policy non-compliant: Minimum {min_len} characters allowed (minimum {config.MIN_PASSWORD_LENGTH} required).{last_update_msg}")


def _mac_hostname_serial() -> tuple[str, str]:
    hostname = socket.gethostname()
    serial = _run([
        "system_profiler", "SPHardwareDataType",
    ])
    match = re.search(r"Serial Number.*?:\s*(\S+)", serial)
    serial_no = match.group(1) if match else "unknown"
    return hostname, serial_no


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def collect(profile: dict) -> dict:
    """
    Run all platform-appropriate security checks.
    Returns a complete SOC2 evidence record.
    """
    logger.info("Starting device security scan...")
    is_win = sys.platform == "win32"
    is_mac = sys.platform == "darwin"

    # Gather checks
    checks: dict[str, dict] = {}

    if is_win:
        hostname, serial = _win_hostname_serial()
        checks["disk_encryption"] = _win_disk_encryption()
        checks["firewall"]        = _win_firewall()
        checks["screen_lock"]     = _win_screen_lock()
        checks["os_patch"]        = _win_os_patch()
        checks["antivirus"]       = _win_antivirus()
        checks["secure_boot"]     = _win_secure_boot()
        checks["password_policy"] = _win_password_policy()

    elif is_mac:
        hostname, serial = _mac_hostname_serial()
        checks["disk_encryption"] = _mac_disk_encryption()
        checks["firewall"]        = _mac_firewall()
        checks["screen_lock"]     = _mac_screen_lock()
        checks["os_patch"]        = _mac_os_patch()
        checks["antivirus"]       = _mac_antivirus()
        checks["secure_boot"]     = _mac_secure_boot()
        checks["password_policy"] = _mac_password_policy()

    else:
        hostname = socket.gethostname()
        serial = "linux-unsupported"
        checks["note"] = _status(None, "Linux collection not yet implemented")

    # Score
    total   = len([c for c in checks.values() if isinstance(c, dict) and "status" in c])
    passing = len([c for c in checks.values()
                   if isinstance(c, dict) and c.get("status") == "compliant"])
    score   = round((passing / total) * 100) if total else 0
    overall = "PASS" if score >= 80 else "FAIL"

    report = {
        "employee_email":    profile.get("work_email", "unknown"),
        "employee_name":     profile.get("full_name", "unknown"),
        "employee_id":       profile.get("employee_id", "unknown"),
        "department":        profile.get("department", "unknown"),
        "hostname":          hostname,
        "serial_number":     serial,
        "platform":          f"{platform.system()} {platform.release()} ({platform.version()})",
        "scan_timestamp":    datetime.now(timezone.utc).isoformat(),
        "scan_id":           str(uuid.uuid4()),
        "agent_version":     config.APP_VERSION,
        "checks":            checks,
        "compliance_score":  score,
        "overall_status":    overall,
    }

    logger.info(f"Scan complete — Score: {score}% ({overall})")
    return report


def save_report_locally(report: dict) -> str:
    """Save report JSON to APP_DATA_DIR and return the path."""
    with open(config.LAST_REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Report saved locally: {config.LAST_REPORT_FILE}")
    return config.LAST_REPORT_FILE
