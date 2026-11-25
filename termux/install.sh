#!/data/data/com.termux/files/usr/bin/bash
set -eu
pkg install -y python termux-api
mkdir -p "$HOME/.switchsnitch"
chmod +x termux/decision.sh termux/install.sh termux/bridge.py
echo "SwitchSnitch installed. Start: python termux/bridge.py"
