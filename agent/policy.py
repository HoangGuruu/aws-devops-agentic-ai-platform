"""Deterministic recovery policy, shared by proposer and human-operated executor."""
import hashlib,json,re,time
ENVS={'develop','uat','staging','prod'}
ACTIONS={'rollback','restart','scale'}
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def digest(proposal):return hashlib.sha256(canonical(proposal).encode()).hexdigest()
def release_path(environment):
    if environment not in ENVS:raise ValueError('Unsupported environment')
    return f'gitops/overlays/{environment}/release.yaml'
def validate_proposal(p,now=None):
    required={'version','environment','action','base_sha','created_at','expires_at','parameters'}
    if set(p)!=required or p['version']!=1:raise ValueError('Invalid proposal structure')
    release_path(p['environment'])
    if p['action'] not in ACTIONS:raise ValueError('Action denied')
    if not isinstance(p['base_sha'],str) or not re.fullmatch(r'[0-9a-f]{40}',p['base_sha']):raise ValueError('Invalid base SHA')
    now=time.time() if now is None else now
    if not all(type(p[x]) in (int,float) for x in ('created_at','expires_at')):raise ValueError('Invalid time')
    if not p['created_at']<=now<=p['expires_at'] or not 0<p['expires_at']-p['created_at']<=900:raise ValueError('Expired/future proposal')
    params=p['parameters']
    if not isinstance(params,dict):raise ValueError('Invalid parameters')
    if p['action']=='rollback':
        if set(params)!={'commit'} or not re.fullmatch(r'[0-9a-f]{40}',str(params['commit'])):raise ValueError('Invalid rollback commit')
    if p['action']=='restart' and params:raise ValueError('Restart takes no parameters')
    if p['action']=='scale':
        if set(params)!={'replicas'} or type(params['replicas']) is not int or not 1<=params['replicas']<=4:raise ValueError('Replicas must be 1..4')
    return p
