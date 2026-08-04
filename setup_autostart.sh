#!/usr/bin/env bash
# TokenTicker macOS 开机自启（LaunchAgent）。用法:
#   ./setup_autostart.sh          # 安装
#   ./setup_autostart.sh --uninstall  # 卸载
set -euo pipefail

LABEL="com.tokenticker.widget"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$LABEL.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--uninstall" ]]; then
    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
    fi
    rm -f "$PLIST_PATH"
    echo "已卸载开机自启: $PLIST_PATH"
    exit 0
fi

APP_PATH="/Applications/TokenTicker.app/Contents/MacOS/TokenTicker"
if [[ -x "$APP_PATH" ]]; then
    PROGRAM="$APP_PATH"
    PROGRAM_ARGS=()
else
    PYTHON_BIN="$(command -v python3 || true)"
    if [[ -z "$PYTHON_BIN" ]]; then
        echo "错误: 未找到 python3，且 /Applications/TokenTicker.app 不存在" >&2
        exit 1
    fi
    PROGRAM="$PYTHON_BIN"
    PROGRAM_ARGS=("$SCRIPT_DIR/ccswitch_widget.py")
fi

mkdir -p "$LAUNCH_AGENTS_DIR"
cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROGRAM</string>
PLIST

if [[ ${#PROGRAM_ARGS[@]} -gt 0 ]]; then
    for arg in "${PROGRAM_ARGS[@]}"; do
        printf '        <string>%s</string>\n' "$arg" >> "$PLIST_PATH"
    done
fi

cat >> "$PLIST_PATH" <<PLIST
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH" >/dev/null
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "已安装: $PLIST_PATH (先运行 --uninstall 再重装可刷新程序路径)"
    exit 0
fi
launchctl load "$PLIST_PATH"
echo "已安装开机自启: $PLIST_PATH"
echo "程序: $PROGRAM"
