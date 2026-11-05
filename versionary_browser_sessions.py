"""Isolated HTTPS beta browser sessions; bearer-only API routes stay unchanged."""
import hashlib
import hmac
import secrets
import threading
import time
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from admin_auth import authenticate_admin
from admin_agents_api import list_agents
from agent_registry import approve_agent, revoke_agent
from uuid import UUID
from dashboard_ui import PAGE, dashboard_page

router = APIRouter(include_in_schema=False)
COOKIE = '__Host-versionary-beta-session'
LIFETIME = 3600
_sessions = {}
_lock = threading.Lock()

class LoginBody(BaseModel):
    token: str

def _digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def _session(request):
    raw=request.cookies.get(COOKIE, '')
    if len(raw)!=64:
        raise HTTPException(401,'Session required')
    key=_digest(raw)
    with _lock:
        record=_sessions.get(key)
        if record and record[0] <= time.monotonic():
            _sessions.pop(key,None)
            record=None
    if not record:
        raise HTTPException(401,'Session expired or invalid')
    return record

def _same_origin(request):
    origin=request.headers.get('origin')
    if origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403,'Origin validation failed')

def _csrf(request, record):
    _same_origin(request)
    supplied=request.headers.get('x-versionary-csrf','')
    if not supplied or not hmac.compare_digest(supplied,record[1]):
        raise HTTPException(403,'CSRF validation failed')

@router.post('/admin/session/login')
def login(body: LoginBody, request: Request, response: Response):
    _same_origin(request)
    if not authenticate_admin(body.token):
        raise HTTPException(401,'Invalid administrator token')
    raw=secrets.token_hex(32)
    csrf=secrets.token_hex(32)
    with _lock:
        now=time.monotonic()
        for key,value in list(_sessions.items()):
            if value[0]<=now: _sessions.pop(key,None)
        _sessions[_digest(raw)]=(now+LIFETIME,csrf)
    response.set_cookie(COOKIE,raw,max_age=LIFETIME,secure=True,httponly=True,
                        samesite='strict',path='/')
    response.headers['Cache-Control']='no-store'
    return {'csrf':csrf,'expires_in':LIFETIME}

@router.get('/admin/session/status')
def status(request: Request, response: Response):
    record=_session(request)
    response.headers['Cache-Control']='no-store'
    return {'authenticated':True,'csrf':record[1]}

@router.post('/admin/session/logout')
def logout(request: Request, response: Response):
    record=_session(request)
    _csrf(request,record)
    with _lock:
        _sessions.pop(_digest(request.cookies[COOKIE]),None)
    response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='strict')
    response.headers['Cache-Control']='no-store'
    return {'logged_out':True}

@router.get('/admin/session/agents')
def agents(request: Request):
    _session(request)
    return list_agents()

@router.post('/admin/session/agents/{agent_id}/{action}')
def agent_action(agent_id: UUID, action: str, request: Request):
    record=_session(request)
    _csrf(request,record)
    if action not in ('approve','revoke'):
        raise HTTPException(404,'Unknown action')
    result=(approve_agent if action=='approve' else revoke_agent)(str(agent_id))
    if not result:
        raise HTTPException(409,'Agent action rejected')
    return {'agent_id':str(agent_id),'status':'approved' if action=='approve' else 'revoked'}


def _beta_page():
    page = PAGE
    def swap(before, after):
        nonlocal page
        if page.count(before) != 1:
            raise RuntimeError("Dashboard compatibility mismatch: " + repr(before[:100]) + " count=" + str(page.count(before)))
        page = page.replace(before, after, 1)

    swap("let credential='';", "let credential='';\nlet csrf='';")
    swap("  credential='';inventory=[];$('token').value='';",
         "  credential='';csrf='';inventory=[];$('token').value='';")
    swap("if(!credential){\n    $('message').textContent='Administrator authentication required.';",
         "if(!csrf){\n    $('message').textContent='Administrator authentication required.';")
    swap("  const actionCredential=credential;", "  const actionCredential=csrf;")
    swap("'/api/v1/admin/agents/'+encodeURIComponent(agent.id)+'/'+action",
         "'/admin/session/agents/'+encodeURIComponent(agent.id)+'/'+action")
    swap("    const updated=await fetch('/api/v1/admin/agents',{\n      headers:{Authorization:'Bearer '+actionCredential},",
         "    const updated=await fetch('/admin/session/agents',{\n      headers:{},")
    swap("headers:{Authorization:'Bearer '+actionCredential}",
         "headers:{'X-Versionary-CSRF':actionCredential}")
    swap("const response=await fetch('/api/v1/admin/agents',{\n      headers:{Authorization:'Bearer '+requestCredential},cache:'no-store',credentials:'omit'",
         "const response=await fetch('/admin/session/agents',{\n      headers:{},cache:'no-store',credentials:'same-origin'")
    if page.count("credentials:'omit'") != 2:
        raise RuntimeError("Unexpected credential mode in dashboard")
    page = page.replace("credentials:'omit'", "credentials:'same-origin'")
    swap("$('clear').addEventListener('click',()=>{clear();$('message').textContent='Access cleared.';});",
         """$('clear').addEventListener('click',async()=>{
  const oldCsrf=csrf;
  clear();
  try { await fetch('/admin/session/logout',{method:'POST',credentials:'same-origin',
    headers:{'X-Versionary-CSRF':oldCsrf}}); } catch(_){}
  $('message').textContent='Access cleared.';
});""")
    start=page.index("  if(entered&&entered!==credential){")
    end=page.index("  const generation=sessionGeneration;",start)
    page=page[:start]+"""  if(entered){
    sessionGeneration++; inventoryGeneration++; inventoryTrusted=false;
    inventory=[]; render(inventory); csrf='';
    try {
      const login=await fetch('/admin/session/login',{method:'POST',
        credentials:'same-origin',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({token:entered})});
      if(!login.ok)throw Error('Administrator login failed (HTTP '+login.status+').');
      csrf=(await login.json()).csrf;
    }catch(error){clear();$('message').textContent=error.message;return;}
  }
  if(!csrf){$('message').textContent='Enter an admin token.';return;}
"""+page[end:]
    swap("  const requestCredential=credential;", "  const requestCredential=csrf;")
    swap("if(credential){\n  $('message').textContent='Restoring administrator access...';\n  $('refresh').click();\n}",
         """fetch('/admin/session/status',{credentials:'same-origin',cache:'no-store'})
  .then(r=>{if(!r.ok)throw Error('No session');return r.json();})
  .then(data=>{csrf=data.csrf;$('refresh').click();})
  .catch(()=>{});""")
    swap("Admin bearer token (memory only)", "Admin token (secure session)")
    return page

@router.get('/admin/dashboard', response_class=HTMLResponse)
def beta_dashboard():
    original = dashboard_page()
    headers = {
        key: value
        for key, value in original.headers.items()
        if key.lower() not in ("content-length", "content-type")
    }
    return HTMLResponse(_beta_page(), headers=headers)
