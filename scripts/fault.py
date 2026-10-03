#!/usr/bin/env python3
"""Change ONLY the development lab fault flag. Commit this file change separately."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import yaml
from agent.recovery import validate_release
p=argparse.ArgumentParser();p.add_argument('state',choices=['on','off']);p.add_argument('--environment',choices=['develop'],default='develop');a=p.parse_args()
file=Path(f'gitops/overlays/{a.environment}/release.yaml');doc=validate_release(yaml.safe_load(file.read_text()))
doc['spec']['template']['spec']['containers'][0]['env'][0]['value']='http500' if a.state=='on' else 'off'
file.write_text(yaml.safe_dump(doc,sort_keys=False));print(f'Changed {file}. Review, then commit this file alone and push to your lab branch.')
