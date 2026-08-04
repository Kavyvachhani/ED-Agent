@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM build_windows.bat — Build IndustrilityAgent.exe + IndustrilityAgentSetup.exe
REM
REM OUTPUT:
REM   dist\IndustrilityAgent.exe        — raw portable executable (PyInstaller)
REM   dist\IndustrilityAgentSetup.exe   — proper Windows installer (NSIS)
REM   dist\install_app.bat              — fallback double-click installer (batch)
REM ═══════════════════════════════════════════════════════════════════════════════

setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Industrility — Windows Build           ║
echo  ╚══════════════════════════════════════════╝
echo.

REM ── 1. Check Python ───────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  ❌  Python not found.
    echo      Download from https://python.org and check "Add Python to PATH".
    pause & exit /b 1
)
echo  ✔  Python found.

REM ── 2. Install / update dependencies ─────────────────────────────────────────
echo  → Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo  ❌  pip install failed
    pause & exit /b 1
)
echo  ✔  Dependencies installed.

REM ── 3. Prepare icons ─────────────────────────────────────────────────────────
echo  → Preparing icons...
python prepare_icons.py
if errorlevel 1 (
    echo  ⚠️   Icon preparation warning - continuing with existing icon
)

REM ── 4. Clean previous builds ─────────────────────────────────────────────────
echo  → Cleaning previous build artefacts...
if exist build       rmdir /s /q build
if exist dist        rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM ── 5. PyInstaller build ─────────────────────────────────────────────────────
echo  → Running PyInstaller...
python -m PyInstaller IndustrilityAgent.spec --noconfirm

if not exist "dist\IndustrilityAgent.exe" (
    echo  ❌  PyInstaller did not produce dist\IndustrilityAgent.exe
    pause & exit /b 1
)
echo  ✔  PyInstaller: dist\IndustrilityAgent.exe

REM ── 6. Create Fallback One-Click Installer (install_app.bat) ─────────────────
(
echo @echo off
echo :: Industrility Agent One-Click Installer
echo net session ^>nul 2^>^&1
echo if %%errorlevel%% neq 0 ^(
echo     echo Requesting Administrator privileges...
echo     powershell -Command "Start-Process '%%~f0' -Verb RunAs"
echo     exit /b
echo ^)
echo echo Installing Industrility Agent to Program Files...
echo set "TARGET=C:\Program Files\Industrility\IndustrilityAgent"
echo if not exist "%%TARGET%%" mkdir "%%TARGET%%"
echo copy /y "%%~dp0IndustrilityAgent.exe" "%%TARGET%%\IndustrilityAgent.exe" ^>nul
echo echo Creating Start Menu ^& Desktop shortcuts...
echo set "SM=C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Industrility Agent"
echo if not exist "%%SM%%" mkdir "%%SM%%"
echo powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%%SM%%\Industrility Agent.lnk'); $s.TargetPath='%%TARGET%%\IndustrilityAgent.exe'; $s.Save()"
echo powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%%PUBLIC%%\Desktop\Industrility Agent.lnk'); $s.TargetPath='%%TARGET%%\IndustrilityAgent.exe'; $s.Save()"
echo echo Registering in Windows Apps ^& Features...
echo reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\com.industrility.agent" /v "DisplayName" /d "Industrility Agent" /f /reg:64 ^>nul
echo reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\com.industrility.agent" /v "DisplayVersion" /d "1.0.0" /f /reg:64 ^>nul
echo reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\com.industrility.agent" /v "Publisher" /d "Industrility" /f /reg:64 ^>nul
echo reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\com.industrility.agent" /v "InstallLocation" /d "%%TARGET%%" /f /reg:64 ^>nul
echo reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "IndustrilityAgent" /d "\"%%TARGET%%\IndustrilityAgent.exe\"" /f ^>nul
echo echo Launching Industrility Agent...
echo start "" "%%TARGET%%\IndustrilityAgent.exe"
echo echo.
echo ✅ Installation Complete! Installed to Program Files, Start Menu, Desktop, and Apps ^& Features.
echo pause
) > "dist\install_app.bat"

REM ── 7. NSIS Installer ────────────────────────────────────────────────────────
echo  → Looking for NSIS (makensis.exe)...

where makensis >nul 2>&1
if not errorlevel 1 (
    set MAKENSIS=makensis
    goto :found_nsis
)

set NSIS_PATHS=^
    "C:\Program Files (x86)\NSIS\makensis.exe" ^
    "C:\Program Files\NSIS\makensis.exe"

for %%P in (%NSIS_PATHS%) do (
    if exist %%P (
        set MAKENSIS=%%P
        goto :found_nsis
    )
)

echo.
echo  ⚠️  NSIS not found — created fallback installer script 'dist\install_app.bat'.
echo     You have 2 options:
echo       Option A (Quick): Double-click  dist\install_app.bat  to install the app to Program Files & Start Menu.
echo       Option B (Single EXE): Download NSIS from https://nsis.sourceforge.io/Download, install it, and re-run build_windows.bat to create dist\IndustrilityAgentSetup.exe.
echo.
echo  ✔  Executable created: dist\IndustrilityAgent.exe
echo  ✔  Installer script created: dist\install_app.bat
echo.
pause
exit /b 0

:found_nsis
echo  ✔  NSIS found: %MAKENSIS%

echo  → Building Windows installer with NSIS...
%MAKENSIS% installer_windows.nsi

if not exist "dist\IndustrilityAgentSetup.exe" (
    echo  ❌  NSIS did not produce dist\IndustrilityAgentSetup.exe
    pause & exit /b 1
)
echo  ✔  Installer: dist\IndustrilityAgentSetup.exe

echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║  ✅  BUILD COMPLETE                                                  ║
echo  ╠══════════════════════════════════════════════════════════════════════╣
echo  ║  Portable .exe   →  dist\IndustrilityAgent.exe                       ║
echo  ║  Installer       →  dist\IndustrilityAgentSetup.exe  ← share this   ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
pause
