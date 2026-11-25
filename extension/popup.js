const expected=document.querySelector("#expected"),token=document.querySelector("#token"),status=document.querySelector("#status"),health=document.querySelector("#health");
chrome.storage.local.get({expected:"GPT-5.6 Sol",bridgeToken:"",bridgeHealth:null},v=>{expected.value=v.expected;token.value=v.bridgeToken||"";renderHealth(v.bridgeHealth)});
function renderHealth(h){if(!h){health.textContent="Bridge: unverified";return}health.textContent=h.ok===false?"Bridge: DEGRADED "+(h.degraded||""):"Bridge: "+(h.notification||"connected")+" / "+(h.security_posture||"security unverified");health.className=h.ok===false?"bad":"ok"}
document.querySelector("#saveExpected").onclick=()=>chrome.storage.local.set({expected:expected.value},()=>status.textContent="Expected model explicitly set: "+expected.value);
document.querySelector("#saveToken").onclick=()=>{const v=token.value.trim();if(!v){status.textContent="Token required";return}chrome.storage.local.set({bridgeToken:v},()=>status.textContent="Bridge token provisioned")};
document.querySelector("#clearToken").onclick=()=>chrome.storage.local.set({bridgeToken:"",bridgeHealth:{ok:false,degraded:"TOKEN_CLEARED"}},()=>{token.value="";status.textContent="Local extension token cleared. Bridge token was NOT rotated."});
chrome.storage.onChanged.addListener((c,a)=>{if(a==="local"&&c.bridgeHealth)renderHealth(c.bridgeHealth.newValue)});
