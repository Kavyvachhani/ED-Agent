@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM build_windows.bat — Build Single-File Windows Installer (IndustrilityAgentSetup.exe)
REM
REM Produces:
REM   dist\IndustrilityAgentSetup.exe  ← Single-file setup wizard for distribution
REM ═══════════════════════════════════════════════════════════════════════════════

setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║   Industrility — Single Executable Installer Build           ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM ── 1. Check Python ───────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  ❌  Python not found.
    echo      Download from https://python.org and check "Add Python to PATH".
    pause & exit /b 1
)
echo  ✔  Python environment verified.

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
echo  → Packaging binary with PyInstaller...
python -m PyInstaller IndustrilityAgent.spec --noconfirm

if not exist "dist\IndustrilityAgent.exe" (
    echo  ❌  PyInstaller did not produce dist\IndustrilityAgent.exe
    pause & exit /b 1
)
echo  ✔  Binary bundled successfully.

REM ── 6. Detect or Auto-Install NSIS Compiler ──────────────────────────────────
echo  → Checking for NSIS compiler (makensis.exe)...

set MAKENSIS=
where makensis >nul 2>&1
if not errorlevel 1 (
    set MAKENSIS=makensis
    goto :found_nsis
)

set NSIS_PATHS=^
    "C:\Program Files (x86)\NSIS\makensis.exe" ^
    "C:\Program Files\NSIS\makensis.exe" ^
    "%LocalAppData%\Programs\NSIS\makensis.exe"

for %%P in (%NSIS_PATHS%) do (
    if exist %%P (
        set MAKENSIS=%%P
        goto :found_nsis
    )
)

echo  → NSIS not found on PATH. Attempting automatic installation via winget...
winget install --id NSIS.NSIS -e --silent --accept-source-agreements --accept-package-agreements >nul 2>&1

for %%P in (%NSIS_PATHS%) do (
    if exist %%P (
        set MAKENSIS=%%P
        goto :found_nsis
    )
)

where makensis >nul 2>&1
if not errorlevel 1 (
    set MAKENSIS=makensis
    goto :found_nsis
)

echo.
echo  ⚠️  NSIS Compiler is required to create the single .exe setup wizard.
echo     Please install NSIS once (takes 30 seconds):
echo       1. Download from: https://nsis.sourceforge.io/Download
echo       2. Install it (accept default settings)
echo       3. Re-run this build_windows.bat script
echo.
echo  ✔  Portable executable is ready at: dist\IndustrilityAgent.exe
pause
exit /b 0

:found_nsis
echo  ✔  NSIS Compiler ready: %MAKENSIS%

REM ── 7. Compile Single .exe Setup Wizard ──────────────────────────────────────
echo  → Compiling single-file setup wizard (IndustrilityAgentSetup.exe)...
%MAKENSIS% installer_windows.nsi

if not exist "dist\IndustrilityAgentSetup.exe" (
    echo  ❌  NSIS compilation failed.
    pause & exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║  ✅  SINGLE .EXE INSTALLER CREATED SUCCESSFULLY!                      ║
echo  ╠══════════════════════════════════════════════════════════════════════╣
echo  ║  File to Distribute:                                                 ║
echo  ║    dist\IndustrilityAgentSetup.exe                                   ║
echo  ║                                                                      ║
echo  ║  What the end-user does:                                            ║
echo  ║    1. Double-click IndustrilityAgentSetup.exe                        ║
echo  ║    2. Click Next -> Install -> Finish                                ║
echo  ║    3. App installs to Program Files, Start Menu & Apps & Features   ║
echo  ║       and launches automatically! Zero manual steps.                 ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.
pause
