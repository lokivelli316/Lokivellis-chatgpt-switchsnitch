const expected=document.querySelector("#expected"), status=document.querySelector("#status");
chrome.storage.local.get({expected:"GPT-5.6 Sol"},v=>expected.value=v.expected);
document.querySelector("#save").onclick=()=>chrome.storage.local.set({expected:expected.value},()=>status.textContent="Saved: "+expected.value);
