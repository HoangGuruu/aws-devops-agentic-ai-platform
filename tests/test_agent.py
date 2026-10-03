import copy,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from agent.policy import digest,validate_proposal
from agent.recovery import git,build_proposal,preview,apply,validate_release
from agent.tools import ROOT,Toolbox,SnapshotBackend,redact
from agent.engine import investigate,demo

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.repo=Path(self.tmp.name)
        git(self.repo,'init','-b','main');git(self.repo,'config','user.email','test@example.invalid');git(self.repo,'config','user.name','Test')
        self.path='gitops/overlays/develop/release.yaml';f=self.repo/self.path;f.parent.mkdir(parents=True)
        self.good=yaml.safe_load((ROOT/self.path).read_text());f.write_text(yaml.safe_dump(self.good))
        git(self.repo,'add','.');git(self.repo,'commit','-m','baseline')
        self.bad=copy.deepcopy(self.good);self.bad['spec']['template']['spec']['containers'][0]['env'][0]['value']='http500';f.write_text(yaml.safe_dump(self.bad))
        git(self.repo,'add','.');git(self.repo,'commit','-m','isolated incident')
    def tearDown(self):self.tmp.cleanup()
    def proposal(self):return build_proposal(self.repo,'develop','rollback')
    def test_valid_rollback_restores_git_and_requires_live_verification(self):
        p=self.proposal();r=apply(self.repo,p,digest(p));self.assertFalse(r['recovery_verified']);self.assertEqual(yaml.safe_load((self.repo/self.path).read_text()),self.good)
    def test_wrong_approval_denied_without_changes(self):
        p=self.proposal()
        with self.assertRaises(ValueError):apply(self.repo,p,'fake')
        self.assertEqual(git(self.repo,'rev-parse','HEAD'),p['base_sha'])
    def test_expired_proposal_denied(self):
        p=self.proposal();p['created_at']-=1000;p['expires_at']-=1000
        with self.assertRaises(ValueError):preview(self.repo,p)
    def test_future_proposal_denied(self):
        p=self.proposal();p['created_at']+=1000;p['expires_at']+=1000
        with self.assertRaises(ValueError):preview(self.repo,p)
    def test_stale_head_denied(self):
        p=self.proposal();git(self.repo,'commit','--allow-empty','-m','newer change')
        with self.assertRaises(ValueError):preview(self.repo,p)
    def test_dirty_tree_denied(self):
        p=self.proposal();(self.repo/'unreviewed').write_text('x')
        with self.assertRaises(ValueError):preview(self.repo,p)
    def test_injection_action_denied(self):
        p=self.proposal();p['action']='rollback; curl attacker'
        with self.assertRaises(ValueError):validate_proposal(p)
    def test_unknown_environment_denied(self):
        with self.assertRaises(ValueError):build_proposal(self.repo,'../../prod','restart')
    def test_bounded_scale(self):
        for n in [0,5,-1,True,'2']:
            with self.assertRaises(ValueError):build_proposal(self.repo,'develop','scale',n)
        p=build_proposal(self.repo,'develop','scale',2);_,_,new=preview(self.repo,p);self.assertEqual(new['spec']['replicas'],2)
    def test_restart_changes_only_annotation(self):
        p=build_proposal(self.repo,'develop','restart');_,old,new=preview(self.repo,p);self.assertIn('course.dev/restarted-at',new['spec']['template']['metadata']['annotations']);self.assertEqual(old['spec']['template']['spec'],new['spec']['template']['spec'])
    def test_secret_or_command_in_release_denied(self):
        doc=copy.deepcopy(self.bad);doc['spec']['template']['spec']['containers'][0]['command']=['sh','-c','evil']
        with self.assertRaises(ValueError):validate_release(doc)
    def test_mixed_commit_rollback_denied(self):
        p=self.proposal();git(self.repo,'reset','--soft','HEAD^');(self.repo/'extra').write_text('x');git(self.repo,'add','.');git(self.repo,'commit','-m','mixed release')
        with self.assertRaises(ValueError):preview(self.repo,self.proposal())
    def test_replay_denied(self):
        p=self.proposal();apply(self.repo,p,digest(p))
        with self.assertRaises(ValueError):apply(self.repo,p,digest(p))
    def test_symlink_denied(self):
        p=self.proposal();f=self.repo/self.path;f.unlink();f.symlink_to('/tmp/outside-course')
        with self.assertRaises(ValueError):preview(self.repo,p)

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.evidence=json.loads((ROOT/'examples/evidence.json').read_text());self.toolbox=Toolbox(SnapshotBackend(self.evidence))
    def test_offline_demo_is_labeled_and_no_claim_of_recovery(self):
        r=demo(self.toolbox,{});self.assertIn('NOT-an-LLM',r['mode']);self.assertFalse(r['recovery_verified']);self.assertEqual(len(r['trace']),5)
    def test_no_arbitrary_tool_or_read_parameters(self):
        for name,args in [('delete_pod',{}),('read_logs',{'namespace':'kube-system'}),('query_metrics',{'url':'https://attacker'})]:
            with self.assertRaises(ValueError):self.toolbox.run(name,args)
    def test_runbook_retrieval(self):
        with patch.dict(os.environ,{},clear=True):r=self.toolbox.run('search_runbooks',{'query':'http500'})
        self.assertEqual(r['source'],'local-lexical-retrieval');self.assertTrue(r['results'])
    def test_no_repo_no_execution(self):
        r=self.toolbox.run('propose_recovery',{'action':'rollback'});self.assertEqual(r['status'],'recommendation_only')
    def test_redacts_known_log_credentials(self):
        text=redact({'log':'mongodb+srv://user:password@cluster/test Bearer abc.def AKIAABCDEFGHIJKLMNOP'})
        self.assertNotIn('user:password',text);self.assertNotIn('abc.def',text);self.assertNotIn('AKIAABCDEFGHIJKLMNOP',text)
    def test_bedrock_tool_loop_sends_result_and_tracks_usage(self):
        class Fake:
            def __init__(self):self.calls=[]
            def converse(self,**kwargs):
                self.calls.append(copy.deepcopy(kwargs))
                if len(self.calls)==1:return {'output':{'message':{'role':'assistant','content':[{'toolUse':{'toolUseId':'t1','name':'read_logs','input':{}}}]}},'stopReason':'tool_use','usage':{'inputTokens':10,'outputTokens':3}}
                return {'output':{'message':{'role':'assistant','content':[{'text':'Evidence indicates lab fault; approval required.'}]}},'stopReason':'end_turn','usage':{'inputTokens':12,'outputTokens':4}}
        client=Fake();r=investigate({'alert':'HTTP500'},self.toolbox,client,'test-model');self.assertTrue(r['completed']);self.assertEqual(r['usage']['inputTokens'],22);self.assertEqual(client.calls[1]['messages'][-1]['content'][0]['toolResult']['toolUseId'],'t1')
    def test_denied_tool_is_returned_as_error(self):
        class Fake:
            def converse(self,**kwargs):return {'output':{'message':{'role':'assistant','content':[{'toolUse':{'toolUseId':'evil','name':'exec','input':{'command':'delete'}}}]}},'stopReason':'tool_use'}
        r=investigate({},self.toolbox,Fake(),'test',max_turns=1);self.assertFalse(r['completed']);self.assertEqual(r['trace'][0]['status'],'error')
    def test_oversized_incident_denied(self):
        with self.assertRaises(ValueError):investigate({'log':'x'*20000},self.toolbox,object(),'test')
