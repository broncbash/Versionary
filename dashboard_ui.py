"""Administrative beta dashboard with authenticated agent lifecycle controls."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()
PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Versionary | Agent Fleet</title>
<style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;background:#0f172a;color:#e2e8f0}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:#0f172a}
main{max-width:1180px;margin:auto;padding:36px 22px}header{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
h1{margin:0;color:#93c5fd;letter-spacing:.1em;font-size:clamp(1.5rem,4vw,2.5rem)}h2{font-size:1.1rem;margin:0 0 14px;color:#76c9ff}
.sub{color:#9db5c7}.eyebrow{letter-spacing:.2em;color:#8e9fb6;font-size:.75rem}
a{color:#67c9ff}.panel,.stat,.agent{border:1px solid #334155;background:#172338;border-radius:14px;padding:20px;box-shadow:0 0 24px #00000010}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:24px 0}input,button{font:inherit;border:1px solid #475569;border-radius:8px;background:#1e293b;color:#f8fafc;padding:12px}
input{min-width:180px;flex:1}select{font:inherit;border:1px solid #475569;border-radius:8px;background:#1e293b;color:#f8fafc;padding:12px}.filters{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 20px}.filters input{max-width:360px}.filters select{min-width:150px}.muted{color:#94a3b8}button{cursor:pointer;border-color:#93c5fd}button:hover,button:focus-visible,a:focus-visible{outline:2px solid #93c5fd;outline-offset:3px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:24px}
.stat strong{display:block;font-size:2rem;color:#93c5fd;margin-top:5px}.stat span{color:#a4b8c9}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,350px),1fr));gap:16px}
.agent{min-width:0;padding:22px}
.agent h3{margin:0;font-size:1.2rem;overflow-wrap:anywhere}
.agent p{color:#a9c0d0}
.meta{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.35fr);gap:12px 16px;font-size:.9rem;align-items:start}
.meta span:nth-child(2n){text-align:right;overflow-wrap:anywhere;line-height:1.5}
.meta span:nth-child(2n)[title]{font-variant-numeric:tabular-nums}
.tag{display:inline-block;border:1px solid #458b9d;border-radius:20px;padding:4px 10px;margin-top:16px}
@media(max-width:420px){
  main{padding:24px 14px}
  .agent{padding:16px}
  .meta{grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:10px}
}
.agent-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.agent-actions button{font-size:.85rem;padding:9px 12px}.agent-actions button:disabled{opacity:.55;cursor:wait}.agent-actions .danger{border-color:#fb7185;color:#fecdd3}.approved,.online{color:#86efac}.pending,.stale,.no_contact,.unknown{color:#fbbf24}.revoked{color:#fda4af}.error{color:#fda4af}
#message{min-height:24px;color:#ffcf91}#fleet:empty:after{content:'No agents to display.';color:#9db5c7}
footer{margin-top:28px;color:#93aabd;font-size:.85rem}
.agent-identity{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.agent-labels{min-width:0}.agent-labels p{margin:5px 0 0}
.distro-mark{flex:none;display:grid;place-items:center;width:48px;height:48px;border-radius:13px;font-size:1.25rem;font-weight:800;background:#334155;color:white;border:1px solid #64748b}
.distro-cachyos{background:#235d72;color:#a5f3fc}.distro-arch{background:#136b9c}.distro-debian{background:#a80030}.distro-ubuntu{background:#a83b15}.distro-fedora{background:#294a90}.distro-opensuse{background:#417c19}.distro-almalinux{background:#326b6d}.distro-rocky{background:#087a5a}.distro-rhel{background:#9c2727}
</style></head><body><main>
<header><div><div class="eyebrow">VERSIONARY · PRIVATE BETA</div><h1>Agent Fleet</h1><p class="sub">Infrastructure monitoring · Observer mode</p></div><a href="/admin/settings">Settings</a></header>
<section class="controls" aria-label="Administrator controls">
<input id="token" type="password" autocomplete="off" spellcheck="false" aria-label="Admin bearer token" placeholder="Admin bearer token (memory only)">
<button id="refresh" type="button">Refresh fleet</button><button id="clear" type="button">Clear access</button>
</section><p id="message" role="status" aria-live="polite">Enter an admin token to load the fleet.</p>
<section class="stats" aria-label="Fleet totals">
<div class="stat"><span>Registered</span><strong id="total">—</strong></div>
<div class="stat"><span>Approved</span><strong id="approved">—</strong></div>
<div class="stat"><span>Pending</span><strong id="pending">—</strong></div>
<div class="stat"><span>Reported updates</span><strong id="updates">—</strong></div><div class="stat"><span>Online</span><strong id="online">—</strong></div><div class="stat"><span>Needs attention</span><strong id="attention">—</strong></div>
</section><section class="panel"><h2>Registered agents</h2><div class="filters" aria-label="Fleet filters"><input id="search" type="search" aria-label="Search agents" placeholder="Search hostname or platform"><select id="status-filter" aria-label="Filter by approval status"><option value="all">All statuses</option><option value="approved">Approved</option><option value="pending">Pending</option><option value="revoked">Revoked</option></select><select id="sort" aria-label="Sort agents"><option value="name">Hostname</option><option value="updates">Most updates</option><option value="contact">Recent contact</option></select></div><p id="results" class="muted" role="status" aria-live="polite"></p><div class="grid" id="fleet" aria-live="polite"></div></section>
<footer>Administrator-approved agent lifecycle actions are available. Revocation is permanent for the selected agent identity. No scans, package installations, reboots, or deployments are initiated here. Online means an approved agent reported a heartbeat within 30 minutes. Update totals reflect latest successful reports, not live scans.</footer>
</main><script>
'use strict';
const $=id=>document.getElementById(id);
let credential='';
let inventory=[];
let sessionGeneration=0;
let inventoryGeneration=0;
let inventoryTrusted=false;
function clear(){
  sessionGeneration++;
  inventoryGeneration++;
  inventoryTrusted=false;
  credential='';inventory=[];$('token').value='';$('fleet').replaceChildren();$('results').textContent='';
  for(const id of ['total','approved','pending','updates','online','attention']) $(id).textContent='—';
}
function node(tag,text,className){
  const element=document.createElement(tag);
  element.textContent=text;
  if(className)element.className=className;
  return element;
}
function formatTimestamp(value){
  if(!value)return 'Never';
  const parsed=new Date(value);
  if(Number.isNaN(parsed.getTime()))return 'Invalid timestamp';
  return new Intl.DateTimeFormat(undefined,{
    year:'numeric',month:'short',day:'numeric',
    hour:'numeric',minute:'2-digit',timeZoneName:'short'
  }).format(parsed);
}
let lifecycleBusy=false;
async function manageAgent(agent,action,button){
  if(lifecycleBusy)return;
  if(!['approve','revoke'].includes(action))return;
  if(!inventoryTrusted){
    $('message').textContent='Refresh fleet before managing agents.';
    return;
  }
  const current=inventory.find(a=>a.id===agent.id);
  if(!current||current.status!==agent.status||
     (action==='approve'&&current.status!=='pending')||
     (action==='revoke'&&!['pending','approved'].includes(current.status))){
    $('message').textContent='Agent status changed. Refresh fleet before continuing.';
    return;
  }
  if(!credential){
    $('message').textContent='Administrator authentication required.';
    return;
  }
  const revoke=action==='revoke';
  const warning=revoke
    ? 'PERMANENTLY revoke '+agent.hostname+' ('+agent.id+')? This identity cannot be approved again.'
    : 'Approve pending agent '+agent.hostname+' ('+agent.id+')?';
  if(revoke){
    const typed=window.prompt(
      warning+'\\n\\nType REVOKE to confirm permanent revocation:'
    );
    if(typed!=='REVOKE'){
      $('message').textContent='Revocation cancelled.';
      return;
    }
  }else if(!window.confirm(warning)){
    return;
  }
  if(lifecycleBusy)return;
  lifecycleBusy=true;
  inventoryTrusted=false;
  const generation=sessionGeneration;
  const actionCredential=credential;
  button.disabled=true;
  $('message').textContent=(revoke?'Revoking ':'Approving ')+agent.hostname+'...';
  let mutationSucceeded=false;
  try{
    const response=await fetch(
      '/api/v1/agents/'+encodeURIComponent(agent.id)+'/'+action,{
        method:'POST',
        headers:{Authorization:'Bearer '+actionCredential},
        cache:'no-store',
        credentials:'omit'
      }
    );
    if(generation!==sessionGeneration)return;
    if(!response.ok){
      throw Error('Action rejected (HTTP '+response.status+'). Refresh and check agent status.');
    }
    mutationSucceeded=true;
    const updated=await fetch('/api/v1/admin/agents',{
      headers:{Authorization:'Bearer '+actionCredential},
      cache:'no-store',
      credentials:'omit'
    });
    if(!updated.ok)throw Error('Action completed, but fleet refresh failed.');
    const data=await updated.json();
    if(generation!==sessionGeneration)return;
    if(!Array.isArray(data.agents))throw Error('Unexpected fleet response.');
    inventory=data.agents;
    inventoryTrusted=true;
    render(inventory);
    $('message').textContent=agent.hostname+
      (revoke?' revoked.':' approved.')+' Fleet refreshed.';
  }catch(error){
    if(generation!==sessionGeneration)return;
    inventoryTrusted=false;
    $('message').textContent=mutationSucceeded
      ? 'Agent action succeeded, but fleet refresh failed. Refresh fleet before another action.'
      : 'Agent action outcome may be uncertain. Refresh fleet and verify status before retrying. '+error.message;
    inventory=[];
    render(inventory);
  }finally{
    lifecycleBusy=false;
    button.disabled=false;
  }
}
function render(agents){
  $('fleet').replaceChildren();
  $('total').textContent=agents.length;
  $('approved').textContent=agents.filter(a=>a.status==='approved').length;
  $('pending').textContent=agents.filter(a=>a.status==='pending').length;
  $('updates').textContent=agents.reduce((sum,a)=>sum+(a.scan_status==='success'&&Number.isInteger(a.updates)?a.updates:0),0);
  $('online').textContent=agents.filter(a=>a.health==='online').length;
  $('attention').textContent=agents.filter(a=>['stale','no_contact','unknown'].includes(a.health)||a.scan_status==='error').length;
  const query=$('search').value.trim().toLocaleLowerCase();
  const status=$('status-filter').value;
  const selected=agents.filter(a=>(status==='all'||a.status===status)&&
    (String(a.hostname).toLocaleLowerCase().includes(query)||String(a.platform).toLocaleLowerCase().includes(query)));
  const order=$('sort').value;
  selected.sort((a,b)=>order==='updates' ?
    ((b.scan_status==='success'?b.updates:-1)??-1)-((a.scan_status==='success'?a.updates:-1)??-1)||a.hostname.localeCompare(b.hostname) :
    order==='contact' ? String(b.last_seen||'').localeCompare(String(a.last_seen||''))||a.hostname.localeCompare(b.hostname) :
    a.hostname.localeCompare(b.hostname));
  $('results').textContent='Showing '+selected.length+' of '+agents.length+' agents';
  for(const a of selected){
    const card=node('article','', 'agent');
    const identity=node('div','', 'agent-identity');
    const distro=String(a.distro_id||a.platform||'linux').toLowerCase();
    const distroName=String(a.distro_name||a.platform||'Linux');
    const logos={cachyos:'C',arch:'A',debian:'D',ubuntu:'U',fedora:'F',opensuse:'S',almalinux:'Al',rocky:'R',rhel:'RH'};
    const mark=node('span',logos[distro]||'L','distro-mark distro-'+(Object.hasOwn(logos,distro)?distro:'linux'));
    mark.setAttribute('role','img');mark.setAttribute('aria-label',distroName+' distribution');
    const info=node('div','', 'agent-labels');
    info.append(node('h3',a.hostname),node('p',distroName));
    identity.append(mark,info);card.append(identity);
    const meta=node('div','', 'meta');
    for(const [key,value] of [
      ['Connection',a.health==='online'?'Online':a.health==='stale'?'Stale (>30 min)':a.health==='no_contact'?'No heartbeat':a.health==='unknown'?'Unknown':a.health],
      ['Last contact',formatTimestamp(a.last_seen)],
      ['Last scan',formatTimestamp(a.scan_at)],
      ['Scan status',a.scan_status||'No report'],
      ['Updates',a.scan_status==='success'&&a.updates!==null?String(a.updates):'Unknown']
    ]){
      const label=node('span',key);
      const detail=node('span',value);
      if((key==='Last contact'&&a.last_seen)||(key==='Last scan'&&a.scan_at)){
        detail.title=key==='Last contact'?String(a.last_seen):String(a.scan_at);
      }
      meta.append(label,detail);
    }
    card.append(meta,node('span',a.status,'tag '+a.status));
    if(a.status==='pending'||a.status==='approved'){
      const actions=node('div','','agent-actions');
      if(a.status==='pending'){
        const approve=node('button','Approve agent');
        approve.type='button';
        approve.addEventListener('click',()=>manageAgent(a,'approve',approve));
        actions.append(approve);
      }
      const revoke=node('button','Revoke identity','danger');
      revoke.type='button';
      revoke.addEventListener('click',()=>manageAgent(a,'revoke',revoke));
      actions.append(revoke);
      card.append(actions);
    }
    if(a.scan_status==='error') card.append(node('p','Latest scan failed','error'));
    $('fleet').append(card);
  }
}
for(const id of ['search','status-filter','sort']){
  $(id).addEventListener(id==='search'?'input':'change',()=>render(inventory));
}
$('clear').addEventListener('click',()=>{clear();$('message').textContent='Access cleared.';});
$('refresh').addEventListener('click',async()=>{
  if(lifecycleBusy){
    $('message').textContent='Wait for the current agent action to finish.';
    return;
  }
  const entered=$('token').value;
  $('token').value='';
  if(entered&&entered!==credential){
    sessionGeneration++;
    inventoryTrusted=false;
    inventory=[];
    render(inventory);
  }
  credential=entered||credential;
  if(!credential){$('message').textContent='Enter an admin token.';return;}
  const generation=sessionGeneration;
  const request=++inventoryGeneration;
  const requestCredential=credential;
  inventoryTrusted=false;
  $('message').textContent='Loading fleet...';
  try{
    const response=await fetch('/api/v1/admin/agents',{
      headers:{Authorization:'Bearer '+requestCredential},cache:'no-store',credentials:'omit'
    });
    if(generation!==sessionGeneration||request!==inventoryGeneration)return;
    if(!response.ok)throw Error('Inventory request failed (HTTP '+response.status+').');
    const data=await response.json();
    if(generation!==sessionGeneration||request!==inventoryGeneration)return;
    if(!Array.isArray(data.agents))throw Error('Unexpected fleet response.');
    inventory=data.agents;
    inventoryTrusted=true;
    render(inventory);
    $('message').textContent='Fleet loaded. Administrator controls available.';
  }catch(error){
    if(generation!==sessionGeneration||request!==inventoryGeneration)return;
    clear();
    $('message').textContent=error.message;
  }
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
