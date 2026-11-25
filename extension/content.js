let BRIDGE="http://127.0.0.1:8765";
let lastMismatch="", pending=false;
const PORTS=Array.from({length:100},(_,i)=>8765+i);

const norm=s=>(s||"").replace(/\s+/g," ").trim();
async function bridge(){
  for(const port of PORTS){
    const base="http://127.0.0.1:"+port;
    try{
      const r=await fetch(base+"/health");
      const j=await r.json();
      if(r.ok&&j.ok){BRIDGE=base;return base;}
    }catch{}
  }
  return BRIDGE;
}
function selectedModel(){
  const candidates=[...document.querySelectorAll('button[aria-haspopup="menu"], button[data-testid*="model"], [role="button"]')];
  for(const el of candidates){
    const t=norm(el.textContent);
    if(/GPT[- ]?(5\.6|6\.2)/i.test(t)) return t;
  }
  return "UNVERIFIED";
}
async function expectedModel(){return (await chrome.storage.local.get({expected:"GPT-5.6 Sol"})).expected;}
async function post(path,obj){
  try{const base=await bridge(); return await (await fetch(base+path,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(obj)})).json();}
  catch{return null;}
}
async function check(){
  if(pending)return;
  const expected=await expectedModel(); if(expected==="UNLOCKED")return;
  const selected=selectedModel(); if(selected==="UNVERIFIED")return;
  if(selected.toLowerCase().includes(expected.toLowerCase())){lastMismatch="";return;}
  const key=expected+"|"+selected+"|"+location.href; if(key===lastMismatch)return;
  lastMismatch=key; pending=true;
  await post("/event",{type:"MODEL_MISMATCH",expected,selected,observed:"UNVERIFIED",chat:document.title,url:location.href,ts:new Date().toISOString()});
  pending=false;
}
async function restore(target){
  const buttons=[...document.querySelectorAll('button[aria-haspopup="menu"], button[data-testid*="model"], [role="button"]')];
  const picker=buttons.find(x=>/GPT[- ]?(5\.6|6\.2)/i.test(norm(x.textContent))); if(!picker)return false;
  picker.click(); await new Promise(r=>setTimeout(r,350));
  const options=[...document.querySelectorAll('[role="menuitem"],[role="option"],button')];
  const wanted=options.find(x=>norm(x.textContent).toLowerCase().includes(target.toLowerCase())); if(!wanted)return false;
  wanted.click(); await new Promise(r=>setTimeout(r,500));
  return selectedModel().toLowerCase().includes(target.toLowerCase());
}
async function poll(){
  try{
    const base=await bridge(); const r=await fetch(base+"/decision"); const d=await r.json();
    if(!d||!d.action)return;
    if(d.action==="RESTORE"){
      const verified=await restore(d.target);
      await post("/receipt",{...d,verified,selected_after:selectedModel(),ts:new Date().toISOString()});
    }else if(d.action==="ACCEPT"){
      await chrome.storage.local.set({expected:d.target});
      await post("/receipt",{...d,verified:true,selected_after:selectedModel(),ts:new Date().toISOString()});
    }
  }catch{}
}
new MutationObserver(()=>check()).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
setInterval(check,2000); setInterval(poll,1500); bridge(); check();
