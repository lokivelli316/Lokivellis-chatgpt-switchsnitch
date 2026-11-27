// Loopback-only broker. Content scripts cannot depend on page CORS/local-network policy.
const allowed=new Set(["/health","/decision","/event","/receipt","/surface"]);
chrome.runtime.onMessage.addListener((m,s,reply)=>{
 if(m?.kind!=="switchsnitch-http")return;
 if(!s.tab||!s.url||new URL(s.url).origin!=="https://chatgpt.com")return;
 let u;try{u=new URL(m.base)}catch{return}
 if(u.protocol!=="http:"||u.hostname!=="127.0.0.1"||+u.port<8765||+u.port>8864||u.pathname!=="/"||u.username||u.password||u.search||u.hash||!allowed.has(m.path)){reply({ok:false,error:"ENDPOINT_DENIED"});return}
 const method=m.options?.method||"GET";
 if(!(["GET","POST"].includes(method))||(method==="GET")!==["/health","/decision"].includes(m.path)){reply({ok:false,error:"METHOD_DENIED"});return}
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),1800);
 fetch(u.origin+m.path,{method,headers:m.options?.headers,body:method==="POST"?m.options?.body:undefined,signal:ctl.signal,redirect:"error",credentials:"omit",cache:"no-store"}).then(async r=>reply({ok:true,status:r.status,data:await r.json()})).catch(e=>reply({ok:false,error:String(e)})).finally(()=>clearTimeout(timer));
 return true;
});
