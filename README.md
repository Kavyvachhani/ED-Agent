# Employee Device Security Agent

A cross-platform desktop agent that collects SOC2 audit evidence from employee devices and uploads structured JSON reports to Zoho WorkDrive.

## Features

- 🛡️ **System tray icon** — always visible, shows compliance status (green/yellow/red)
- 📋 **In-app registration** — employee fills their profile on first launch
- 🔐 **Zoho OAuth 2.0** — employees log in with their own Zoho account (tokens stored in OS keychain)
- 📊 **7 security checks** — disk encryption, firewall, screen lock, OS patches, antivirus, secure boot, password policy
- ☁️ **Auto-upload** — evidence JSON uploaded to `SOC2-Evidence/{Employee Name}/` in WorkDrive
- ⏰ **Friday auto-scan** — runs every Friday at 08:00 local time
- 🖥️ **Windows + macOS** — native checks for BitLocker/FileVault, Windows Firewall/macOS Firewall, etc.

## Quick Start (Development)

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Configure (see ZOHO_SETUP.md)
# Edit agent/config.py with your Zoho Client ID and WorkDrive Folder ID

# 3. Run
python run.py
```

## Building

See [ZOHO_SETUP.md](ZOHO_SETUP.md) for full admin + build instructions.

| Platform | Command          | Output                           |
|----------|------------------|----------------------------------|
| Windows  | `build_windows.bat` | `dist/DeviceSecurityAgent.exe` |
| macOS    | `./build_mac.sh` | `dist/DeviceSecurityAgent.app`   |

## Evidence JSON Format

```json
{
  "employee_email": "john@company.com",
  "employee_name": "John Doe",
  "employee_id": "EMP-001",
  "department": "Engineering",
  "hostname": "LAPTOP-XYZ",
  "serial_number": "C02...",
  "platform": "Windows 11 22H2",
  "scan_timestamp": "2025-07-25T08:00:00+00:00",
  "scan_id": "uuid4",
  "agent_version": "1.0.0",
  "checks": {
    "disk_encryption": { "status": "compliant",     "detail": "BitLocker enabled on C:" },
    "firewall":        { "status": "compliant",     "detail": "Firewall ON (Domain, Private, Public)" },
    "screen_lock":     { "status": "compliant",     "detail": "Screen locks after 5 min with password" },
    "os_patch":        { "status": "compliant",     "detail": "Windows 11 22H2, last updated 2025-07-20" },
    "antivirus":       { "status": "compliant",     "detail": "Windows Defender (ON)" },
    "secure_boot":     { "status": "compliant",     "detail": "Secure Boot enabled" },
    "password_policy": { "status": "non_compliant", "detail": "Minimum password length: 6" }
  },
  "compliance_score": 86,
  "overall_status": "PASS"
}
```

## File Locations

| File | Path |
|------|------|
| Profile | `%APPDATA%\DeviceSecurityAgent\profile.json` (Win) / `~/Library/Application Support/DeviceSecurityAgent/profile.json` (Mac) |
| Last Report | Same dir, `last_report.json` |
| Logs | Same dir, `agent.log` |

## Project Structure

```
Employe_Device_plugin/
├── agent/
│   ├── __init__.py
│   ├── main.py          # Entry point + tray icon
│   ├── auth.py          # Zoho OAuth PKCE
│   ├── registration.py  # Employee registration form (tkinter)
│   ├── collector.py     # Device security checks
│   ├── uploader.py      # Zoho WorkDrive upload
│   ├── scheduler.py     # Friday auto-scan
│   └── config.py        # Configuration (edit before distributing)
├── assets/
│   └── icon.png
├── run.py
├── requirements.txt
├── build_windows.bat
├── build_mac.sh
├── ZOHO_SETUP.md        # ← Admin setup guide
└── README.md
```
