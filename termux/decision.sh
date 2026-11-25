#!/data/data/com.termux/files/usr/bin/bash
set -eu
ACTION="${1:?RESTORE or ACCEPT}"
MISMATCH_ID="${2:?opaque mismatch id}"
case "$ACTION" in RESTORE|ACCEPT) ;; *) echo "invalid action" >&2; exit 2;; esac
python - "$ACTION" "$MISMATCH_ID" <<'PY'
import json,socket,sys
from pathlib import Path
sock=Path.home()/".switchsnitch"/"decision.sock"
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.connect(str(sock))
s.sendall(json.dumps({"action":sys.argv[1],"mismatch_id":sys.argv[2]},separators=(",",":")).encode())
print(s.recv(4096).decode().strip())
PY
