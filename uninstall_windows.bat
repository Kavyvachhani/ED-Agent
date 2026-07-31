@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM uninstall_windows.bat — Completely uninstall Industrility Device Security Agent
REM ═══════════════════════════════════════════════════════════════════════════

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║   Industrility Device Security Agent — Complete Uninstaller  ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

echo  → Stopping background processes...
taskkill /F /IM IndustrilityAgent.exe 2>nul
taskkill /F /IM DeviceSecurityAgent.exe 2>nul

echo  → Removing Windows Startup registry keys...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "IndustrilityAgent" /f 2>nul
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "IndustrilityAgent" /f 2>nul

echo  → Removing Add/Remove Programs registry entries...
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\IndustrilityAgent" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\IndustrilityAgent" /f 2>nul

echo  → Removing application binaries and program files...
if exist "C:\Program Files\Industrility Agent" (
    rmdir /S /Q "C:\Program Files\Industrility Agent" 2>nul
)
if exist "%LOCALAPPDATA%\IndustrilityAgent" (
    rmdir /S /Q "%LOCALAPPDATA%\IndustrilityAgent" 2>nul
)

echo  → Removing local application data, tokens, and logs...
if exist "%APPDATA%\IndustrilityAgent" (
    rmdir /S /Q "%APPDATA%\IndustrilityAgent" 2>nul
)
if exist "%USERPROFILE%\.industrility_agent_tokens.json" (
    del /F /Q "%USERPROFILE%\.industrility_agent_tokens.json" 2>nul
)

echo.
echo  ✅ Uninstallation Complete! All traces of IndustrilityAgent have been removed from Windows.
echo.
pause
