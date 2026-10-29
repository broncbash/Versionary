"""Self-contained admin settings page; no external assets or token persistence."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARBY PATCH COMMAND | Settings</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#080d17;color:#d8f9ff}
body{margin:0 auto;max-width:800px;padding:2rem 1rem;background:radial-gradient(circle at 95% 5%,#163449,transparent 45%)}
h1{letter-spacing:.1em;color:#47f5dc}h2{font-size:1.1rem;color:#69bbff}
.panel{border:1px solid #2b8098;border-radius:14px;padding:1.5rem;background:#0d1929e8;box-shadow:0 0 24px #08d4cf13}
label{display:block;margin:1rem 0 .35rem}input,select,button{font:inherit;border-radius:7px;padding:.65rem;background:#101f31;color:#fff;border:1px solid #417c96;box-sizing:border-box}
input:not([type=checkbox]),select{width:100%}input[type=checkbox]{width:1.1rem;height:1.1rem}button{cursor:pointer;border-color:#35e3cf;margin:.75rem .5rem .25rem 0}button:hover,button:focus-visible{outline:2px solid #45f3dc}
.note{color:#a6b8c9;font-size:.9rem}#status{white-space:pre-wrap;min-height:2em} .warn{color:#ffce7d}
</style></head><body><h1>ARBY // SETTINGS</h1>
<p class="warn">STAGING MODE — changes are saved but not applied to running services.</p>
<main class="panel"><h2>Administrator access</h2>
<label for="token">Admin bearer token (kept in this tab's memory only)</label><input id="token" type="password" autocomplete="off" spellcheck="false">
<button id="load" type="button">Load settings</button>
<form id="settings" hidden><h2>Server configuration</h2>
<label for="public_url">Public HTTPS origin</label><input id="public_url" placeholder="https://patch.example.org" autocomplete="off">
<label for="scan_interval_minutes">Scan interval (minutes)</label><input id="scan_interval_minutes" type="number" min="5" max="10080" required>
<label for="appearance">Appearance</label><select id="appearance"><option value="cyberpunk">Cyberpunk</option><option value="dark">Dark</option><option value="light">Light</option></select>
<label for="tls_mode">TLS mode</label><select id="tls_mode"><option value="external">External proxy</option><option value="local_ca">Local CA</option><option value="provided">Provided certificate</option></select>
<label><input id="enrollment_enabled" type="checkbox"> Enable agent enrollment (staged)</label>
<label><input id="reporting_enabled" type="checkbox"> Enable agent reporting (staged)</label>
<button type="submit">Save staged settings</button></form>
<p id="status" role="status" aria-live="polite"></p><p class="note">No automatic deployments, service restarts, or certificate changes.</p></main>
<script>
'use strict';
const $ = id => document.getElementById(id);
const keys = ['public_url','scan_interval_minutes','appearance','tls_mode','enrollment_enabled','reporting_enabled'];
let token = '';
function status(message){ $('status').textContent = message; }
async function request(method, data){
  const headers = {'Authorization':'Bearer '+token};
  if(data !== undefined) headers['Content-Type']='application/json';
  const response = await fetch('/api/v1/admin/settings',{method,headers,cache:'no-store',credentials:'omit',body:data === undefined ? undefined : JSON.stringify(data)});
  const result = await response.json();
  if(!response.ok) throw Error('HTTP '+response.status+': '+(typeof result.detail === 'string' ? result.detail : 'Request rejected'));
  return result;
}
function populate(values){
  for(const key of keys){const element=$(key);if(element.type === 'checkbox') element.checked=values[key];else element.value=values[key] ?? '';}
}
$('load').addEventListener('click',async()=>{
  token=$('token').value; $('token').value=''; $('settings').hidden=true;
  if(!token){status('Enter your admin token.');return;}
  try{const result=await request('GET');populate(result.settings);$('settings').hidden=false;status('Settings loaded. Changes are staged only.');}
  catch(error){token='';status(error.message);}
});
$('settings').addEventListener('submit',async event=>{
  event.preventDefault();
  const changes={};
  for(const key of keys){const element=$(key);changes[key]=element.type==='checkbox'?element.checked:key==='scan_interval_minutes'?Number(element.value):key==='public_url'?(element.value.trim()||null):element.value;}
  try{const result=await request('PATCH',changes);populate(result.settings);status('Saved successfully. Not applied to running services.');}
  catch(error){status(error.message);}
});
</script></body></html>'''

@router.get('/admin/settings', response_class=HTMLResponse, include_in_schema=False)
def settings_page():
    return HTMLResponse(PAGE, headers={
        'Cache-Control': 'no-store',
        'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'",
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'X-Frame-Options': 'DENY',
    })
