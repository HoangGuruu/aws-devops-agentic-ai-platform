"""Executed by a human account, never registered as an LLM tool."""
from pathlib import Path
import argparse,datetime,json,subprocess,time
import yaml
from .policy import digest,release_path,validate_proposal

def git(repo,*args):
    return subprocess.run(['git','-C',str(repo),*args],check=True,text=True,capture_output=True,timeout=30).stdout.strip()

def validate_release(doc):
    if not isinstance(doc,dict) or set(doc)!={'apiVersion','kind','metadata','spec'}:raise ValueError('Invalid release')
    if doc['apiVersion']!='apps/v1' or doc['kind']!='Deployment' or doc['metadata']!={'name':'productpage-v1'}:raise ValueError('Wrong recovery target')
    spec=doc['spec']
    if not isinstance(spec,dict) or not set(spec)<= {'replicas','template'} or 'template' not in spec:raise ValueError('Unexpected deployment fields')
    if 'replicas' in spec and (type(spec['replicas']) is not int or not 1<=spec['replicas']<=4):raise ValueError('Invalid replica bound')
    t=spec['template']
    if not isinstance(t,dict) or not set(t)<={'metadata','spec'}:raise ValueError('Unexpected pod fields')
    if 'metadata' in t:
        if set(t['metadata'])!={'annotations'} or set(t['metadata']['annotations'])!={'course.dev/restarted-at'}:raise ValueError('Unexpected annotations')
        if not isinstance(t['metadata']['annotations']['course.dev/restarted-at'],str):raise ValueError('Invalid restart value')
    if set(t['spec'])!={'containers'}:raise ValueError('Unexpected pod spec')
    cs=t['spec']['containers']
    if not isinstance(cs,list) or len(cs)!=1 or cs[0].get('name')!='productpage' or set(cs[0])!={'name','env'}:raise ValueError('Unexpected container')
    env=cs[0]['env']
    if not isinstance(env,list) or len(env)!=1 or set(env[0])!={'name','value'} or env[0]['name']!='LAB_FAULT_MODE' or env[0]['value'] not in ('off','http500'):raise ValueError('Invalid fault mode')
    return doc

def build_proposal(repo,environment,action,replicas=None):
    path=release_path(environment)
    now=int(time.time());params={}
    if action=='rollback':params={'commit':git(repo,'log','-1','--format=%H','--',path)}
    if action=='scale':params={'replicas':replicas}
    p={'version':1,'environment':environment,'action':action,'base_sha':git(repo,'rev-parse','HEAD'),'created_at':now,'expires_at':now+900,'parameters':params}
    return validate_proposal(p)

def preview(repo,p):
    validate_proposal(p)
    if git(repo,'status','--porcelain'):raise ValueError('Working tree must be clean, including untracked files')
    if git(repo,'rev-parse','HEAD')!=p['base_sha']:raise ValueError('Stale proposal: HEAD changed')
    path=release_path(p['environment'])
    target=Path(repo)/path
    if target.is_symlink() or target.resolve()!=Path(repo).resolve()/path:raise ValueError('Symlink target denied')
    old=validate_release(yaml.safe_load(target.read_text()))
    new=json.loads(json.dumps(old))
    if p['action']=='rollback':
        commit=p['parameters']['commit']
        if git(repo,'log','-1','--format=%H','--',path)!=commit:raise ValueError('Only latest release-file change can be reverted')
        if len(git(repo,'rev-list','--parents','-n','1',commit).split())!=2:raise ValueError('Cannot revert merge/root commit')
        files=git(repo,'diff-tree','--no-commit-id','--name-only','-r',commit).splitlines()
        if files!=[path]:raise ValueError('Rollback only accepts an isolated release.yaml commit')
        new=validate_release(yaml.safe_load(git(repo,'show',f'{commit}^:{path}')))
        if new['spec']['template']['spec']['containers'][0]['env'][0]['value']!='off':raise ValueError('Rollback target must disable fault')
    elif p['action']=='restart':
        new['spec']['template']['metadata']={'annotations':{'course.dev/restarted-at':datetime.datetime.fromtimestamp(p['created_at'],datetime.timezone.utc).isoformat()}}
    elif p['action']=='scale':new['spec']['replicas']=p['parameters']['replicas']
    validate_release(new)
    if old==new:raise ValueError('No recovery change required')
    return path,old,new

def apply(repo,p,approval,push=False):
    if approval!=digest(p):raise ValueError('Approval digest does not match proposal')
    path,old,new=preview(repo,p)
    target=Path(repo)/path
    target.write_text(yaml.safe_dump(new,sort_keys=False))
    git(repo,'add','--',path)
    git(repo,'commit','-m',f"recovery({p['environment']}): approved {p['action']} {digest(p)[:12]}")
    commit=git(repo,'rev-parse','HEAD')
    if push:git(repo,'push')
    return {'status':'committed_and_pushed' if push else 'committed_not_pushed','commit':commit,'recovery_verified':False,'next':'Wait for Argo CD; run agent.cli verify against the live app.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('proposal');p.add_argument('--repo',default='.');p.add_argument('--approve');p.add_argument('--push',action='store_true');a=p.parse_args()
    proposal=json.loads(Path(a.proposal).read_text());proposal=proposal.get('proposal',proposal)
    if a.approve:print(json.dumps(apply(a.repo,proposal,a.approve,a.push),indent=2))
    else:
        path,old,new=preview(a.repo,proposal)
        print(json.dumps({'path':path,'before':old,'after':new,'approval_digest':digest(proposal)},indent=2))
if __name__=='__main__':main()
