# 7 — Monitor and scale the application

**Goal:** see application metrics, configure alerts and understand Pod versus node scaling.

**Before you start:** Bookinfo and Argo CD are working. Use the operator terminal.

## Step 1 — Install Metrics Server

```bash
source reports/lab.env
source platform/versions.env
kubectl apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/$METRICS_SERVER_VERSION/components.yaml"
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
kubectl top nodes
```

**Expected:** CPU and memory usage appear. Metrics Server supplies resource metrics for HPA. Prometheus, installed next, stores the metrics used by dashboards and alerts.

## Step 2 — Install Prometheus and Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version "$KUBE_PROMETHEUS_CHART_VERSION" \
  -n monitoring --create-namespace \
  -f platform/monitoring/values.yaml \
  --wait --timeout 10m
kubectl apply -f platform/monitoring/bookinfo.yaml
kubectl -n monitoring get pods
```

The last manifest adds a ServiceMonitor for productpage and the incident alert rules.

## Step 3 — Open Prometheus

In **terminal C**:

```bash
source reports/lab.env
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Open `http://127.0.0.1:9090`. Leave the port-forward running.

## Step 4 — Open Grafana

In **terminal D**, stop the Argo port-forward if you are reusing that terminal:

```bash
source reports/lab.env
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
```

In terminal A, read the password privately:

```bash
kubectl -n monitoring get secret monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 --decode
```

Open `http://127.0.0.1:3000`, log in as `admin`, then go to Dashboards → New/Import → Upload JSON. Select `platform/monitoring/dashboard.json`. Use the provisioned Prometheus data source.

## Step 5 — Generate requests and check scraping

Keep terminal B's application port-forward running. In terminal A:

```bash
source .venv/bin/activate
python scripts/load_test.py --seconds 60
```

This course utility sends a bounded stream of HTTP requests. It does not modify the cluster.

In Prometheus, open Targets and find the productpage target. It should be UP. Paste this query into the query box:

```promql
sum(rate(bookinfo_http_responses_total{namespace="bookinfo-develop",path="/productpage"}[2m]))
```

**Expected:** a positive request rate after enough samples. An empty result is not proof that the application is healthy; check the target and ServiceMonitor.

## Step 6 — Inspect the alert

```bash
nano platform/monitoring/bookinfo.yaml
```

Find `BookinfoHighErrorRate`. It checks whether HTTP 5xx responses exceed 20% of productpage traffic using a two-minute rate window, for at least one minute. Lesson 8 triggers this rule.

You can also open Alertmanager in another terminal:

```bash
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-alertmanager 9093:9093
```

Open `http://127.0.0.1:9093`.

## Step 7 — Add Slack notifications (optional)

In your Slack workspace, create an app, enable Incoming Webhooks and add a webhook for your chosen course channel. Notifications will be sent to that channel when the rule fires.

Read the webhook with hidden input. Paste the URL at the prompt and press Enter:

```bash
read -r -s -p 'Slack webhook URL: ' SLACK_WEBHOOK
```

Create the Secret, then remove the temporary shell variable:

```bash
kubectl -n monitoring create secret generic slack-webhook --from-literal=url="$SLACK_WEBHOOK"
unset SLACK_WEBHOOK
```

If the Secret already exists, update it through your normal secret-management process rather than creating another one. Keep the webhook private.

```bash
nano platform/monitoring/slack.yaml
```

Set `channel` to your selected channel, then apply:

```bash
kubectl apply -f platform/monitoring/slack.yaml
```

Without Slack, use the Prometheus Alerts page and Alertmanager to observe the exercise.

## Step 8 — Let HPA manage replicas

Argo normally restores the replica count from Git. HPA needs to manage that field without Argo resetting it.

```bash
nano platform/argocd/develop.yaml
```

Under `spec`, add `ignoreDifferences`. Under the existing `spec.syncPolicy.syncOptions`, add `RespectIgnoreDifferences=true`. Keep the rest of the file. The relevant section should look like this:

```yaml
  ignoreDifferences:
    - group: apps
      kind: Deployment
      name: productpage-v1
      namespace: bookinfo-develop
      jsonPointers:
        - /spec/replicas
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - RespectIgnoreDifferences=true
```

Do not create a second `syncPolicy` key. Apply the updated Application and create HPA:

```bash
kubectl apply -f platform/argocd/develop.yaml
kubectl apply -f platform/monitoring/hpa.yaml
kubectl -n bookinfo-develop get hpa
kubectl -n bookinfo-develop top pods
```

## Step 9 — Observe HPA

In **terminal E**:

```bash
source .venv/bin/activate
python scripts/load_test.py --seconds 240
```

In terminal A:

```bash
kubectl -n bookinfo-develop get hpa -w
```

Press Ctrl+C when finished observing. The small traffic generator may not create enough CPU load to increase replicas. Compare current CPU utilization against the HPA target; do not expect a fixed replica count. If needed, run the same bounded load command in a second traffic terminal. HPA also waits before scaling down.

## Step 10 — Increase worker-node capacity

HPA adds Pods; it does not add EC2 nodes. To try a manual capacity change:

```bash
nano infra/environments/develop.tfvars
```

Change:

```hcl
node_desired_size = 3
```

Review and apply:

```bash
terraform -chdir=infra/main plan -var-file=../environments/develop.tfvars
terraform -chdir=infra/main apply -var-file=../environments/develop.tfvars
kubectl get nodes
```

**Expected:** a third node joins. This is manual infrastructure scaling, not a node autoscaler. To return to two nodes, set the value back to `2`, review the plan and apply again.

## Step 11 — Return replica ownership to Git

Before the recovery lessons:

```bash
kubectl -n bookinfo-develop delete hpa productpage
nano platform/argocd/develop.yaml
```

Remove the `ignoreDifferences` block added in Step 8 and remove `RespectIgnoreDifferences=true`. Keep `CreateNamespace=true` and the existing automated sync settings.

```bash
kubectl apply -f platform/argocd/develop.yaml
kubectl -n bookinfo-develop get deployment productpage-v1
```

If the file now exactly matches the original, no commit is needed. If you made other intended configuration changes, save them through the PR procedure in Lesson 6 before continuing.

**Checkpoint:** metrics are visible, the alert rule exists, and HPA is removed before the incident exercise.

Next: [Investigate an incident](08-incident.md). Database and Vault are separate optional labs.
