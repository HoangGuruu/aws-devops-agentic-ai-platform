#!/usr/bin/env python3
"""Offline structural checks; not a substitute for AWS plan, image builds or a cluster apply."""
from pathlib import Path
import ast,json,sys,yaml
ROOT=Path(__file__).resolve().parents[1]
errors=[];count=0
for p in ROOT.rglob('*'):
    if any(x in p.parts for x in ['legacy','.git','.terraform','.venv','__pycache__','node_modules']):continue
    try:
        if p.suffix in ('.yaml','.yml'):list(yaml.safe_load_all(p.read_text()));count+=1
        elif p.suffix=='.json':
            if p.name=='ratings_data.json':
                for line in p.read_text().splitlines():
                    if line.strip():json.loads(line)
            else:json.loads(p.read_text())
            count+=1
        elif p.suffix=='.py':ast.parse(p.read_text());count+=1
    except Exception as e:errors.append(f'{p.relative_to(ROOT)}: {e}')
for d in yaml.safe_load_all((ROOT/'gitops/base/bookinfo.yaml').read_text()):
    if d and d['kind']=='Deployment':
        for c in d['spec']['template']['spec']['containers']:
            for required in ['resources','readinessProbe','livenessProbe','startupProbe','securityContext']:
                if required not in c:errors.append(f"{d['metadata']['name']}: missing {required}")
for p in (ROOT/'.github/workflows').glob('*.yaml'):
    text=p.read_text()
    if 'AWS_ACCESS_KEY_ID' in text or 'KUBECONFIG' in text:errors.append(f'{p.name}: static cloud/cluster credentials prohibited')
if errors:print('\n'.join(errors));sys.exit(1)
print(f'PASS: parsed {count} files; workload probes/resources/security contexts and CI credential checks passed.')
