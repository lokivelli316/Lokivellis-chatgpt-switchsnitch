#!/usr/bin/env python3
import hashlib, json, os, secrets, socket, struct, subprocess, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path.home()/".switchsnitch"; ROOT.mkdir(mode=0o700,exist_ok=True)
TOKEN=ROOT/"token"; RECEIPTS=ROOT/"receipts.jsonl"; PORT_FILE=ROOT/"port"; SOCK=ROOT/"decision.sock"
SPEC_VERSION="1.0.0"; SPEC_FILE=Path(__file__).resolve().parents[1]/"SWITCHSNITCH_SECURITY_STATE_MACHINE_SPEC_v1.0.0.md"
SCHEMA_VERSION=1; DECISION_TTL=120; SUPPRESSION_TTL=900
SERVICE="Lokivelli-SwitchSnitch"
lock=threading.RLock(); pending={}; suppressions={}; issued={}; receipt_seq=0
health={"notification":"UNKNOWN","security_posture":"SO_PEERCRED_UNVERIFIED","conformance":"UNKNOWN"}

def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
def spec_hash(): return hashlib.sha256(SPEC_FILE.read_bytes()).hexdigest() if SPEC_FILE.exists() else "MISSING"
SPEC_SHA256=spec_hash()

def token_value():
    if not TOKEN.exists():
        TOKEN.write_text(secrets.token_urlsafe(32)); os.chmod(TOKEN,0o600)
    return TOKEN.read_text().strip()
def token_fp(): return hashlib.sha256(token_value().encode()).hexdigest()[:16]

def recover_sequence():
    global receipt_seq
    if not RECEIPTS.exists(): return
    raw=RECEIPTS.read_bytes()
    lines=raw.splitlines()
    good=0; truncated=False
    for line in lines:
        try: good=max(good,int(json.loads(line).get("receipt_sequence",0)))
        except Exception: truncated=True
    receipt_seq=good
    if truncated: receipt("RECEIPT_RECOVERED",{"reason":"TRUNCATED_OR_MALFORMED_TAIL"},fsync=True)

def receipt(event_type,data=None,fsync=False):
    global receipt_seq
    with lock:
        receipt_seq+=1
        r={"schema_version":SCHEMA_VERSION,"spec_version":SPEC_VERSION,"spec_sha256":SPEC_SHA256,
           "receipt_sequence":receipt_seq,"event_type":event_type,"ts":now(),"token_fingerprint":token_fp()}
        if data:r.update(data)
        with RECEIPTS.open("a") as f:
            f.write(json.dumps(r,separators=(",",":"))+"\n"); f.flush()
            if fsync: os.fsync(f.fileno())
        return r

def auth_ok(h):
    supplied=h.headers.get("X-SwitchSnitch-Token","")
    ok=secrets.compare_digest(supplied,token_value())
    if not ok: receipt("AUTH_REJECTED",{"surface":h.headers.get("X-SwitchSnitch-Surface","UNKNOWN")})
    return ok

def hotkey_signal(action,**extras):
    cmd=["/system/bin/am","broadcast","-a",f"com.lokivelli.hotkeyprompter.{action}","-p","com.lokivelli.hotkeyprompter"]
    for k,v in extras.items(): cmd += ["--es",k,str(v)]
    try:return subprocess.run(cmd,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    except FileNotFoundError:return False

def notification_id(surface): return "switchsnitch-"+hashlib.sha256(surface.encode()).hexdigest()[:12]

def notify(e):
    mid=e["mismatch_id"]; surface=e["surface_id"]
    cmd=["termux-notification","--id",notification_id(surface),"--priority","max","--title","⚠ CHATGPT MODEL SWITCH",
         "--content",f"Expected {e['expected_at_event']} — detected {e['selected_at_event']}",
         "--button1","YES — SWITCH BACK","--button1-action",f"bash {Path(__file__).with_name('decision.sh')} RESTORE {mid}",
         "--button2","NO — ACCEPT","--button2-action",f"bash {Path(__file__).with_name('decision.sh')} ACCEPT {mid}"]
    try:
        p=subprocess.run(cmd,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        delivered=p.returncode==0
    except FileNotFoundError: delivered=False
    with lock:
        cur=pending.get(surface)
        if cur and cur["mismatch_id"]==mid:
            if delivered:
                cur["state"]="DECISION_PENDING"; cur["actionable"]=True
                health["notification"]="OK"; receipt("NOTIFICATION_DELIVERED",{"mismatch_id":mid,"surface_id":surface})
                hotkey_signal("SWITCHSNITCH_ALERT",mismatch_id=mid)
            else:
                cur["state"]="NOTIFICATION_FAILED"; cur["actionable"]=False
                health["notification"]="FAILED"; receipt("NOTIFICATION_FAILED",{"mismatch_id":mid,"surface_id":surface},fsync=True)
                hotkey_signal("SWITCHSNITCH_DEGRADED",reason="NOTIFICATION_FAILED")

def create_mismatch(d):
    surface=d["surface_id"]; chat=d["chat_id"]; selected=d["selected_at_event"]
    sk=(surface,chat,selected)
    if suppressions.get(sk,0)>time.time(): receipt("SUPPRESSED",{"surface_id":surface,"chat_id":chat}); return None
    old=pending.get(surface)
    predecessor=d.get("predecessor_id")
    if old and old["state"] not in ("RESTORE_VERIFIED","ACCEPTED","EXPIRED","SUPERSEDED","RESTORE_FAILED"):
        old["state"]="SUPERSEDED"; receipt("MISMATCH_SUPERSEDED",{"mismatch_id":old["mismatch_id"],"surface_id":surface})
    mid=str(uuid.uuid4())
    e={"mismatch_id":mid,"surface_id":surface,"chat_id":chat,"expected_at_event":d["expected_at_event"],
       "selected_at_event":selected,"observed_at_event":d.get("observed_at_event","UNVERIFIED"),
       "created_epoch":time.time(),"expires_epoch":time.time()+DECISION_TTL,"state":"DETECTED","actionable":False,
       "predecessor_id":predecessor}
    pending[surface]=e
    receipt("MISMATCH_DETECTED",{k:v for k,v in e.items() if k not in ("created_epoch","expires_epoch")})
    threading.Thread(target=notify,args=(e,),daemon=True).start()
    return e

def issue(surface,chat,current_expected):
    with lock:
        e=pending.get(surface)
        if not e:return {"action":"NOOP","reason":"NONE_PENDING"}
        if e["chat_id"]!=chat:return {"action":"NOOP","reason":"CHAT_CHANGED","mismatch_id":e["mismatch_id"]}
        if e["expected_at_event"]!=current_expected:return {"action":"NOOP","reason":"EXPECTED_CHANGED","mismatch_id":e["mismatch_id"]}
        if time.time()>e["expires_epoch"]:
            e["state"]="EXPIRED"; receipt("DECISION_EXPIRED",{"mismatch_id":e["mismatch_id"]},fsync=True); return {"action":"NOOP","reason":"EXPIRED"}
        if e["state"]=="DECISION_ISSUED":return {"action":"NOOP","reason":"ALREADY_ISSUED","mismatch_id":e["mismatch_id"]}
        if not e.get("actionable"):return {"action":"NOOP","reason":e["state"]}
        dec=issued.get(e["mismatch_id"])
        if not dec:return {"action":"NOOP","reason":"AWAITING_OPERATOR","mismatch_id":e["mismatch_id"]}
        e["state"]="DECISION_ISSUED"; receipt("DECISION_ISSUED",{"mismatch_id":e["mismatch_id"],"action":dec})
        return {"action":dec,"mismatch_id":e["mismatch_id"],"target":e["expected_at_event"],"chat_id":e["chat_id"],"surface_id":surface}

def operator_decision(action,mid):
    with lock:
        e=next((x for x in pending.values() if x["mismatch_id"]==mid),None)
        if not e:return {"ok":False,"reason":"UNKNOWN_ID"}
        if time.time()>e["expires_epoch"]:
            e["state"]="EXPIRED"; receipt("DECISION_EXPIRED",{"mismatch_id":mid},fsync=True); return {"ok":False,"reason":"EXPIRED"}
        if not e.get("actionable"):return {"ok":False,"reason":e["state"]}
        issued[mid]=action; receipt("DECISION_"+action,{"mismatch_id":mid},fsync=True); return {"ok":True}

def socket_loop():
    try: SOCK.unlink()
    except FileNotFoundError: pass
    s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.bind(str(SOCK)); os.chmod(SOCK,0o600); s.listen(4)
    while True:
        c,_=s.accept()
        with c:
            posture="FILESYSTEM_PERMISSIONS_ONLY_WEAKER"
            try:
                raw=c.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize("3i"))
                _,uid,_=struct.unpack("3i",raw)
                if uid==os.getuid(): posture="SO_PEERCRED_VERIFIED_RUNTIME"
                else: c.sendall(b'{"ok":false,"reason":"PEER_UID"}\n'); continue
            except Exception: pass
            health["security_posture"]=posture
            try:
                d=json.loads(c.recv(4096)); out=operator_decision(d["action"],d["mismatch_id"])
            except Exception: out={"ok":False,"reason":"BAD_REQUEST"}
            c.sendall((json.dumps(out)+"\n").encode())

def read_json(h):
    n=int(h.headers.get("content-length","0")); return json.loads(h.rfile.read(n) or b"{}")

class H(BaseHTTPRequestHandler):
    def headers_out(self,code=200):
        self.send_response(code); self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","https://chatgpt.com")
        self.send_header("Access-Control-Allow-Headers","content-type,x-switchsnitch-token,x-switchsnitch-surface")
        self.end_headers()
    def reply(self,obj,code=200): self.headers_out(code); self.wfile.write(json.dumps(obj).encode())
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin","https://chatgpt.com")
        self.send_header("Access-Control-Allow-Headers","content-type,x-switchsnitch-token,x-switchsnitch-surface")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.end_headers()
    def do_GET(self):
        if self.path=="/health":
            authorized=auth_ok(self)
            base={"ok":True,"service":SERVICE,"port":self.server.server_port,"authenticated":authorized,
                  "spec_version":SPEC_VERSION,"spec_sha256":SPEC_SHA256}
            if authorized: base.update(health)
            return self.reply(base,200 if authorized else 401)
        if not auth_ok(self): return self.reply({"ok":False,"reason":"AUTH_REJECTED"},401)
        if self.path=="/decision":
            q=dict(x.split("=",1) for x in self.path_query.split("&") if "=" in x) if False else {}
            surface=self.headers.get("X-SwitchSnitch-Surface","")
            chat=self.headers.get("X-SwitchSnitch-Chat","")
            expected=self.headers.get("X-SwitchSnitch-Expected","")
            return self.reply(issue(surface,chat,expected))
        return self.reply({},404)
    def do_POST(self):
        if not auth_ok(self): return self.reply({"ok":False,"reason":"AUTH_REJECTED"},401)
        d=read_json(self)
        if self.path=="/event":
            if d.get("type")=="OBSERVED_MODEL_UNVERIFIED":
                receipt("OBSERVED_MODEL_UNVERIFIED",d); return self.reply({"ok":True,"actionable":False})
            return self.reply({"ok":True,"event":create_mismatch(d)})
        if self.path=="/receipt":
            et=d.pop("event_type","EXTENSION_RECEIPT"); receipt(et,d,fsync=et in ("RESTORE_VERIFIED","RESTORE_FAILED","ACCEPTED"))
            mid=d.get("mismatch_id")
            e=next((x for x in pending.values() if x["mismatch_id"]==mid),None)
            if e and et=="ACCEPTED":
                e["state"]="ACCEPTED"; suppressions[(e["surface_id"],e["chat_id"],e["selected_at_event"])]=time.time()+SUPPRESSION_TTL
                hotkey_signal("SWITCHSNITCH_RESOLVED",mismatch_id=mid)
            elif e and et=="RESTORE_VERIFIED":
                e["state"]="RESTORE_VERIFIED"; hotkey_signal("SWITCHSNITCH_RESOLVED",mismatch_id=mid)
            elif e and et=="RESTORE_FAILED": e["state"]="RESTORE_FAILED"
            return self.reply({"ok":True})
        return self.reply({},404)
    def log_message(self,*args): pass

def existing_bridge():
    if not PORT_FILE.exists(): return None
    try:
        port=int(PORT_FILE.read_text())
        with socket.create_connection(("127.0.0.1",port),timeout=.25) as s:
            s.sendall(b"GET /health HTTP/1.0\r\n\r\n"); data=s.recv(512)
            return port if SERVICE.encode() in data else None
    except Exception:return None

def bind_auto(start=8765,attempts=100):
    for p in range(start,start+attempts):
        try:return ThreadingHTTPServer(("127.0.0.1",p),H)
        except OSError as e:
            if getattr(e,"errno",None)!=98:raise
    raise OSError("No free SwitchSnitch port")

if __name__=="__main__":
    recover_sequence(); token_value()
    health["conformance"]="BOUND_TO_RUNTIME_SPEC_HASH"
    receipt("RUNTIME_STARTED",{"security_posture":health["security_posture"]},fsync=True)
    threading.Thread(target=socket_loop,daemon=True).start()
    live=existing_bridge()
    if live: print(f"SwitchSnitch already running on http://127.0.0.1:{live}",flush=True); raise SystemExit(0)
    server=bind_auto(); PORT_FILE.write_text(str(server.server_port))
    print(f"SwitchSnitch listening on http://127.0.0.1:{server.server_port}",flush=True)
    print("Provision extension token with: snitch-token",flush=True)
    try:server.serve_forever()
    finally:
        try:
            if PORT_FILE.exists() and PORT_FILE.read_text().strip()==str(server.server_port):PORT_FILE.unlink()
            SOCK.unlink(missing_ok=True)
        except Exception:pass
