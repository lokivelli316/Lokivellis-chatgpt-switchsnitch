#!/usr/bin/env python3
import json, os, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path.home()/".switchsnitch"
ROOT.mkdir(exist_ok=True)
DECISION=ROOT/"decision.json"
RECEIPTS=ROOT/"receipts.jsonl"

def read_json(handler):
    n=int(handler.headers.get("content-length","0"))
    return json.loads(handler.rfile.read(n) or b"{}")

def notify(e):
    expected=e.get("expected","UNVERIFIED"); selected=e.get("selected","UNVERIFIED")
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
        else:
            self.cors(404); self.wfile.write(b'{}'); return
        self.cors(); self.wfile.write(b'{"ok":true}')
    def log_message(self,*args): pass

if __name__=="__main__":
    ThreadingHTTPServer(("127.0.0.1",8765),H).serve_forever()
