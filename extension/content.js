let BRIDGE=""; let scanning=null,checking=false,polling=false; let lastDeliveredKey="",lastDeliveredAt=0,lastHeartbeat=0; let lastRaw=null,lastRawAt=0,lastStable="";let predecessorId=null;
const PORTS=Array.from({length:100},(_,i)=>8765+i), STABLE_MS=700, VERIFY_MS=5000, VERIFY_STEP=250;
const norm=s=>(s||"").replace(/\s+/g," ").trim();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const surfaceId=(()=>{let x=sessionStorage.getItem("switchsnitch_surface_id");if(!x){x=crypto.randomUUID();sessionStorage.setItem("switchsnitch_surface_id",x)}return x})();
function chatId(){const m=location.pathname.match(/^\/c\/([^/?#]+)/);return m?m[1]:"NEW:"+location.pathname;}
async function cfg(){return chrome.storage.local.get({expected:"GPT-5.6 Sol",bridgeToken:""});}
function selectedModel(){
 const candidates=[...document.querySelectorAll('button[data-testid*="model"],button[aria-haspopup="menu"]')];
 for(const el of candidates){const t=norm(el.textContent);if(/^GPT[- ]?/i.test(t)&&t.length<80)return t}
 return "UNVERIFIED";
}
async function headers(extra={}){
 const c=await cfg(); return {"content-type":"application/json","X-SwitchSnitch-Token":c.bridgeToken,
 "X-SwitchSnitch-Surface":surfaceId,"X-SwitchSnitch-Chat":chatId(),"X-SwitchSnitch-Expected":c.expected,...extra};
}
async function discover(){
 const c=await cfg(); if(!c.bridgeToken)return "";
 for(const port of PORTS){const base="http://127.0.0.1:"+port;try{const r=await transport(base,"/health",{headers:await headers()});const j=await r.json();if(r.ok&&j.service==="Lokivelli-SwitchSnitch"&&j.authenticated){BRIDGE=base;await chrome.storage.local.set({bridgeHealth:j});return base}}catch{}}
 await chrome.storage.local.set({bridgeHealth:{ok:false,degraded:"BRIDGE_UNREACHABLE"}});return "";
}
function transport(base,path,options={}) {
 return chrome.runtime.sendMessage({kind:"switchsnitch-http",base,path,options}).then(x=>{
  if(!x?.ok)throw new Error(x?.error||"BRIDGE_TRANSPORT_FAILED");
  return {ok:x.status>=200&&x.status<300,status:x.status,json:async()=>x.data};
 });
}
async function bridge(){if(!scanning)scanning=discover().finally(()=>scanning=null);return scanning}
async function post(path,obj){
 try{const base=BRIDGE||await bridge();if(!base)return null;const r=await transport(base,path,{method:"POST",headers:await headers(),body:JSON.stringify(obj)});if(!r.ok)throw new Error("HTTP_"+r.status);return await r.json()}catch{BRIDGE="";await chrome.storage.local.set({bridgeHealth:{ok:false,degraded:"EVENT_DELIVERY_FAILED"}});return null}
}
async function stableRead(){
 const raw=selectedModel(),t=Date.now();
 if(raw!==lastRaw){lastRaw=raw;lastRawAt=t;return null}
 if(t-lastRawAt<STABLE_MS)return null;
 lastStable=raw;return raw;
}
async function check(){
 if(checking)return;checking=true;
 try{
 const c=await cfg();if(c.expected==="UNLOCKED"||!c.bridgeToken)return;
 const selected=await stableRead();if(selected===null)return;
 if(Date.now()-lastHeartbeat>=10000){lastHeartbeat=Date.now();await post("/surface",{state:selected==="UNVERIFIED"?"SELECTOR_UNVERIFIED":"MONITORING"})}
 const chat=chatId(),key=JSON.stringify([chat,c.expected,selected]);
 if(selected.toLowerCase()===c.expected.toLowerCase()){lastDeliveredKey="";return}
 if(key===lastDeliveredKey&&Date.now()-lastDeliveredAt<15000)return;
 const payload={type:selected==="UNVERIFIED"?"OBSERVED_MODEL_UNVERIFIED":"MODEL_MISMATCH",surface_id:surfaceId,chat_id:chat,expected_at_event:c.expected,selected_at_event:selected,observed_at_event:"UNVERIFIED",predecessor_id:predecessorId,ts:new Date().toISOString()};
 const result=await post("/event",payload);
 if(result?.ok){lastDeliveredKey=key;lastDeliveredAt=Date.now();predecessorId=null}
 }finally{checking=false}
}
async function restore(target){
 const beforeChat=chatId();
 const buttons=[...document.querySelectorAll('button[aria-haspopup="menu"],button[data-testid*="model"],[role="button"]')];
 const picker=buttons.find(x=>/^GPT[- ]?/i.test(norm(x.textContent)));if(!picker)return {ok:false,reason:"PICKER_NOT_FOUND",value:selectedModel()};
 picker.click();await sleep(350);
 const options=[...document.querySelectorAll('[role="menuitem"],[role="option"],button')];
 const wanted=options.find(x=>norm(x.textContent).toLowerCase()===target.toLowerCase());if(!wanted)return {ok:false,reason:"TARGET_NOT_FOUND",value:selectedModel()};
 wanted.click();
 const deadline=Date.now()+VERIFY_MS;let value="UNVERIFIED";
 while(Date.now()<deadline){if(chatId()!==beforeChat)return {ok:false,reason:"CHAT_CHANGED",value:selectedModel()};await sleep(VERIFY_STEP);value=selectedModel();if(value!=="UNVERIFIED"&&value.toLowerCase()===target.toLowerCase())return {ok:true,reason:"VERIFIED",value}}
 return {ok:false,reason:"VERIFY_TIMEOUT",value};
}
async function poll(){
 if(polling)return;polling=true;
 try{
  const c=await cfg(),base=BRIDGE||await bridge();if(!base||!c.bridgeToken)return;
  const r=await transport(base,"/decision",{headers:await headers()});const d=await r.json();if(!d||!d.action||d.action==="NOOP")return;
  if(d.surface_id!==surfaceId||d.chat_id!==chatId()){await post("/receipt",{event_type:"RESTORE_FAILED",mismatch_id:d.mismatch_id,reason:"SURFACE_OR_CHAT_CHANGED"});predecessorId=d.mismatch_id;return}
  if(d.action==="RESTORE"){
   await post("/receipt",{event_type:"RESTORE_ATTEMPTED",mismatch_id:d.mismatch_id});
   const v=await restore(d.target);
   const type=v.ok?"RESTORE_VERIFIED":"RESTORE_FAILED";
   await post("/receipt",{event_type:type,mismatch_id:d.mismatch_id,verified:v.ok,reason:v.reason,selected_after:v.value});
   if(!v.ok){predecessorId=d.mismatch_id;lastDeliveredKey="";}
  }else if(d.action==="ACCEPT"){
   await post("/receipt",{event_type:"ACCEPTED",mismatch_id:d.mismatch_id,selected_after:selectedModel()});
  }
 }catch{BRIDGE="";}finally{polling=false;}
}
chrome.storage.onChanged.addListener((changes,area)=>{if(area==="local"&&(changes.bridgeToken||changes.expected)){BRIDGE="";lastDeliveredKey="";bridge()}});
new MutationObserver(()=>check()).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
setInterval(check,250);setInterval(poll,1000);setInterval(()=>{if(!BRIDGE)bridge()},5000);bridge();check();
