# 9 — Run the AI investigator

**Goal:** run the agent first with fixtures, then with Bedrock and read-only cluster access.

The Python commands in this lesson start the actual course agent. Configuration is edited directly in files; you do not need Python scripts to generate it.

## Step 1 — Run the offline demo

```bash
source .venv/bin/activate
python -m agent.cli investigate --mode demo --incident examples/incident.json --output reports/demo.json
nano reports/demo.json
```

**Expected:** mode `offline-fixture-NOT-an-LLM`, with zero model tokens. This is a fixture exercise; it neither calls a model nor reads your cluster.

## Step 2 — Install the agent dependencies

```bash
python -m pip install -r agent/requirements.txt
```

The agent uses the AWS SDK to call Bedrock and the Kubernetes client to inspect the cluster.

## Step 3 — Choose a Bedrock model

Use the operator terminal:

```bash
source reports/lab.env
aws bedrock list-foundation-models --by-provider Amazon --output table
aws bedrock list-inference-profiles --output table
```

Open Bedrock Console in the same region. Choose a model that supports **Converse tool use**, check its access requirements and pricing, and test access in the playground if needed. Use a profile ID when the selected model requires inference through a profile.

Write down the ID and allowed ARN or ARNs. To inspect a foundation model, replace the placeholder:

```bash
aws bedrock get-foundation-model --model-identifier YOUR_MODEL_ID
```

For an inference profile, use this command instead:

```bash
aws bedrock get-inference-profile --inference-profile-identifier YOUR_PROFILE_ID
```

A profile policy needs its `inferenceProfileArn` and the underlying `modelArn` values returned by the command. Check cross-region destinations against your account's rules.

## Step 4 — Prepare the role trust file

```bash
cp examples/iam/investigator-trust.json reports/investigator-trust.json
nano reports/investigator-trust.json
```

Replace `YOUR_OPERATOR_IAM_ROLE_ARN` with the full IAM ARN used in Lesson 3. This identifies who can assume the investigator role. Do not use an STS session ARN.

## Step 5 — Prepare model permissions

```bash
cp examples/iam/model-permissions.json reports/model-permissions.json
nano reports/model-permissions.json
```

Replace the Resource placeholder with the exact model ARN. If using a profile, the array should contain the profile ARN and each underlying model ARN:

```json
"Resource": [
  "YOUR_INFERENCE_PROFILE_ARN",
  "YOUR_FIRST_FOUNDATION_MODEL_ARN",
  "YOUR_SECOND_FOUNDATION_MODEL_ARN"
]
```

The number of model entries depends on the profile. Remove entries you do not need. Keep valid JSON: no comments or trailing commas. Do not replace the resources with `*` to work around a denied request.

## Step 6 — Create the investigator role

Run as the operator:

```bash
aws iam create-role --role-name devops-course-investigator --assume-role-policy-document file://reports/investigator-trust.json
aws iam put-role-policy --role-name devops-course-investigator --policy-name course-model-inference --policy-document file://reports/model-permissions.json
```

If that role already exists, inspect it before reusing it. Do not overwrite an unrelated role.

Create an AWS CLI profile for it:

```bash
aws configure set role_arn "arn:aws:iam::$ACCOUNT_ID:role/devops-course-investigator" --profile course-agent
aws configure set source_profile course-lab --profile course-agent
aws configure set region "$AWS_REGION" --profile course-agent
aws sts get-caller-identity --profile course-agent
```

**Expected:** the ARN contains `assumed-role/devops-course-investigator/`.

For an EC2 instance role, use `credential_source Ec2InstanceMetadata` instead of `source_profile course-lab`. Do not set both. If role assumption is denied, check trust, the operator's AssumeRole permissions and organization policy with your administrator.

## Step 7 — Apply Kubernetes read-only permissions

Still in the operator terminal:

```bash
kubectl apply -f platform/security/agent-rbac.yaml
```

This grants access to Bookinfo Pods/logs/deployments and the named Argo application. It does not grant Secrets, exec, update or delete access.

## Step 8 — Build a separate reader kubeconfig

Read the cluster endpoint:

```bash
aws eks describe-cluster --name devops-course-develop --query cluster.endpoint --output text
```

Copy that HTTPS endpoint into this setting:

```bash
export EKS_ENDPOINT=PASTE_YOUR_CLUSTER_HTTPS_ENDPOINT
```

Save the cluster CA and request a one-hour reader token:

```bash
aws eks describe-cluster --name devops-course-develop --query cluster.certificateAuthority.data --output text | base64 --decode > reports/cluster-ca.crt
kubectl -n bookinfo-develop create token incident-agent --duration=1h > reports/agent-token.txt
chmod 600 reports/agent-token.txt
```

Create the separate config, one part at a time:

```bash
kubectl --kubeconfig=reports/agent.kubeconfig config set-cluster course --server="$EKS_ENDPOINT" --certificate-authority=reports/cluster-ca.crt --embed-certs=true
```

```bash
kubectl --kubeconfig=reports/agent.kubeconfig config set-credentials incident-agent --token="$(cat reports/agent-token.txt)"
```

```bash
kubectl --kubeconfig=reports/agent.kubeconfig config set-context incident-agent --cluster=course --user=incident-agent --namespace=bookinfo-develop
kubectl --kubeconfig=reports/agent.kubeconfig config use-context incident-agent
chmod 600 reports/agent.kubeconfig
rm reports/agent-token.txt
```

These commands do not replace your normal operator kubeconfig. Never commit the reader config. When the token expires, repeat the token and set-credentials commands using the operator identity.

## Step 9 — Verify the boundary

```bash
kubectl --kubeconfig=reports/agent.kubeconfig auth can-i get pods -n bookinfo-develop
kubectl --kubeconfig=reports/agent.kubeconfig auth can-i get secrets -n bookinfo-develop
kubectl --kubeconfig=reports/agent.kubeconfig auth can-i patch deployments -n bookinfo-develop
```

**Expected:** `yes`, `no`, `no`. The denied checks returning a nonzero exit code are expected.

## Step 10 — Edit the agent settings

```bash
cp examples/agent.env.example reports/agent.env
nano reports/agent.env
```

Set your selected model/profile ID and region. Keep `AWS_PROFILE=course-agent` and the reader kubeconfig path. If your Prometheus port-forward uses the course default, keep its URL unchanged.

## Step 11 — Test Bedrock with a supplied snapshot

Open **terminal F**, from the project root:

```bash
source .venv/bin/activate
source reports/agent.env
python -m agent.cli investigate --mode snapshot --incident examples/incident.json --snapshot examples/evidence.json --output reports/bedrock-snapshot.json
nano reports/bedrock-snapshot.json
```

This calls a real model and incurs inference charges, but its evidence is still a fixture. Resolve model access/IAM errors here before testing live data.

## Step 12 — Investigate the healthy live application

Keep the operator's Prometheus port-forward in terminal C running. The reader identity cannot open that port-forward itself.

```bash
cp examples/health-check.json reports/health-check.json
nano reports/health-check.json
```

Read the request. It asks for the current health and does not assume an incident exists.

```bash
python -m agent.cli investigate --mode live --incident reports/health-check.json --output reports/live-health.json
nano reports/live-health.json
```

Review `completed`, `report`, `trace`, `usage` and `latency_seconds`. A tool error is missing evidence, not a healthy result. The model may need another investigation if it reaches its tool budget.

Keep terminal F separate from operator work. If you accidentally switch an operator terminal to the reader config, run `source reports/lab.env` and `unset KUBECONFIG` before operator commands. Restore your custom operator kubeconfig explicitly if you use one.

**Checkpoint:** demo and model calls work, the agent can read evidence, and it cannot read Secrets or change deployments.

Next: [Runbooks and Knowledge Base](10-rag-agentcore.md).
