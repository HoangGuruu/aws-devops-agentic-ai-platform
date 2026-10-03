from pathlib import Path
import argparse,json,sys,urllib.request
from .engine import investigate,demo
from .tools import ROOT,Toolbox,SnapshotBackend,LiveBackend
from .recovery import build_proposal

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    inv=sub.add_parser('investigate');inv.add_argument('--mode',choices=['demo','live','snapshot'],default='demo');inv.add_argument('--incident',required=True);inv.add_argument('--snapshot',default=str(ROOT/'examples/evidence.json'));inv.add_argument('--output',required=True);inv.add_argument('--environment',default='develop');inv.add_argument('--repo',default='.');inv.add_argument('--enable-proposals',action='store_true')
    proposal=sub.add_parser('propose');proposal.add_argument('--action',choices=['rollback','restart','scale'],required=True);proposal.add_argument('--replicas',type=int);proposal.add_argument('--environment',default='develop');proposal.add_argument('--repo',default='.');proposal.add_argument('--output',required=True)
    verify=sub.add_parser('verify');verify.add_argument('--environment',default='develop');verify.add_argument('--url',default='http://127.0.0.1:9080/productpage');verify.add_argument('--output',required=True)
    a=p.parse_args()
    if a.command=='investigate':
        incident=json.loads(Path(a.incident).read_text())
        backend=LiveBackend(a.environment) if a.mode=='live' else SnapshotBackend(json.loads(Path(a.snapshot).read_text()))
        toolbox=Toolbox(backend,a.environment,a.repo,a.enable_proposals and a.mode!='demo')
        result=demo(toolbox,incident) if a.mode=='demo' else investigate(incident,toolbox)
        result['evidence_source']=a.mode
        if a.mode=='snapshot':result['mode']='bedrock-with-supplied-snapshot'
        # Save newest validated proposal separately for the human-operated executor.
        if result.get('proposals'):
            q=Path(a.output).with_suffix('.proposal.json');q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(result['proposals'][-1],indent=2))
    elif a.command=='propose':result=build_proposal(a.repo,a.environment,a.action,a.replicas)
    else:
        backend=LiveBackend(a.environment);state=backend.read('inspect_kubernetes');argo=backend.read('inspect_gitops')
        try:
            with urllib.request.urlopen(a.url,timeout=10) as r:http=r.status
        except Exception:http=None
        result={'http_status':http,'kubernetes':state,'gitops':argo,'recovery_verified':http==200 and state['fault_mode']=='off' and state['available']>=state['desired'] and argo['status'].get('status')=='Synced' and argo['health'].get('status')=='Healthy','note':'Point-in-time verification; keep load running and confirm alert resolves over the next metrics window.'}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2,default=str))
    print(f'Saved {dest}')
    if a.command=='verify' and not result['recovery_verified']:sys.exit(1)
if __name__=='__main__':main()
