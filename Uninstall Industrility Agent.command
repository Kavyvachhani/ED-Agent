#!/bin/bash
# Double-clickable macOS Uninstaller for Industrility Agent

echo "=================================================================="
echo "   Industrility Device Security Agent — Complete Uninstaller"
echo "=================================================================="
echo ""

read -p "Are you sure you want to completely uninstall Industrility Agent? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Uninstallation cancelled."
    sleep 2
    exit 0
fi

echo "→ Stopping background processes and LaunchAgents..."
launchctl unload "$HOME/Library/LaunchAgents/com.industrility.agent.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.industrility.agent.plist" 2>/dev/null || true
rm -f "/Library/LaunchAgents/com.industrility.agent.plist" 2>/dev/null || true

echo "→ Removing application from /Applications..."
rm -rf "/Applications/IndustrilityAgent.app" 2>/dev/null || true
rm -rf "/Applications/Industrility Agent.app" 2>/dev/null || true

echo "→ Removing application data, tokens, and local reports..."
rm -rf "$HOME/Library/Application Support/IndustrilityAgent" 2>/dev/null || true
rm -rf "$HOME/.config/IndustrilityAgent" 2>/dev/null || true

echo "→ Clearing package receipts..."
pkgutil --forget com.industrility.agent 2>/dev/null || true

echo "→ Flushing LaunchServices cache..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain user 2>/dev/null || true

pkill -9 -f "IndustrilityAgent" 2>/dev/null || true

echo ""
echo "✅ Uninstallation Complete! All traces of Industrility Agent have been removed."
echo "You can close this window now."
sleep 3
