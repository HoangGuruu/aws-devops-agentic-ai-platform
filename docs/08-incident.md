# 8 — Investigate and recover an incident

**Goal:** connect an application failure to a Git change and restore the application.

**Before you start:** Argo is Synced/Healthy, Prometheus has data, HPA is removed and the app returns 200. Use only the isolated course lab.

## Step 1 — Check the baseline

In terminal A:

```bash
source reports/lab.env
source .venv/bin/activate
git switch main
git pull --ff-only origin main
git status --short
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
```

**Expected:** Git is clean and HTTP is `200`. Finish earlier changes before creating the fault. Keep application and Prometheus port-forwards running.

## Step 2 — Create an incident branch

```bash
git switch -c lab/incident-01
nano gitops/overlays/develop/release.yaml
```

Change the existing fault value from `off` to `http500`:

```yaml
        - name: LAB_FAULT_MODE
          value: http500
```

Keep the surrounding manifest unchanged.

## Step 3 — Commit only the fault file

```bash
git diff -- gitops/overlays/develop/release.yaml
git add gitops/overlays/develop/release.yaml
git commit -m "Trigger the productpage HTTP500 lab incident"
git push -u origin lab/incident-01
```

Open a GitHub PR. Confirm it changes **only** `release.yaml`, then **Squash and merge**. This creates the isolated commit needed by the later rollback exercise.

```bash
git switch main
git pull --ff-only origin main
git log -1 --stat -- gitops/overlays/develop/release.yaml
```

## Step 4 — Wait for the faulty release

```bash
kubectl -n argocd annotate application bookinfo-develop argocd.argoproj.io/refresh=hard --overwrite
kubectl -n bookinfo-develop get deployment productpage-v1 -o yaml
```

Find `LAB_FAULT_MODE` in the deployment. Wait until its value is `http500`. Restart terminal B's port-forward if the deployment replaced its Pod.

## Step 5 — Generate traffic

In terminal E:

```bash
source .venv/bin/activate
python scripts/load_test.py --seconds 240
```

In terminal A:

```bash
date -u
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/health
```

**Expected:** productpage returns 500; health returns 200. Record the time you observed the failure.

## Step 6 — Investigate Pods, logs and metrics

```bash
kubectl -n bookinfo-develop get pods
kubectl -n bookinfo-develop logs deployment/productpage-v1 -c productpage --tail=60
kubectl -n argocd get application bookinfo-develop
```

Pods may be Ready and Argo may be Healthy while customers see failures.

In Prometheus, run:

```promql
sum(rate(bookinfo_http_responses_total{namespace="bookinfo-develop",path="/productpage",status=~"5.."}[2m])) / clamp_min(sum(rate(bookinfo_http_responses_total{namespace="bookinfo-develop",path="/productpage"}[2m])), 0.001)
```

Check the alert moves from Pending to Firing after sufficient traffic and the configured duration.

## Step 7 — Inspect the latest change

```bash
git log -5 --oneline
git log -1 -p -- gitops/overlays/develop/release.yaml
```

Compare the change with the error log and metrics. The fault flag changed just before the error rate increased. Do not assume every HTTP500 means insufficient CPU.

## Step 8 — Create the recovery change

```bash
git switch -c lab/manual-recovery-01
nano gitops/overlays/develop/release.yaml
```

Change only the value back to `'off'`. Keep the quotes around `off` to avoid YAML boolean ambiguity:

```yaml
        - name: LAB_FAULT_MODE
          value: 'off'
```

```bash
git diff -- gitops/overlays/develop/release.yaml
git add gitops/overlays/develop/release.yaml
git commit -m "Recover productpage by disabling the lab fault"
git push -u origin lab/manual-recovery-01
```

Review and squash-merge the recovery PR. Then pull main:

```bash
git switch main
git pull --ff-only origin main
kubectl -n argocd annotate application bookinfo-develop argocd.argoproj.io/refresh=hard --overwrite
```

## Step 9 — Verify recovery

Wait for Argo to sync the new commit. Check the flag in the live deployment:

```bash
kubectl -n bookinfo-develop get deployment productpage-v1 -o yaml
kubectl -n argocd get application bookinfo-develop
```

Restart the application port-forward if necessary, then:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
python scripts/load_test.py --seconds 240
```

**Expected:** flag off, HTTP200, available replicas, the correct Git revision in Argo, and the alert resolves after the metrics window clears. A successful Git push alone does not prove recovery.

## Step 10 — Write the incident report

```bash
cp docs/templates/incident-report.md reports/manual-incident.md
nano reports/manual-incident.md
```

Record the actual impact, timestamps, fault commit, evidence, recovery commit and verification. Do not invent timing measurements.

Use new branch names if repeating the exercise.

**Checkpoint:** the app is healthy again and your report explains why it failed and how you verified the fix.

Next: [Run the AI investigator](09-ai-agent.md).
