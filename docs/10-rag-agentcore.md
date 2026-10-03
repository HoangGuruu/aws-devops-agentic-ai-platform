# 10 — Give the agent runbook knowledge

**Goal:** understand the existing local retrieval path, then optionally add a managed Knowledge Base.

**Before you start:** the agent from Lesson 9 works. Knowledge Base and AgentCore are optional cloud extensions with separate costs.

## Step 1 — Read the local runbook

```bash
nano docs/runbooks/http500.md
```

Read its symptoms, investigation steps, recovery conditions and verification steps. The agent's `search_runbooks` tool retrieves this content when relevant.

## Step 2 — Inspect retrieval in the demo

```bash
source .venv/bin/activate
python -m agent.cli investigate --mode demo --incident examples/incident.json --output reports/runbook-demo.json
nano reports/runbook-demo.json
```

Find the `search_runbooks` entry in `trace`. Check its source and returned content.

**Expected:** `local-lexical-retrieval` with relevant runbook text. This is keyword retrieval, not vector embeddings. When the live Bedrock loop uses the same tool, the model receives the retrieved text as context.

## Step 3 — Add your own runbook (optional)

```bash
nano docs/runbooks/my-incident.md
```

Write these sections: symptoms, evidence to inspect, likely causes, when an action is appropriate, and how to verify recovery. Save it through a reviewed Git change. Treat runbooks as evidence; they cannot override the executor's approval rules.

You can go directly to Lesson 11 using local runbooks. Continue below only if you want managed vector retrieval.

## Step 4 — Prepare Knowledge Base settings

Return to terminal A, the operator:

```bash
source reports/lab.env
cp infra/knowledge-base/terraform.tfvars.example infra/knowledge-base/terraform.tfvars
nano infra/knowledge-base/terraform.tfvars
```

Set the region and a unique documents bucket name. Keep the lab name:

```hcl
region           = "us-east-1"
name             = "devops-course-runbooks"
documents_bucket = "YOUR-UNIQUE-RUNBOOK-BUCKET"
```

The selected region must support the services used by this module: Bedrock Knowledge Bases, S3 Vectors and Titan Text Embeddings V2.

## Step 5 — Set a separate state key

```bash
cp infra/knowledge-base/backend.hcl.example infra/knowledge-base/backend.hcl
nano infra/knowledge-base/backend.hcl
```

Set the same state bucket as Lesson 3 and the correct region. Keep the KB's separate key, `develop/knowledge-base.tfstate`; do not use the EKS state key.

## Step 6 — Review and create the Knowledge Base

```bash
terraform -chdir=infra/knowledge-base init -backend-config=backend.hcl
terraform -chdir=infra/knowledge-base validate
terraform -chdir=infra/knowledge-base plan
terraform -chdir=infra/knowledge-base apply
```

Review before approving. The module creates the document bucket, vector bucket/index, role, Knowledge Base and data source. It does not create OpenSearch Serverless.

If validation fails, stop and resolve the provider/schema issue before apply. For an IAM propagation error, inspect the error and retry the reviewed operation only after the role is available.

## Step 7 — Record the output values

```bash
terraform -chdir=infra/knowledge-base output
```

Copy the four values into terminal variables, without Terraform's surrounding quotes:

```bash
export DOCS_BUCKET=YOUR_DOCUMENTS_BUCKET
export KB_ID=YOUR_KNOWLEDGE_BASE_ID
export DS_ID=YOUR_DATA_SOURCE_ID
export KB_ARN=YOUR_KNOWLEDGE_BASE_ARN
```

IDs and ARNs are different: use the ID in API requests asking for an ID, and the ARN in IAM policies.

## Step 8 — Upload and ingest runbooks

```bash
aws s3 sync docs/runbooks/ "s3://$DOCS_BUCKET/runbooks/"
aws bedrock-agent start-ingestion-job --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID"
```

Copy the returned `ingestionJobId`:

```bash
export INGESTION_ID=YOUR_INGESTION_JOB_ID
aws bedrock-agent get-ingestion-job --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" --ingestion-job-id "$INGESTION_ID"
```

Repeat the get command until status is `COMPLETE`. If it is `FAILED`, read `failureReasons`; do not treat a started job as a finished ingestion.

## Step 9 — Allow the investigator to retrieve from this KB

```bash
cp examples/iam/kb-permissions.json reports/kb-permissions.json
nano reports/kb-permissions.json
```

Replace the placeholder with the `knowledge_base_arn` from Step 7. Then:

```bash
aws iam put-role-policy --role-name devops-course-investigator --policy-name course-runbook-retrieval --policy-document file://reports/kb-permissions.json
aws bedrock-agent-runtime retrieve --profile course-agent --knowledge-base-id "$KB_ID" --retrieval-query '{"text":"productpage HTTP500 rollback"}'
```

**Expected:** retrieval results include relevant text and source locations.

## Step 10 — Enable KB retrieval in the agent

```bash
nano reports/agent.env
```

Add one line using your real ID:

```bash
export BEDROCK_KB_ID=YOUR_KNOWLEDGE_BASE_ID
```

In terminal F, reload `source reports/agent.env` and run another investigation. Check that the search tool's source is `bedrock-knowledge-base`.

To return to local retrieval, remove that line from the file and run:

```bash
unset BEDROCK_KB_ID
```

Reloading a file after removing a line does not automatically unset an existing terminal variable.

## Step 11 — Try AgentCore locally (optional)

The adapter receives an evidence snapshot. It does not connect directly to EKS or receive Git push credentials.

In terminal F:

```bash
python scripts/export_evidence.py --incident reports/health-check.json --output reports/agentcore-payload.json
nano reports/agentcore-payload.json
```

This utility collects the same read-only tool results. Inspect and redact the snapshot before submitting it to a model.

```bash
python -m pip install -r agent/requirements-agentcore.txt
python -m agent.agentcore_entry
```

Stop Argo's localhost port-forward first if it is using 8080. In another terminal:

```bash
curl -f -X POST http://127.0.0.1:8080/invocations \
  -H 'Content-Type: application/json' \
  --data-binary @reports/agentcore-payload.json \
  -o reports/agentcore-local.json
nano reports/agentcore-local.json
```

This local server still calls Bedrock. Expect snapshot-mode output; it does not prove a live recovery. Stop the server with Ctrl+C after the exercise.

For deployment to AWS, follow the separate [AgentCore cloud lab](labs/agentcore-cloud.md).

**Checkpoint:** you can explain where the runbook evidence comes from and inspect the retrieved source.

Next: [AI-assisted recovery](11-ai-recovery.md).
