# Industrility Device Security Agent

![Industrility Logo](assets/logo_header_clean.png)

A cross-platform corporate desktop agent built with Python and Tkinter for continuous endpoint security monitoring, compliance posture auditing, and automated evidence submission to Zoho WorkDrive.

---

## 🌟 Key Features

- **Automated Security Compliance Checks**:
  - 🔒 **Disk Encryption**: Monitors BitLocker (Windows) and FileVault (macOS) posture.
  - 🛡️ **Firewall Status**: Audits system firewall status across domain, private, and public profiles.
  - ⏱️ **Screen Lock**: Verifies screen saver lock timeouts (threshold: <= 15 mins).
  - 🔄 **OS Patch Currency**: Checks system build numbers and update timestamps (threshold: <= 30 days).
  - 🛡️ **Antivirus & Endpoint Protection**: Detects active antivirus solutions.
  - 🔐 **Secure Boot & SIP**: Audits UEFI Secure Boot (Windows) and System Integrity Protection (macOS).
  - 🔑 **Password Policy**: Ensures minimum password length enforcement (>= 8 chars).

- **Hardware & System Inventory**:
  - Collects Processor details, RAM capacity (GB), Storage Drive space (GB total/free), Hostname, and Device Serial Number.

- **Automated Evidence Upload**:
  - Integrates with **Zoho WorkDrive API** (OAuth 2.0).
  - Automatically creates employee evidence folders (`{Employee Full Name}`) and uploads monthly compliance JSON reports.
  - Features intelligent monthly submission tracking to prevent accidental duplicate uploads.

- **Background Scheduling**:
  - Runs automated scans on a configurable schedule (default: Last Friday of each month at 08:00 AM local time).
  - Registers system background daemons (**LaunchAgent** on macOS, **Registry Startup** on Windows).

- **Modern Dark Theme UI**:
  - Dark mode interface styled with Industrility brand colors.
  - Includes password show/hide eye toggle (`👁️`/`🙈`).
  - Native timezone-aware scan timestamps for multi-region teams.
  - Integrated 1-click **Uninstall / Remove Agent** functionality.

---

## 🏗️ System Architecture

```text
Employe_Device_plugin/
├── agent/                  # Core application source code
│   ├── app_window.py       # Tkinter graphical user interface (Login & Dashboard)
│   ├── auth.py             # Zoho OAuth 2.0 authentication manager
│   ├── collector.py        # OS security checks and system hardware collector
│   ├── config.py           # Application settings and environment configuration
│   ├── main.py             # Application entry point and daemon setup
│   ├── registration.py     # Employee profile persistence layer
│   ├── scheduler.py        # Background scan scheduler (APScheduler)
│   ├── uninstaller.py      # Programmatic in-app uninstallation engine
│   └── uploader.py         # Zoho WorkDrive evidence upload engine
├── assets/                 # Brand logos, master application icons (.icns, .ico, .png)
├── build_mac.sh            # macOS build pipeline (PyInstaller + codesign + pkgbuild)
├── build_windows.bat       # Windows build pipeline (PyInstaller + NSIS Installer)
├── entitlements.plist      # macOS security entitlements
├── file_version_info.txt   # Windows executable version metadata
├── installer_windows.nsi   # Windows NSIS Installer script
├── pkg_scripts/            # macOS installer post-installation scripts
├── prepare_icons.py        # Multi-platform icon generator script
├── requirements.txt        # Python dependency manifest
├── run.py                  # CLI runner script
├── uninstall_mac.sh        # Standalone macOS uninstaller script
└── uninstall_windows.bat    # Standalone Windows uninstaller script
```

---

## 🚀 Installation & Distribution

###  macOS (`IndustrilityAgent.pkg`)
1. Download **`IndustrilityAgent.pkg`** from the latest release or `dist/` directory.
2. Double-click the installer and complete the setup wizard.
3. The app installs to `/Applications/IndustrilityAgent.app` and registers a background startup agent.

*To uninstall on macOS:*
- Click **`🗑️ Uninstall`** inside the app UI, or
- Double-click **`Uninstall Industrility Agent.command`** in `/Applications`, or
- Run `bash uninstall_mac.sh` in Terminal.

---

### 🪟 Windows (`IndustrilityAgentSetup.exe`)
1. Download **`IndustrilityAgentSetup.exe`** from the latest release or `dist/` directory.
2. Run the installer wizard (installs to `C:\Program Files\Industrility Agent`).
3. Shortcut created in Start Menu. Registered under Windows **Apps & Features**.

*To uninstall on Windows:*
- Go to **Windows Settings → Apps & Features → Uninstall**, or
- Click **`🗑️ Uninstall`** inside the app UI, or
- Run `uninstall_windows.bat`.

---

## 🛠️ Building from Source

### Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### 1. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Build macOS Package (.app & .pkg)
```bash
bash build_mac.sh
```
*Output generated in `dist/IndustrilityAgent.pkg`.*

### 3. Build Windows Package (.exe)
*(Must be executed on Windows with NSIS installed)*
```cmd
build_windows.bat
```
*Output generated in `dist\IndustrilityAgentSetup.exe`.*

---

## ⚙️ Configuration & Environment Variables

Key parameters can be overridden using environment variables:

| Environment Variable | Description | Default |
| :--- | :--- | :--- |
| `ZOHO_CLIENT_ID` | Zoho API OAuth Client ID | Built-in |
| `ZOHO_CLIENT_SECRET` | Zoho API OAuth Client Secret | Built-in |
| `ZOHO_COMPANY_FOLDER_ID` | Zoho WorkDrive Target Folder ID | Built-in |
| `ZOHO_ACCOUNTS_URL` | Zoho OAuth Datacenter Base URL | `https://accounts.zoho.com` |
| `ZOHO_WORKDRIVE_API` | Zoho WorkDrive API Endpoint | `https://workdrive.zoho.com/api/v1` |

---

## 📄 License

Distributed under the terms of the MIT License. See [LICENSE.txt](LICENSE.txt) for more details.
