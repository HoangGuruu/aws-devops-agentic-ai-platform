"""Optional AgentCore read-only snapshot investigator (no cluster/Git write credentials)."""
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent.engine import investigate
from agent.tools import Toolbox,SnapshotBackend
app=BedrockAgentCoreApp()
@app.entrypoint
def invoke(payload):
    if not isinstance(payload,dict) or len(json.dumps(payload))>100000:raise ValueError('Payload must be an object <=100 KB')
    incident=payload.get('incident');evidence=payload.get('evidence')
    if not isinstance(incident,dict) or not isinstance(evidence,dict):raise ValueError('incident and evidence objects required')
    result=investigate(incident,Toolbox(SnapshotBackend(evidence),proposal_enabled=False))
    result['mode']='agentcore-bedrock-with-supplied-snapshot'
    result['evidence_source']='caller-supplied snapshot; no direct live cluster access'
    return result
if __name__=='__main__':app.run()
