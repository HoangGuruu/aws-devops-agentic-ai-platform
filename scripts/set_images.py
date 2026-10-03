#!/usr/bin/env python3
"""Update all four immutable image refs after CI build/scan succeeds."""
import argparse,re
from pathlib import Path
import yaml
p=argparse.ArgumentParser();p.add_argument('--environment',choices=['develop','uat','staging','prod'],required=True);p.add_argument('--registry',required=True);p.add_argument('--prefix',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
if not re.fullmatch(r'[a-zA-Z0-9.-]+',a.registry):p.error('Invalid registry')
if not re.fullmatch(r'[a-z0-9/-]+',a.prefix):p.error('Invalid prefix')
if not re.fullmatch(r'[0-9a-f]{40}',a.tag):p.error('Tag must be full source commit SHA')
file=Path(f'gitops/overlays/{a.environment}/kustomization.yaml');doc=yaml.safe_load(file.read_text())
for image in doc['images']:
 service=image['name'].split('/')[-1]
 image['newName']=f'{a.registry}/{a.prefix}/{service}';image['newTag']=a.tag
file.write_text(yaml.safe_dump(doc,sort_keys=False))
