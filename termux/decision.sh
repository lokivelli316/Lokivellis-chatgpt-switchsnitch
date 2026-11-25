#!/data/data/com.termux/files/usr/bin/bash
set -eu
ACTION="${1:?RESTORE or ACCEPT}"
TARGET="${2:?target model}"
mkdir -p "$HOME/.switchsnitch"
python - "$ACTION" "$TARGET" > "$HOME/.switchsnitch/decision.json" <<'PY'
import json,sys,time
print(json.dumps({"action":sys.argv[1],"target":sys.argv[2],"operator_ts":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}))
PY
