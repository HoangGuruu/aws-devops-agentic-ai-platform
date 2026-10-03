# Optional lab — Deploy AgentCore Runtime on AWS

**Goal:** send an evidence snapshot to a deployed runtime and receive an investigation report.

**Before you start:** the local adapter in Lesson 10 works; Docker buildx can build Linux ARM64; your operator can create ECR/IAM/runtime resources and pass the runtime role. Use the same working Bedrock model as Lesson 9.

The runtime receives a snapshot. It does not get cluster credentials or Git push access. This lab uses local runbooks inside the image; it does not require the optional KB.

## Step 1 — Create a dedicated ECR repository

In the operator terminal:

```bash
source reports/lab.env
aws ecr create-repository --repository-name devops-course-agentcore --image-tag-mutability IMMUTABLE
export REGISTRY="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
```

If this lab repository already exists, inspect and reuse it. Do not recreate unrelated resources.

## Step 2 — Set the image tag

```bash
git rev-parse HEAD
```

Copy the source SHA:

```bash
export IMAGE_TAG=YOUR_FULL_SOURCE_COMMIT_SHA
export AGENTCORE_IMAGE="$REGISTRY/devops-course-agentcore:$IMAGE_TAG"
docker buildx inspect --bootstrap
```

The builder's Platforms must include `linux/arm64`. If missing, use an ARM-capable builder or Docker Desktop with suitable emulation before continuing.

## Step 3 — Build and push the ARM64 image

```bash
docker buildx build --platform linux/arm64 -f agent/Dockerfile.agentcore -t "$AGENTCORE_IMAGE" --push .
docker buildx imagetools inspect "$AGENTCORE_IMAGE"
```

**Check:** the image includes the required architecture. Do not upload an amd64-only image and expect an ARM64 runtime to run it.

## Step 4 — Edit the runtime trust policy

```bash
cp examples/iam/agentcore-trust.json reports/agentcore-trust.json
nano reports/agentcore-trust.json
```

Replace both account placeholders. If using another region, replace `us-east-1` too. Keep the service principal `bedrock-agentcore.amazonaws.com`.

## Step 5 — Edit runtime permissions

```bash
cp examples/iam/agentcore-runtime-permissions.json reports/agentcore-runtime-permissions.json
nano reports/agentcore-runtime-permissions.json
```

Replace every account placeholder and the region if needed. The policy grants access to the lab ECR repository and runtime logs. Model permissions are attached separately using the file you already reviewed in Lesson 9.

## Step 6 — Create the execution role

```bash
aws iam create-role --role-name devops-course-agentcore-runtime --assume-role-policy-document file://reports/agentcore-trust.json
aws iam put-role-policy --role-name devops-course-agentcore-runtime --policy-name course-runtime --policy-document file://reports/agentcore-runtime-permissions.json
aws iam put-role-policy --role-name devops-course-agentcore-runtime --policy-name course-model-inference --policy-document file://reports/model-permissions.json
```

The last file must allow the model/profile you will configure next. IAM changes can take time to propagate. Check the actual error before retrying.

## Step 7 — Edit the runtime request

```bash
cp examples/agentcore-runtime.json reports/agentcore-runtime.json
echo "$AGENTCORE_IMAGE"
nano reports/agentcore-runtime.json
```

Replace:

| Field | Value |
|---|---|
| `containerUri` | The full image URI printed above, including tag |
| `roleArn` account | Your account ID |
| `AWS_DEFAULT_REGION` | Your selected region |
| `BEDROCK_MODEL_ID` | The model/profile ID that worked in Lesson 9 |

Keep the runtime name `devops_course_incident`. This name also appears in the scoped log permissions. PUBLIC is the network mode; invocation still uses IAM authentication.

## Step 8 — Create the runtime

```bash
aws bedrock-agentcore-control create-agent-runtime --cli-input-json file://reports/agentcore-runtime.json > reports/runtime-created.json
cat reports/runtime-created.json
```

Copy the returned ID and ARN:

```bash
export RUNTIME_ID=YOUR_RETURNED_RUNTIME_ID
export RUNTIME_ARN=YOUR_RETURNED_RUNTIME_ARN
aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$RUNTIME_ID"
```

Repeat the get command until status is `READY`. If it fails, inspect `failureReason` and the runtime logs before proceeding.

## Step 9 — Review the input snapshot

Use `reports/agentcore-payload.json` from Lesson 10. If the cluster has changed, export a new snapshot in the reader terminal first.

```bash
nano reports/agentcore-payload.json
```

Make sure it contains the intended incident/evidence and no information you should not send to the model.

## Step 10 — Invoke the runtime

In the operator terminal:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --content-type application/json \
  --runtime-session-id "$(openssl rand -hex 24)" \
  --payload fileb://reports/agentcore-payload.json \
  --cli-read-timeout 180 \
  reports/agentcore-cloud-response.json
nano reports/agentcore-cloud-response.json
```

`openssl` supplies a random session identifier. The caller needs InvokeAgentRuntime permission for this runtime; that caller permission is separate from the runtime execution role.

**Expected:** a snapshot-mode investigation with tool trace and usage. `recovery_verified=false` is correct: the runtime did not perform recovery.

If startup or invocation fails, inspect CloudWatch log groups under `/aws/bedrock-agentcore/runtimes/` and check image, role and model access.

## Step 11 — Delete the optional runtime when finished

Inspect the ID and ARN saved in `reports/runtime-created.json`. Confirm they belong to this lab, then:

```bash
aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id "$RUNTIME_ID"
```

Wait for deletion. Its ECR images, role and logs need separate cleanup in [Lesson 12](../12-portfolio-cleanup.md).

Reference: [Create runtime](https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/create-agent-runtime.html), [Invoke runtime](https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore/invoke-agent-runtime.html), [Runtime IAM](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html).
