#!/usr/bin/env bash
# 本地构建 TokenTicker macOS release candidate。本脚本绝不推送或发布 Release。
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="$(command -v python3)"
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" -m PyInstaller --clean --onefile --windowed --name TokenTicker \
    --collect-all customtkinter --osx-bundle-identifier com.tokenticker.widget \
    ccswitch_widget.py

BINARY="dist/TokenTicker.app/Contents/MacOS/TokenTicker"
if [[ ! -x "$BINARY" ]]; then
    echo "缺少构建产物: $BINARY" >&2
    exit 1
fi
HASH="$(shasum -a 256 "$BINARY" | awk '{print $1}')"
printf '%s  TokenTicker\n' "$HASH" > "dist/TokenTicker.app.sha256"

echo "artifact = dist/TokenTicker.app"
echo "sha256   = $HASH"
echo "Release remains local until tag and GitHub Release authorization is granted."
