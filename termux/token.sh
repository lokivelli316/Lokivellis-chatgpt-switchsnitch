#!/data/data/com.termux/files/usr/bin/bash
set -eu
TOKEN="$HOME/.switchsnitch/token"
[ -f "$TOKEN" ] || { echo "SwitchSnitch token not created yet; start snitch first." >&2; exit 1; }
cat "$TOKEN"; printf '\n'
