# DeviceSecurityAgent.spec
# PyInstaller spec file — produces a single-file binary for macOS and Windows.
# Usage:
#   macOS  :  pyinstaller DeviceSecurityAgent.spec
#   Windows:  pyinstaller DeviceSecurityAgent.spec

import sys
import os

block_cipher = None

# Detect platform-specific hidden imports
HIDDEN = [
    "PIL._imaging",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "PIL.ImageTk",
    "PIL.ImageFilter",
    "keyring.backends",
    "keyring.backend",
    "apscheduler",
    "apscheduler.schedulers.background",
    "apscheduler.triggers.cron",
    "tzlocal",
    "tzdata",
    "zoneinfo",
    "requests",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.scrolledtext",
]

if sys.platform == "win32":
    HIDDEN += [
        "pystray",
        "pystray._win32",
        "keyring.backends.Windows",
        "win32api",
        "win32con",
        "win32gui",
        "wmi",
        "winreg",
    ]
elif sys.platform == "darwin":
    HIDDEN += [
        "pystray",
        "pystray._darwin",
        "keyring.backends.macOS",
        "objc",
        "AppKit",
        "Foundation",
    ]

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("assets/Industirlity.png", "assets"),
        ("assets/logo_dark_theme.png", "assets"),
        ("assets/logo_production_brand.png", "assets"),
        ("assets/logo_header_clean.png", "assets"),
        ("assets/icon_master.png", "assets"),
        ("assets/icon.png", "assets"),
    ] + (
        [("assets/icon.icns", "assets")] if os.path.exists("assets/icon.icns") else []
    ) + (
        [("assets/icon.ico",  "assets")] if os.path.exists("assets/icon.ico")  else []
    ),
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ─── macOS: onedir (required for .app bundle) ────────────────────────────────
if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="IndustrilityAgent",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon="assets/icon.icns" if os.path.exists("assets/icon.icns") else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="IndustrilityAgent",
    )

# ─── Windows: onefile (single portable .exe) ──────────────────────────────────
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="IndustrilityAgent",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon="assets/icon.ico" if (sys.platform == "win32" and os.path.exists("assets/icon.ico")) else None,
    )

# macOS: wrap COLLECT output in a .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="IndustrilityAgent.app",
        icon="assets/icon.icns" if os.path.exists("assets/icon.icns") else None,
        bundle_identifier="com.industrility.agent",
        info_plist={
            # ── Required keys ─────────────────────────────────────────────
            "NSPrincipalClass":                "NSApplication",
            "NSAppleScriptEnabled":            False,
            "CFBundleDisplayName":             "Industrility Agent",
            "CFBundleVersion":                 "1.0.0",
            "CFBundleShortVersionString":      "1.0.0",
            "CFBundleName":                    "Industrility Agent",
            "CFBundleIconFile":                "icon.icns",
            "CFBundleIconName":                "icon",
            "NSHumanReadableCopyright":        "© 2026 Industrility",
            "LSMinimumSystemVersion":          "12.0",
            # ── Show in Dock + app switcher (not a background-only agent) ─
            "LSUIElement":                     False,
            "LSBackgroundOnly":                False,
            "NSRequiresAquaSystemAppearance":  False,
            "NSHighResolutionCapable":         True,
            # ── Privacy usage strings (macOS 13+ requires these) ─────────
            "NSAppleEventsUsageDescription":   "Industrility Agent uses Apple Events to collect system information for compliance reporting.",
            "NSSystemAdministrationUsageDescription": "Industrility Agent needs elevated access to read security settings.",
            # ── Notifications ─────────────────────────────────────────────
            "NSUserNotificationAlertStyle":    "alert",
        },
    )
