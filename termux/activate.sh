#!/data/data/com.termux/files/usr/bin/bash
# Additive activation of the existing bridge; never kill an unrelated process.
set -eu
repo="$(cd "$(dirname "$0")/.." && pwd)"
root="$HOME/.switchsnitch"
mkdir -p "$root"; chmod 700 "$root"
command -v python >/dev/null || pkg install -y python
command -v termux-notification >/dev/null || pkg install -y termux-api
health() {
 python - "$root" <<'PY'
import json,sys,urllib.request
from pathlib import Path
p=Path(sys.argv[1])
try:
 port=int((p/"port").read_text())
 if not 8765<=port<=8864: raise ValueError("invalid port")
 req=urllib.request.Request(f"http://127.0.0.1:{port}/health",headers={"X-SwitchSnitch-Token":(p/"token").read_text().strip()})
 with urllib.request.urlopen(req,timeout=2) as r: j=json.load(r)
 if j.get("service")!="Lokivelli-SwitchSnitch" or not j.get("authenticated"): raise ValueError("not authenticated")
 print(json.dumps(j,indent=2))
 sys.exit(0 if "surfaces" in j and j.get("conformance")=="CONFORMANT" else 2)
except Exception as e:
 print("Bridge health unavailable:",type(e).__name__,file=sys.stderr);sys.exit(1)
PY
}
if [ "${1:-start}" = status ]; then health; exit $?; fi
# Only restart the exact local bridge process, never a different service using the port.
if health >/dev/null 2>&1; then
 echo "Patched authenticated bridge is already active."
else
 python - "$repo" <<'PY'
import os,signal,sys,time
from pathlib import Path
repo=Path(sys.argv[1]).resolve(); target=repo/"termux/bridge.py"
for p in Path("/proc").iterdir():
 if not p.name.isdigit(): continue
 try:
  if p.stat().st_uid!=os.getuid(): continue
  args=(p/"cmdline").read_bytes().split(b"\0")
  if len(args)<2 or "python" not in Path(os.fsdecode(args[0])).name: continue
  arg=Path(os.fsdecode(args[1]))
  if not arg.is_absolute(): arg=(p/"cwd").resolve()/arg
  if arg.resolve()!=target: continue
  os.kill(int(p.name),signal.SIGTERM)
 except (OSError,ValueError): continue
time.sleep(1)
PY
 nohup python "$repo/termux/bridge.py" >> "$root/bridge.log" 2>&1 </dev/null &
 echo "$!" > "$root/bridge.pid"
 for i in 1 2 3 4 5 6 7 8 9 10; do if health >/dev/null 2>&1; then break; fi; sleep 1; done
fi
# Termux:Boot runs this only if the operator has installed and enabled that app.
mkdir -p "$HOME/.termux/boot"
boot="$HOME/.termux/boot/90-switchsnitch"
if [ ! -e "$boot" ]; then
 printf '#!/data/data/com.termux/files/usr/bin/bash\nexec bash %q start\n' "$repo/termux/activate.sh" > "$boot"
 chmod 700 "$boot"
fi
health || { echo "Activation not verified; inspect $root/bridge.log. A bridge from a different checkout may still own the saved port." >&2; exit 1; }
echo "Native observer setup: port=$(cat "$root/port"); obtain token via bash $repo/termux/token.sh."
echo "Notification delivery and Android accessibility require device verification."
