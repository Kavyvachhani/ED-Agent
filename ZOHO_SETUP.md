# Zoho API Console Setup Guide

This guide walks you (the IT admin) through registering the Device Security Agent app in Zoho's API Console so employees can log in with their Zoho accounts.

---

## Step 1 — Create the Zoho Application

1. Go to → **https://api-console.zoho.in** (India) or **https://api-console.zoho.com** (US)
2. Sign in with your **admin** Zoho account
3. Click **"Add Client"**
4. Choose client type: **"Desktop (CLI / Native)"**
5. Fill in:
   - **Client Name**: `Device Security Agent`
   - **Homepage URL**: _(your company website)_
   - **Authorized Redirect URIs**: `http://localhost:8765/callback`
6. Click **Create**
7. Copy your **Client ID** (you do **not** need the Client Secret for a native/desktop app)

---

## Step 2 — Configure `agent/config.py`

Open `agent/config.py` and replace:

```python
ZOHO_CLIENT_ID = "YOUR_ZOHO_CLIENT_ID_HERE"
```

with your actual Client ID from Step 1.

Also confirm the data center URL matches your Zoho region:
```python
ZOHO_ACCOUNTS_URL  = "https://accounts.zoho.in"   # India
# ZOHO_ACCOUNTS_URL  = "https://accounts.zoho.com"  # US
# ZOHO_ACCOUNTS_URL  = "https://accounts.zoho.eu"   # EU
```

---

## Step 3 — Create the Company WorkDrive Folder

1. Log into **Zoho WorkDrive** as admin
2. Under **Team Folders**, create a new folder named e.g. `SOC2-Evidence`
3. Share the folder with **all employees** (View + Upload permission is enough; they don't need to Browse others' files)
4. Open the folder URL — it looks like:
   ```
   https://workdrive.zoho.in/home/teams/xxxxxx/ws/YYYYYYYYY
   ```
   The last part (`YYYYYYYYY`) is your **Folder ID**
5. Paste it into `agent/config.py`:
   ```python
   COMPANY_FOLDER_ID = "YYYYYYYYY"
   ```

> **How subfolders work**: On each employee's first scan, the agent automatically creates a subfolder `SOC2-Evidence/John Doe/` using the name from their registration form. Evidence files are uploaded as `evidence_YYYY-MM-DD.json`.

---

## Step 4 — Build & Distribute

### Windows
```bat
pip install -r requirements.txt
build_windows.bat
```
Distribute `dist/DeviceSecurityAgent.exe` to employees.

### macOS
```bash
pip install -r requirements.txt
chmod +x build_mac.sh
./build_mac.sh
```
Distribute `dist/DeviceSecurityAgent` (or the `.app` bundle).

---

## Employee First-Run Flow

1. Employee double-clicks the agent
2. A registration form appears (name, email, department, employee ID)
3. After filling, their browser opens for Zoho login
4. After granting access, the browser shows a "success" page
5. The agent silently moves to the system tray
6. The first Friday at 08:00, the device scan runs automatically
7. Evidence JSON is uploaded to `SOC2-Evidence/{Employee Name}/evidence_YYYY-MM-DD.json`

---

## Security Notes

- **No secrets are bundled in the app** — only the public Client ID
- Employee tokens are stored in the **OS keychain** (macOS Keychain / Windows Credential Manager)
- Each employee can only write to their own subfolder — they cannot access other employees' evidence
- Logs are stored at:
  - Windows: `%APPDATA%\DeviceSecurityAgent\agent.log`
  - macOS: `~/Library/Application Support/DeviceSecurityAgent/agent.log`
