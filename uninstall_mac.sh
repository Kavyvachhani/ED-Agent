#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# uninstall_mac.sh — Completely uninstall Industrility Device Security Agent
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   Industrility Device Security Agent — Complete Uninstaller  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Stop and unload background launch agents
echo "→ Stopping background processes and LaunchAgents..."
launchctl unload "$HOME/Library/LaunchAgents/com.industrility.agent.plist" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.industrility.devicesecurityagent.plist" 2>/dev/null || true

rm -f "$HOME/Library/LaunchAgents/com.industrility.agent.plist"
rm -f "$HOME/Library/LaunchAgents/com.industrility.devicesecurityagent.plist"
rm -f "/Library/LaunchAgents/com.industrility.agent.plist" 2>/dev/null || true

pkill -9 -f "IndustrilityAgent" 2>/dev/null || true
pkill -9 -f "Industrility Agent" 2>/dev/null || true
pkill -9 -f "DeviceSecurityAgent" 2>/dev/null || true

# 2. Remove applications from /Applications
echo "→ Removing application bundles from /Applications..."
rm -rf "/Applications/IndustrilityAgent.app"
rm -rf "/Applications/Industrility Agent.app"
rm -rf "/Applications/DeviceSecurityAgent.app"

# 3. Remove application support data, tokens, and logs
echo "→ Removing application data, tokens, and logs..."
rm -rf "$HOME/Library/Application Support/IndustrilityAgent"
rm -rf "$HOME/Library/Application Support/DeviceSecurityAgent"
rm -rf "$HOME/.industrility_agent_tokens.json"
rm -rf "$HOME/.config/IndustrilityAgent"
rm -rf "$HOME/Library/Caches/com.industrility.agent"

# 4. Clear package receipts
echo "→ Clearing macOS package receipts..."
pkgutil --forget com.industrility.agent 2>/dev/null || true
pkgutil --forget com.industrility.devicesecurityagent 2>/dev/null || true

# 5. Flush LaunchServices cache so Spotlight entries disappear immediately
echo "→ Flushing LaunchServices and Spotlight index cache..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain user 2>/dev/null || true

echo ""
echo "✅ Uninstallation Complete! All traces of Industrility Agent have been removed from your Mac."
echo ""
