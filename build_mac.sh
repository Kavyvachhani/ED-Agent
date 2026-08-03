#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# build_mac.sh — Build IndustrilityAgent.app + IndustrilityAgent.pkg
#
# OUTPUT:
#   dist/IndustrilityAgent.app    — the .app bundle (copy to /Applications manually)
#   dist/IndustrilityAgent.pkg    — double-click installer → installs to /Applications
#
# REQUIREMENTS (install once):
#   brew install python@3.12
#   pip3 install -r requirements.txt
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Industrility Agent"
APP_NAME_NOSPACE="IndustrilityAgent"
BUNDLE_ID="com.industrility.agent"
VERSION="1.0.0"
APP_PATH="dist/${APP_NAME_NOSPACE}.app"
PKG_PATH="dist/${APP_NAME_NOSPACE}.pkg"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Industrility — macOS Build         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Virtual environment ────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "→ Installing / updating dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ── 2. Prepare icons ──────────────────────────────────────────────────────────
echo "→ Preparing icons..."
python3 prepare_icons.py

# ── 3. Clean previous builds ──────────────────────────────────────────────────
echo "→ Cleaning previous builds..."
# Previous installer runs leave root-owned files inside dist/ — must sudo-rm
if [ -d "dist" ]; then
    sudo chmod -R 777 dist 2>/dev/null || true
    sudo rm -rf dist 2>/dev/null || true
fi
if [ -d "build" ]; then
    sudo chmod -R 777 build 2>/dev/null || true
    sudo rm -rf build 2>/dev/null || true
fi

# ── 4. PyInstaller .app bundle ────────────────────────────────────────────────
echo "→ Running PyInstaller..."
pyinstaller IndustrilityAgent.spec --noconfirm

if [ ! -d "$APP_PATH" ]; then
    echo "❌  PyInstaller did not produce ${APP_PATH}"
    exit 1
fi
echo "   ✅ ${APP_PATH} created"

# ── 5. Copy icon into Resources so Finder/Launchpad shows the gold icon ───────
echo "→ Copying icon into app bundle Resources..."
RESOURCES_DIR="${APP_PATH}/Contents/Resources"
mkdir -p "$RESOURCES_DIR"
if [ -f "assets/icon.icns" ]; then
    cp "assets/icon.icns" "${RESOURCES_DIR}/icon.icns"
    echo "   ✅ icon.icns → Contents/Resources/"
else
    echo "   ⚠️  assets/icon.icns not found — app will use default icon"
fi

# ── 6. Strip quarantine so macOS doesn't block the bundled dylibs ─────────────
echo "→ Stripping quarantine attributes..."
xattr -cr "$APP_PATH" 2>/dev/null || true

# ── 7. Code-sign with entitlements (ad-hoc — no paid Developer ID needed) ────
# Using --options runtime + entitlements relaxes Gatekeeper for:
#   • PyInstaller unsigned memory mapping
#   • Third-party .dylib loading (Pillow, tkinter, etc.)
#   • No sandbox → allows system info collection + keychain + network
echo "→ Code-signing with entitlements (ad-hoc)..."
codesign \
    --deep \
    --force \
    --sign - \
    --options runtime \
    --entitlements entitlements.plist \
    --timestamp=none \
    "$APP_PATH" 2>/dev/null || {
    echo "   ⚠️  codesign failed — app may show a warning on first launch"
    echo "   ℹ️  Right-click → Open to bypass Gatekeeper on first run"
}
echo "   ✅ Code-signed (ad-hoc)"

# ── 8. Build .pkg using pkgbuild + productbuild with postinstall script ────────
echo "→ Building component .pkg..."
STAGE_DIR="build/pkg_stage"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
cp -R "$APP_PATH" "$STAGE_DIR/"

pkgbuild \
    --root "$STAGE_DIR" \
    --install-location "/Applications" \
    --scripts "pkg_scripts" \
    --identifier "${BUNDLE_ID}" \
    --version "${VERSION}" \
    "dist/component.pkg"

echo "→ Synthesising distribution XML..."
productbuild \
    --synthesize \
    --package "dist/component.pkg" \
    "dist/distribution.xml"

# Inject welcome + title into distribution XML for a nicer installer wizard
python3 - <<'PYEOF'
import re, pathlib
xml = pathlib.Path("dist/distribution.xml").read_text()
# Insert title and welcome just after the opening <installer-gui-script ...> tag
# (do NOT touch the tag itself — productbuild synthesises it with minSpecVersion already)
injection = '\n    <title>Industrility Agent</title>\n    <welcome file="welcome.html" mime-type="text/html"/>\n'
xml = re.sub(r'(<installer-gui-script[^>]*>)', r'\1' + injection, xml, count=1)
pathlib.Path("dist/distribution.xml").write_text(xml)
print("   \u2705 distribution.xml patched")
PYEOF

# Create a simple welcome HTML (appears in the installer wizard)
cat > "dist/welcome.html" <<'HTML'
<!DOCTYPE html>
<html>
<body style="font-family:-apple-system,sans-serif;background:#1A1A1A;color:#F5C518;padding:20px">
<h2 style="color:#F5C518">Industrility Agent</h2>
<p style="color:#FFFFFF">This installer will place <strong>Industrility Agent</strong> in your
<code>/Applications</code> folder and register it to start automatically at login.</p>
<p style="color:#AAAAAA;font-size:13px">
⚠️ <strong>First launch:</strong> If macOS shows a security warning,<br>
right-click the app in Applications and choose <strong>Open</strong>.
</p>
</body>
</html>
HTML

echo "→ Building final .pkg installer..."
productbuild \
    --distribution "dist/distribution.xml" \
    --package-path "dist" \
    --resources "dist" \
    "$PKG_PATH"

# Clean intermediates
rm -f "dist/component.pkg" "dist/distribution.xml" "dist/welcome.html"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ✅  BUILD COMPLETE                                              ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
printf "║  .app  →  %-53s║\n" "dist/${APP_NAME_NOSPACE}.app"
printf "║  .pkg  →  %-53s║\n" "dist/${APP_NAME_NOSPACE}.pkg  ← share this"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Install on any Mac (macOS 12+):"
echo "  1. Double-click  dist/${APP_NAME_NOSPACE}.pkg"
echo "  2. Follow the wizard — app installs to /Applications"
echo "  3. On first launch: right-click → Open if you see a security warning"
echo ""
