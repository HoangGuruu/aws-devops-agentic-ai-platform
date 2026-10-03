#!/usr/bin/env python3
"""Export bounded read-only evidence for the AgentCore snapshot runtime."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.tools import LiveBackend,Toolbox
p=argparse.ArgumentParser();p.add_argument('--environment',default='develop');p.add_argument('--incident',default='examples/incident.json');p.add_argument('--output',default='reports/agentcore-payload.json');a=p.parse_args()
tools=Toolbox(LiveBackend(a.environment),a.environment)
data={'incident':json.loads(Path(a.incident).read_text()),'evidence':{name:tools.run(name,{}) for name in ['inspect_kubernetes','read_logs','query_metrics','inspect_gitops']}}
dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(data,indent=2))
print('Inspect/redact the snapshot before sending it to Bedrock:',dest)
