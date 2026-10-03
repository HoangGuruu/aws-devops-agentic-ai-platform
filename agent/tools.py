"""Bounded read-only tools. No arbitrary shell, PromQL, URL, namespace, or secret access."""
from pathlib import Path
import json,os,re,urllib.parse,urllib.request
from .recovery import build_proposal
from .policy import digest,ENVS

ROOT=Path(__file__).resolve().parents[1]
def redact(value):
    text=json.dumps(value,default=str)
    text=re.sub(r'(mongodb(?:\+srv)?://)[^\s"@]+@',r'\1[REDACTED]@',text)
    text=re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9._-]+',r'\1[REDACTED]',text)
    text=re.sub(r'AKIA[A-Z0-9]{16}','[REDACTED_AWS_KEY]',text)
    text=re.sub(r'(?i)((?:password|token|secret)[=:]\s*)[^\s,"\\]+',r'\1[REDACTED]',text)
    # Defense in depth, not comprehensive DLP. Use synthetic data in the course.
    return text[:24000]

def schema(name,description,properties=None,required=None):
    return {'toolSpec':{'name':name,'description':description,'inputSchema':{'json':{'type':'object','properties':properties or {},'required':required or [],'additionalProperties':False}}}}
TOOLS=[
 schema('inspect_kubernetes','Read Bookinfo pod state and productpage deployment; no secret/env dump.'),
 schema('read_logs','Read up to 60 recent productpage log lines.'),
 schema('query_metrics','Read fixed productpage error ratio query.'),
 schema('inspect_gitops','Read Argo CD sync and health status.'),
 schema('search_runbooks','Retrieve relevant incident runbooks.',{'query':{'type':'string','maxLength':500}},['query']),
 schema('propose_recovery','Create a proposal ONLY. A separate human process reviews and executes it.',{'action':{'type':'string','enum':['rollback','restart','scale']},'replicas':{'type':'integer','minimum':1,'maximum':4}},['action'])
]
class SnapshotBackend:
    def __init__(self,snapshot):self.snapshot=snapshot
    def read(self,name):
        if name not in self.snapshot:raise ValueError(f'Missing evidence: {name}')
        return self.snapshot[name]

class LiveBackend:
    def __init__(self,environment='develop'):
        if environment not in ENVS:raise ValueError('Environment denied')
        from kubernetes import client,config
        if os.environ.get('KUBERNETES_SERVICE_HOST'):config.load_incluster_config()
        else:config.load_kube_config(context=os.environ.get('KUBE_CONTEXT') or None)
        self.core=client.CoreV1Api();self.apps=client.AppsV1Api();self.custom=client.CustomObjectsApi()
        self.ns=f'bookinfo-{environment}';self.environment=environment
    def read(self,name):
        if name=='inspect_kubernetes':
            pods=self.core.list_namespaced_pod(self.ns,label_selector='app=productpage',_request_timeout=15)
            d=self.apps.read_namespaced_deployment('productpage-v1',self.ns,_request_timeout=15)
            c=d.spec.template.spec.containers[0]
            return {'namespace':self.ns,'deployment':'productpage-v1','desired':d.spec.replicas,'available':d.status.available_replicas or 0,'image':c.image,'fault_mode':next((e.value for e in c.env or [] if e.name=='LAB_FAULT_MODE'),'off'),'pods':[{'name':p.metadata.name,'phase':p.status.phase,'containers':[{'name':s.name,'ready':s.ready,'restarts':s.restart_count} for s in p.status.container_statuses or []]} for p in pods.items]}
        if name=='read_logs':
            pods=self.core.list_namespaced_pod(self.ns,label_selector='app=productpage',_request_timeout=15)
            return [{'pod':p.metadata.name,'logs':self.core.read_namespaced_pod_log(p.metadata.name,self.ns,container='productpage',tail_lines=60,since_seconds=600,limit_bytes=12000,_request_timeout=15)} for p in pods.items[:2]]
        if name=='inspect_gitops':
            obj=self.custom.get_namespaced_custom_object('argoproj.io','v1alpha1','argocd','applications',f'bookinfo-{self.environment}',_request_timeout=15)
            return {'application':obj['metadata']['name'],'status':obj.get('status',{}).get('sync',{}),'health':obj.get('status',{}).get('health',{})}
        if name=='query_metrics':
            base=os.environ.get('PROMETHEUS_URL','http://127.0.0.1:9090')
            query=f'sum(rate(bookinfo_http_responses_total{{namespace="{self.ns}",path="/productpage",status=~"5.."}}[2m])) / clamp_min(sum(rate(bookinfo_http_responses_total{{namespace="{self.ns}",path="/productpage"}}[2m])), 0.001)'
            url=base.rstrip('/')+'/api/v1/query?'+urllib.parse.urlencode({'query':query})
            with urllib.request.urlopen(url,timeout=15) as r:
                result=json.loads(r.read(64000))
            if result.get('status')!='success':raise ValueError('Prometheus query failed')
            return result
        raise ValueError('Unknown read tool')

class Toolbox:
    def __init__(self,backend,environment='develop',repo=ROOT,proposal_enabled=False):
        if environment not in ENVS:raise ValueError('Environment denied')
        self.backend=backend;self.environment=environment;self.repo=Path(repo);self.proposal_enabled=proposal_enabled
        self.proposals=[];self.local_retrieval_only=False
    def run(self,name,args):
        if name not in [t['toolSpec']['name'] for t in TOOLS] or not isinstance(args,dict):raise ValueError('Tool denied')
        if name in ('inspect_kubernetes','read_logs','query_metrics','inspect_gitops'):
            if args:raise ValueError('Read tools take no arguments')
            result = redact(self.backend.read(name))
            try: return json.loads(result)
            except json.JSONDecodeError: return {'truncated_evidence': result}
        if name=='search_runbooks':
            if set(args)!={'query'} or not isinstance(args['query'],str) or not 1<=len(args['query'])<=500:raise ValueError('Invalid search')
            if os.environ.get('BEDROCK_KB_ID') and not self.local_retrieval_only:
                import boto3
                r=boto3.client('bedrock-agent-runtime').retrieve(knowledgeBaseId=os.environ['BEDROCK_KB_ID'],retrievalQuery={'text':args['query']},retrievalConfiguration={'vectorSearchConfiguration':{'numberOfResults':3}})
                return {'source':'bedrock-knowledge-base','results':[{'text':v.get('content',{}).get('text','')[:5000],'location':v.get('location',{}),'score':v.get('score')} for v in r['retrievalResults']]}
            terms=set(re.findall(r'\w+',args['query'].lower()))
            scored=[]
            for p in sorted((ROOT/'docs/runbooks').glob('*.md')):
                text=p.read_text();score=len(terms & set(re.findall(r'\w+',text.lower())))
                if score:scored.append((score,p.name,text))
            return {'source':'local-lexical-retrieval','results':[{'source':name,'text':text[:5000],'score':score} for score,name,text in sorted(scored,reverse=True)[:3]]}
        if set(args)-{'action','replicas'} or args.get('action') not in ('rollback','restart','scale'):raise ValueError('Action denied')
        if args['action']!='scale' and 'replicas' in args:raise ValueError('Unexpected replica parameter')
        if not self.proposal_enabled:return {'status':'recommendation_only','action':args['action'],'reason':'No trusted local Git checkout. Human must generate/review a proposal locally.'}
        p=build_proposal(self.repo,self.environment,args['action'],args.get('replicas'))
        self.proposals.append(p)
        return {'status':'awaiting_human_approval','proposal':p,'approval_digest':digest(p)}
