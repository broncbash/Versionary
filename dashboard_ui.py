"""Read-only administrative beta dashboard. No production actions or persistent credentials."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()
PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Patch Command | Agent Fleet</title>
<style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;background:#0f172a;color:#e2e8f0}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:#0f172a}
main{max-width:1180px;margin:auto;padding:36px 22px}header{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
h1{margin:0;color:#93c5fd;letter-spacing:.1em;font-size:clamp(1.5rem,4vw,2.5rem)}h2{font-size:1.1rem;margin:0 0 14px;color:#76c9ff}
.sub{color:#9db5c7}.eyebrow{letter-spacing:.2em;color:#8e9fb6;font-size:.75rem}
a{color:#67c9ff}.panel,.stat,.agent{border:1px solid #334155;background:#172338;border-radius:14px;padding:20px;box-shadow:0 0 24px #00000010}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:24px 0}input,button{font:inherit;border:1px solid #475569;border-radius:8px;background:#1e293b;color:#f8fafc;padding:12px}
input{min-width:240px;flex:1}button{cursor:pointer;border-color:#93c5fd}button:hover,button:focus-visible,a:focus-visible{outline:2px solid #93c5fd;outline-offset:3px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:24px}
.stat strong{display:block;font-size:2rem;color:#93c5fd;margin-top:5px}.stat span{color:#a4b8c9}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:14px}
.agent h3{margin:0;font-size:1.2rem;overflow-wrap:anywhere}.agent p{color:#a9c0d0}.meta{display:grid;grid-template-columns:1fr auto;gap:8px;font-size:.9rem}
.meta span:nth-child(2n){text-align:right;overflow-wrap:anywhere}.tag{display:inline-block;border:1px solid #458b9d;border-radius:20px;padding:4px 10px;margin-top:12px}
.approved{color:#93c5fd}.pending{color:#fbbf24}.revoked{color:#fda4af}
#message{min-height:24px;color:#ffcf91}#fleet:empty:after{content:'No agents to display.';color:#9db5c7}
footer{margin-top:28px;color:#93aabd;font-size:.85rem}
</style></head><body><main>
<header><div><div class="eyebrow">PATCH COMMAND</div><h1>Agent Fleet</h1><p class="sub">Infrastructure monitoring · Observer mode</p></div><a href="/admin/settings">Settings</a></header>
<section class="controls" aria-label="Administrator controls">
<input id="token" type="password" autocomplete="off" spellcheck="false" aria-label="Admin bearer token" placeholder="Admin bearer token (memory only)">
<button id="refresh" type="button">Refresh fleet</button><button id="clear" type="button">Clear access</button>
</section><p id="message" role="status" aria-live="polite">Enter an admin token to load the fleet.</p>
<section class="stats" aria-label="Fleet totals">
<div class="stat"><span>Registered</span><strong id="total">—</strong></div>
<div class="stat"><span>Approved</span><strong id="approved">—</strong></div>
<div class="stat"><span>Pending</span><strong id="pending">—</strong></div>
<div class="stat"><span>Reported updates</span><strong id="updates">—</strong></div>
</section><section class="panel"><h2>Registered agents</h2><div class="grid" id="fleet" aria-live="polite"></div></section>
<footer>Read-only dashboard. No scans, approvals, service changes, or deployments are initiated here. Update totals reflect latest successful reports, not live scans.</footer>
</main><script>
'use strict';
const $=id=>document.getElementById(id);
let credential='';
function clear(){
  credential='';$('token').value='';$('fleet').replaceChildren();
  for(const id of ['total','approved','pending','updates']) $(id).textContent='—';
}
function node(tag,text,className){
  const element=document.createElement(tag);
  element.textContent=text;
  if(className)element.className=className;
  return element;
}
function render(agents){
  $('fleet').replaceChildren();
  $('total').textContent=agents.length;
  $('approved').textContent=agents.filter(a=>a.status==='approved').length;
  $('pending').textContent=agents.filter(a=>a.status==='pending').length;
  $('updates').textContent=agents.reduce((sum,a)=>sum+(a.scan_status==='success'&&Number.isInteger(a.updates)?a.updates:0),0);
  for(const a of agents){
    const card=node('article','', 'agent');
    card.append(node('h3',a.hostname),node('p',a.platform));
    const meta=node('div','', 'meta');
    for(const [key,value] of [
      ['Last contact',a.last_seen||'Never'],
      ['Last scan',a.scan_at||'Never'],
      ['Scan status',a.scan_status||'No report'],
      ['Updates',a.scan_status==='success'&&a.updates!==null?String(a.updates):'Unknown']
    ]){meta.append(node('span',key),node('span',value));}
    card.append(meta,node('span',a.status,'tag '+a.status));
    $('fleet').append(card);
  }
}
$('clear').addEventListener('click',()=>{clear();$('message').textContent='Access cleared.';});
$('refresh').addEventListener('click',async()=>{
  credential=$('token').value||credential;
  $('token').value='';
  if(!credential){$('message').textContent='Enter an admin token.';return;}
  $('message').textContent='Loading fleet...';
  try{
    const response=await fetch('/api/v1/admin/agents',{
      headers:{Authorization:'Bearer '+credential},cache:'no-store',credentials:'omit'
    });
    if(!response.ok)throw Error('Inventory request failed (HTTP '+response.status+').');
    const data=await response.json();
    render(data.agents);
    $('message').textContent='Fleet loaded. Read-only snapshot.';
  }catch(error){clear();$('message').textContent=error.message;}
});
</script></body></html>'''

@router.get("/admin/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page():
    return HTMLResponse(PAGE, headers={
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
    })
