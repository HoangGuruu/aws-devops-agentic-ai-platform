# 11 — Review and approve AI-assisted recovery

**Goal:** investigate a real lab fault, review a precise proposal and verify recovery.

**Before you start:** the application is healthy, Git is clean/current, the live agent works and HPA is removed. Keep operator and agent terminals separate.

## Step 1 — Inject a fresh fault

Repeat Lesson 8, Steps 1–5, using a new branch such as `lab/incident-02`:

- Edit only the fault value in `release.yaml` to `http500`.
- Commit only that file.
- Review and **Squash and merge** the PR.
- Pull main locally.
- Wait for Argo and confirm a real HTTP500 response.
- Keep traffic running so Prometheus has recent samples.

Do not reuse the old incident report as proof of a new incident.

## Step 2 — Refresh the reader token if necessary

The token from Lesson 9 lasts about an hour. In the **operator** terminal, if it has expired:

```bash
kubectl -n bookinfo-develop create token incident-agent --duration=1h > reports/agent-token.txt
chmod 600 reports/agent-token.txt
kubectl --kubeconfig=reports/agent.kubeconfig config set-credentials incident-agent --token="$(cat reports/agent-token.txt)"
rm reports/agent-token.txt
```

## Step 3 — Describe the incident

```bash
cp examples/current-incident.json reports/current-incident.json
date -u
nano reports/current-incident.json
```

Enter the actual UTC observation time. Adjust the summary to match what you observed. Do not put secrets in incident text.

Check Git and the isolated commit:

```bash
git status --short
git log -1 --stat -- gitops/overlays/develop/release.yaml
```

The working tree must be clean, including untracked files. The latest release-file change must be an isolated, non-merge commit. The course PR process uses squash merge for that reason.

## Step 4 — Ask the agent to investigate

In **terminal F**:

```bash
source .venv/bin/activate
source reports/agent.env
python -m agent.cli investigate --mode live --incident reports/current-incident.json --enable-proposals --output reports/ai-incident.json
nano reports/ai-incident.json
```

Read the tool trace and report. Compare the conclusion with metrics, logs, the fault flag and the runbook. A model can be wrong or run out of tool calls.

## Step 5 — Locate the proposal

```bash
ls reports/ai-incident.proposal.json
```

The agent creates this file only if it produced a validated proposal. If no file exists, inspect the report before continuing.

For a separate **manual proposal exercise**, an operator can run:

```bash
python -m agent.cli propose --action rollback --environment develop --output reports/manual-proposal.json
```

Label that proposal as operator-generated, not AI-generated. If using it, substitute its path in the following commands.

## Step 6 — Preview the exact recovery change

In **terminal A**, the operator:

```bash
source .venv/bin/activate
source reports/lab.env
python -m agent.recovery reports/ai-incident.proposal.json
```

Read `path`, `before`, `after` and `approval_digest`.

Approve only if the target is the intended productpage release file and the change restores the correct state. In this exercise, rollback restores the file from before the isolated fault commit. It is not a general cluster rollback or arbitrary image rollback.

The proposal expires after 15 minutes. Git HEAD and the working tree must still match the reviewed state.

## Step 7 — Apply the approved proposal locally

Create a recovery branch. Creating a branch does not change the commit SHA:

```bash
git switch -c lab/ai-recovery-02
```

Replace the digest placeholder with the exact value you reviewed:

```bash
python -m agent.recovery reports/ai-incident.proposal.json --approve PASTE_THE_REVIEWED_APPROVAL_DIGEST
```

**Expected:** the executor creates a local recovery commit. It does not automatically merge a GitHub PR.

## Step 8 — Review and publish the recovery PR

```bash
git show --stat HEAD
git show HEAD -- gitops/overlays/develop/release.yaml
git push -u origin lab/ai-recovery-02
```

Open the PR, review it and squash-merge it according to branch protection.

```bash
git switch main
git pull --ff-only origin main
kubectl -n argocd annotate application bookinfo-develop argocd.argoproj.io/refresh=hard --overwrite
```

Wait until the cluster contains the new state. Do not replay the old proposal: the changed HEAD should make it invalid.

## Step 9 — Verify using the reader identity

Restart terminal B's application port-forward if its Pod changed. In terminal F:

```bash
python -m agent.cli verify --environment develop --url http://127.0.0.1:9080/productpage --output reports/recovery-verification.json
nano reports/recovery-verification.json
```

**Expected:** `recovery_verified: true`. The check requires HTTP200, fault off, available replicas and Argo Synced/Healthy.

If the command exits with an error, inspect the failed condition. Do not edit the report to mark it successful.

## Step 10 — Confirm the alert clears

Continue traffic for several minutes and inspect the error-rate window and alert state. A point-in-time check does not prove sustained stability.

```bash
cp docs/templates/incident-report.md reports/ai-postmortem.md
nano reports/ai-postmortem.md
```

Record the investigation, proposal, human approval, PR/commit and verification. Token usage is not a dollar amount; use the actual selected model's pricing if reporting cost.

## If a proposal is rejected

| Reason | Next step |
|---|---|
| Dirty working tree | Finish or safely set aside unrelated changes |
| Stale HEAD | Update the checkout, inspect current evidence and make a fresh proposal |
| Expired proposal | Investigate again; do not edit timestamps |
| Mixed or merge commit | Inspect the history; this exercise requires an isolated release-file commit |
| Wrong digest | Preview the intended proposal and copy its digest after review |
| No change required | Verify whether recovery already happened |

Restart and scale are separate exercises. Scaling is limited to 1–4 replicas and must not compete with HPA. Scaling does not fix an intentional HTTP500 fault flag.

**Checkpoint:** a human reviewed the change, GitOps applied it and recovery was verified with live evidence.

Next: [Portfolio and cleanup](12-portfolio-cleanup.md).
