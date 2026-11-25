#!/usr/bin/env python3
import json, os, socket, subprocess, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path.home()/".switchsnitch"
ROOT.mkdir(exist_ok=True)
DECISION=ROOT/"decision.json"
RECEIPTS=ROOT/"receipts.jsonl"
PORT_FILE=ROOT/"port"

def read_json(handler):
    n=int(handler.headers.get("content-length","0"))
    return json.loads(handler.rfile.read(n) or b"{}")

def hotkey_signal(action, expected="UNVERIFIED", selected="UNVERIFIED"):
    cmd=["am","broadcast","-a",f"com.lokivelli.hotkeyprompter.{action}",
         "-p","com.lokivelli.hotkeyprompter",
         "--es","expected",str(expected),"--es","selected",str(selected)]
    try: subprocess.run(cmd,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except FileNotFoundError: pass

def notify(e):
    expected=e.get("expected","UNVERIFIED"); selected=e.get("selected","UNVERIFIED")
    hotkey_signal("SWITCHSNITCH_ALERT", expected, selected)
    cmd=["termux-notification","--id","switchsnitch","--priority","max",
         "--title","⚠ CHATGPT MODEL SWITCH",
         "--content",f"Expected {expected} — detected {selected}",
         "--button1","YES — SWITCH BACK",
         "--button1-action",f"bash {Path(__file__).with_name('decision.sh')} RESTORE '{expected}'",
         "--button2","NO — ACCEPT",
         "--button2-action",f"bash {Path(__file__).with_name('decision.sh')} ACCEPT '{selected}'"]
    try: subprocess.run(cmd,check=False)
    except FileNotFoundError: pass

class H(BaseHTTPRequestHandler):
    def cors(self,code=200):
        self.send_response(code); self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","https://chatgpt.com"); self.end_headers()
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin","https://chatgpt.com")
        self.send_header("Access-Control-Allow-Headers","content-type"); self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.end_headers()
    def do_GET(self):
        if self.path=="/health":
            self.cors(); self.wfile.write(json.dumps({"ok":True,"port":self.server.server_port}).encode()); return
        if self.path!="/decision": self.cors(404); self.wfile.write(b'{}'); return
        data={}
        if DECISION.exists():
            try:data=json.loads(DECISION.read_text()); DECISION.unlink()
            except Exception:data={}
        self.cors(); self.wfile.write(json.dumps(data).encode())
    def do_POST(self):
        data=read_json(self)
        if self.path=="/event":
            threading.Thread(target=notify,args=(data,),daemon=True).start()
        elif self.path=="/receipt":
            with RECEIPTS.open("a") as f:f.write(json.dumps(data,separators=(",",":"))+"\n")
            hotkey_signal("SWITCHSNITCH_RESOLVED", data.get("target","UNVERIFIED"), data.get("selected_after","UNVERIFIED"))
        else:
            self.cors(404); self.wfile.write(b'{}'); return
        self.cors(); self.wfile.write(b'{"ok":true}')
    def log_message(self,*args): pass

def existing_bridge():
    if not PORT_FILE.exists(): return None
    try:
        port=int(PORT_FILE.read_text().strip())
        with socket.create_connection(("127.0.0.1",port),timeout=.25):
            return port
    except Exception:
        return None

def bind_auto(start=8765, attempts=100):
    for port in range(start,start+attempts):
        try:
            return ThreadingHTTPServer(("127.0.0.1",port),H)
        except OSError as e:
            if getattr(e,"errno",None)!=98: raise
    raise OSError(f"No free SwitchSnitch port in {start}-{start+attempts-1}")

if __name__=="__main__":
    live=existing_bridge()
    if live:
        print(f"SwitchSnitch already running on http://127.0.0.1:{live}",flush=True)
        raise SystemExit(0)
    server=bind_auto()
    PORT_FILE.write_text(str(server.server_port))
    print(f"SwitchSnitch listening on http://127.0.0.1:{server.server_port}",flush=True)
    try: server.serve_forever()
    finally:
        try:
            if PORT_FILE.exists() and PORT_FILE.read_text().strip()==str(server.server_port): PORT_FILE.unlink()
        except Exception: pass
