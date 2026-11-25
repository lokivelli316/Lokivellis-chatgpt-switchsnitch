#!/usr/bin/env python3
import json,os,socket,struct
from pathlib import Path
root=Path.home()/".switchsnitch"
out={"schema_version":1,"device":"S24_TARGET","gates":{}}
out["gates"]["GATE-1"]={"status":"UNVERIFIED","next":"Live ChatGPT stable detection + restore + sanitized DOM fixture capture"}
out["gates"]["GATE-2"]={"status":"UNVERIFIED","bridge_port":(root/"port").read_text().strip() if (root/"port").exists() else None,"next":"notification + background/Doze actionability"}
out["gates"]["GATE-3"]={"status":"UNVERIFIED","next":"Hotkey IME/focus/cursor/selection/rotation/navigation/external-keyboard/scroll matrix"}
posture="FILESYSTEM_PERMISSIONS_ONLY_WEAKER"
sock=root/"decision.sock"
if sock.exists():
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(str(sock))
        raw=s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize("3i"))
        pid,uid,gid=struct.unpack("3i",raw)
        posture="SO_PEERCRED_AVAILABLE" if uid==os.getuid() else "SO_PEERCRED_PEER_UID_MISMATCH"
        s.close()
    except Exception as e: posture="FILESYSTEM_PERMISSIONS_ONLY_WEAKER:"+type(e).__name__
out["gates"]["GATE-4"]={"status":"EVIDENCE_REQUIRED","runtime_probe":posture}
print(json.dumps(out,indent=2))
