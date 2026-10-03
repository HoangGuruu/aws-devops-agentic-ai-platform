#!/usr/bin/env python3
"""Replace distributable account/repository placeholders. Writes files only; no AWS calls."""
import argparse,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--account',required=True);p.add_argument('--repo',required=True);p.add_argument('--region',default='us-east-1');p.add_argument('--domain',default='example.com');p.add_argument('--email',default='admin@example.com');a=p.parse_args()
if not re.fullmatch(r'\d{12}',a.account):p.error('account must be 12 digits')
if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):p.error('repo must be OWNER/REPO')
if not re.fullmatch(r'[a-z]{2}-[a-z]+-\d',a.region):p.error('invalid region')
if not re.fullmatch(r'[A-Za-z0-9.-]+',a.domain) or not re.fullmatch(r'[A-Za-z0-9._+@-]+',a.email):p.error('invalid domain/email')
root=Path(__file__).resolve().parents[1];count=0
for folder in ['infra/environments','infra/knowledge-base','platform/argocd','platform/networking','gitops/overlays']:
 for f in (root/folder).rglob('*'):
  if f.is_file() and (f.suffix in ['.yaml','.example']):
   text=f.read_text();new=text.replace('111122223333',a.account).replace('REPLACE_OWNER/REPLACE_REPO',a.repo).replace('admin@example.com',a.email).replace('example.com',a.domain).replace('us-east-1',a.region)
   if new!=text:f.write_text(new);count+=1
print(f'Updated {count} files. Still set your operator ARN, CIDR, state bucket and image commit SHA; review git diff.')
