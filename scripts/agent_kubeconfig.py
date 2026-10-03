#!/usr/bin/env python3
"""Create a short-lived read-only kubeconfig using the current operator context."""
import argparse,json,os,subprocess
from pathlib import Path
import yaml
p=argparse.ArgumentParser();p.add_argument('--output',default='reports/agent.kubeconfig');p.add_argument('--environment',choices=['develop','uat','staging','prod'],default='develop');a=p.parse_args()
def run(*args):return subprocess.run(['kubectl',*args],check=True,text=True,capture_output=True,timeout=30).stdout.strip()
source=json.loads(run('config','view','--raw','--minify','--flatten','-o','json'))
token=run('-n',f'bookinfo-{a.environment}','create','token','incident-agent','--duration=1h')
cluster=source['clusters'][0]
config={'apiVersion':'v1','kind':'Config','clusters':[cluster],'users':[{'name':'incident-agent','user':{'token':token}}],'contexts':[{'name':'incident-agent','context':{'cluster':cluster['name'],'user':'incident-agent','namespace':f'bookinfo-{a.environment}'}}],'current-context':'incident-agent'}
dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as f:yaml.safe_dump(config,f,sort_keys=False)
os.chmod(dest,0o600);print(f'Wrote short-lived reader config to {dest}; token not printed.')
