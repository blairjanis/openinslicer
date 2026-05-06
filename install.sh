#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="/Applications/PrintQueueBridge.app"
SUPPORT_DIR="$HOME/Library/Application Support/PrintQueueBridge"
BUNDLE_ID="com.blairjanis.printqueuebridge"

echo "Installing PrintQueueBridge..."

mkdir -p "$SUPPORT_DIR"
cp "$SCRIPT_DIR/handler.py" "$SUPPORT_DIR/handler.py"
chmod +x "$SUPPORT_DIR/handler.py"
echo "  Handler:   $SUPPORT_DIR/handler.py"

if [ -d "$APP_PATH" ]; then
    rm -rf "$APP_PATH"
fi
osacompile -o "$APP_PATH" "$SCRIPT_DIR/handler.applescript"
echo "  Bundle:    $APP_PATH"

INFO="$APP_PATH/Contents/Info.plist"
PB="/usr/libexec/PlistBuddy"

$PB -c "Delete :CFBundleURLTypes" "$INFO" 2>/dev/null || true
$PB -c "Add :CFBundleURLTypes array" "$INFO"
$PB -c "Add :CFBundleURLTypes:0 dict" "$INFO"
$PB -c "Add :CFBundleURLTypes:0:CFBundleURLName string $BUNDLE_ID" "$INFO"
$PB -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" "$INFO"
$PB -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string printqueue" "$INFO"
$PB -c "Set :CFBundleIdentifier $BUNDLE_ID" "$INFO"
$PB -c "Add :LSUIElement bool true" "$INFO" 2>/dev/null || \
    $PB -c "Set :LSUIElement true" "$INFO"

touch "$APP_PATH"
LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
"$LSREG" -f "$APP_PATH"

echo
echo "Done. Test with:"
echo "  open 'printqueue://open?file=YOUR_CARD_TITLE'"
echo
echo "Logs: tail -f \"$SUPPORT_DIR/handler.log\""
