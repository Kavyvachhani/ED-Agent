; ═══════════════════════════════════════════════════════════════════════════════
; installer_windows.nsi — NSIS installer for Industrility Agent
;
; Produces:  dist\IndustrilityAgentSetup.exe
;
; What the installer does:
;   • Installs to  C:\Program Files\Industrility\IndustrilityAgent\
;   • Creates Start Menu folder: "Industrility Agent"
;   • Creates Desktop shortcut
;   • Writes  HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall  entry
;     → App appears in Settings → Apps & Features with logo + publisher info
;   • Writes  HKCU\...\Run  key so the agent starts at Windows login
;   • Bundles a proper uninstaller (Remove Programs entry + shortcut in Start Menu)
;
; REQUIREMENTS:
;   NSIS 3.x  https://nsis.sourceforge.io/Download
;   After installing NSIS, run:  makensis installer_windows.nsi
; ═══════════════════════════════════════════════════════════════════════════════

Unicode True

;── Metadata ────────────────────────────────────────────────────────────────────
!define APP_NAME        "Industrility Agent"
!define APP_EXE         "IndustrilityAgent.exe"
!define COMPANY         "Industrility"
!define VERSION         "1.0.0"
!define BUNDLE_ID       "com.industrility.agent"
!define INSTALL_DIR     "$PROGRAMFILES64\Industrility\IndustrilityAgent"
!define REG_UNINSTALL   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${BUNDLE_ID}"
!define REG_RUN         "Software\Microsoft\Windows\CurrentVersion\Run"
!define START_MENU      "$SMPROGRAMS\${APP_NAME}"
!define DESKTOP_LNK     "$DESKTOP\${APP_NAME}.lnk"
!define UNINST_EXE      "$INSTDIR\Uninstall.exe"

;── NSIS Includes ────────────────────────────────────────────────────────────────
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

;── General settings ─────────────────────────────────────────────────────────────
Name                    "${APP_NAME}"
OutFile                 "dist\IndustrilityAgentSetup.exe"
InstallDir              "${INSTALL_DIR}"
InstallDirRegKey        HKLM "${REG_UNINSTALL}" "InstallLocation"
RequestExecutionLevel   admin                ; UAC prompt for Program Files
BrandingText            "${COMPANY} v${VERSION}"
SetCompressor           /SOLID lzma

;── MUI2 Pages ───────────────────────────────────────────────────────────────────
; Installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch Industrility Agent now"
!define MUI_FINISHPAGE_SHOWREADME   ""
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

;── MUI Customization ────────────────────────────────────────────────────────────
!define MUI_ICON                    "assets\icon.ico"
!define MUI_UNICON                  "assets\icon.ico"
!define MUI_WELCOMEPAGE_TITLE       "Welcome to ${APP_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT        "This wizard will install ${APP_NAME} ${VERSION} on your computer.$\r$\n$\r$\nThe agent monitors your device's security compliance and reports to your organisation's Industrility dashboard.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_TITLE        "Installation Complete"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP      "assets\logo_production.png"
!define MUI_HEADERIMAGE_RIGHT

;── Version resource (shown in file Properties) ───────────────────────────────────
VIProductVersion                    "${VERSION}.0"
VIAddVersionKey "ProductName"       "${APP_NAME}"
VIAddVersionKey "CompanyName"       "${COMPANY}"
VIAddVersionKey "LegalCopyright"    "© 2026 ${COMPANY}"
VIAddVersionKey "FileDescription"   "${APP_NAME} Installer"
VIAddVersionKey "FileVersion"       "${VERSION}"
VIAddVersionKey "ProductVersion"    "${VERSION}"

;── Helper macro: write size to Uninstall key ─────────────────────────────────────
!macro WriteInstallSize
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${REG_UNINSTALL}" "EstimatedSize" "$0"
!macroend

;── INSTALL Section ───────────────────────────────────────────────────────────────
Section "Install" SEC_MAIN

    SectionIn RO   ; always install — cannot be de-selected

    ; Set output path and copy files
    SetOutPath "$INSTDIR"

    ; Main executable (built by PyInstaller)
    File "dist\${APP_EXE}"

    ; Icon for shortcuts
    File "assets\icon.ico"

    ; Write the uninstaller
    WriteUninstaller "${UNINST_EXE}"

    ; ── Start Menu shortcuts ─────────────────────────────────────────────────
    CreateDirectory "${START_MENU}"
    CreateShortcut "${START_MENU}\${APP_NAME}.lnk" \
                   "$INSTDIR\${APP_EXE}" "" \
                   "$INSTDIR\icon.ico" 0 \
                   SW_SHOWNORMAL ALT|F4 \
                   "Industrility Device Security Agent"
    CreateShortcut "${START_MENU}\Uninstall ${APP_NAME}.lnk" \
                   "${UNINST_EXE}" "" \
                   "${UNINST_EXE}" 0

    ; ── Desktop shortcut ─────────────────────────────────────────────────────
    CreateShortcut "${DESKTOP_LNK}" \
                   "$INSTDIR\${APP_EXE}" "" \
                   "$INSTDIR\icon.ico" 0 \
                   SW_SHOWNORMAL "" \
                   "Industrility Device Security Agent"

    ; ── Apps & Features (Uninstall) registry entry ───────────────────────────
    WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayName"          "${APP_NAME}"
    WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayVersion"       "${VERSION}"
    WriteRegStr   HKLM "${REG_UNINSTALL}" "Publisher"            "${COMPANY}"
    WriteRegStr   HKLM "${REG_UNINSTALL}" "InstallLocation"      "$INSTDIR"
    WriteRegStr   HKLM "${REG_UNINSTALL}" "UninstallString"      '"${UNINST_EXE}"'
    WriteRegStr   HKLM "${REG_UNINSTALL}" "QuietUninstallString" '"${UNINST_EXE}" /S'
    WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayIcon"          "$INSTDIR\icon.ico"
    WriteRegStr   HKLM "${REG_UNINSTALL}" "HelpLink"             "https://industrility.com"
    WriteRegStr   HKLM "${REG_UNINSTALL}" "URLInfoAbout"         "https://industrility.com"
    WriteRegDWORD HKLM "${REG_UNINSTALL}" "NoModify"             1
    WriteRegDWORD HKLM "${REG_UNINSTALL}" "NoRepair"             1
    !insertmacro WriteInstallSize

    ; ── Auto-start at Windows login (current user) ────────────────────────────
    WriteRegStr HKCU "${REG_RUN}" "IndustrilityAgent" '"$INSTDIR\${APP_EXE}"'

SectionEnd

;── UNINSTALL Section ─────────────────────────────────────────────────────────────
Section "Uninstall"

    ; Stop the running app gracefully (taskkill)
    ExecWait 'taskkill /F /IM "${APP_EXE}"' $0

    ; Remove files
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\icon.ico"
    Delete "${UNINST_EXE}"
    RMDir  "$INSTDIR"
    RMDir  "$PROGRAMFILES64\Industrility"   ; remove parent if now empty

    ; Remove shortcuts
    Delete "${START_MENU}\${APP_NAME}.lnk"
    Delete "${START_MENU}\Uninstall ${APP_NAME}.lnk"
    RMDir  "${START_MENU}"
    Delete "${DESKTOP_LNK}"

    ; Remove registry entries
    DeleteRegKey HKLM "${REG_UNINSTALL}"
    DeleteRegValue HKCU "${REG_RUN}" "IndustrilityAgent"

    ; Remove app data (profile, tokens, logs) — ask first
    MessageBox MB_YESNO "Remove all Industrility Agent data (saved profile, logs, tokens)?$\r$\nChoose No to keep your registration data." IDNO skip_data
        RMDir /r "$APPDATA\IndustrilityAgent"
    skip_data:

SectionEnd
