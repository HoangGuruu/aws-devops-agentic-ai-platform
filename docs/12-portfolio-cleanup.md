# 12 — Save your work and clean up

**Goal:** keep useful evidence and remove resources you no longer need.

## Step 1 — Save your portfolio evidence

Keep sanitized copies of the architecture, image/source SHA, passed pipeline, Argo revision, dashboard, manual incident report, AI trace, approved recovery diff and verification.

Explain these decisions in your portfolio: why GitOps, why read-only agent access, why Pods can be Ready during an HTTP500 incident, and how a human approves recovery.

Do not publish kubeconfigs, state files, database URIs, tokens, webhooks or unreviewed logs.

## Step 2 — Check the account and cluster

Use the operator terminal:

```bash
source reports/lab.env
aws sts get-caller-identity
kubectl config current-context
cat infra/main/backend.hcl
terraform -chdir=infra/main state list
```

Confirm the account, cluster and state key belong to the develop lab. If this terminal was previously used for the agent, return to your operator kubeconfig first; for the default operator config, run `unset KUBECONFIG`.

Back up database data you want to keep. The following steps delete resources; they do not simply pause the lab.

## Step 3 — Record persistent volumes before deleting workloads

```bash
kubectl get pv
kubectl get pvc -A
kubectl get pv -o yaml > reports/volumes-before-cleanup.yaml
```

For each Bookinfo/Vault PVC, identify its PV and EBS `volumeHandle`. Keep that mapping for Step 7. Only record volumes belonging to your lab.

## Step 4 — Stop automatic synchronization

If Argo was installed:

```bash
kubectl -n argocd delete application bookinfo-develop
```

The supplied Application has no resource-deletion finalizer. Removing it stops Argo recreating workloads during cleanup.

## Step 5 — Remove public traffic while the LB controller still runs

If you completed the Gateway lesson:

```bash
kubectl delete -f platform/networking/gateway.yaml
kubectl -n bookinfo-develop get svc
```

Wait for the Gateway's load balancer Service and AWS NLB/target groups to be deleted. Check EC2 → Load Balancers in AWS Console before removing the controller or EKS.

Remove the course CNAME in Cloudflare. If a resource is stuck, inspect controller events/logs; do not remove finalizers blindly.

Skip this step if you never installed Gateway resources.

## Step 6 — Remove application and platform components

```bash
kubectl delete namespace bookinfo-develop
helm list -A
```

Deleting this namespace deletes its workloads and Secrets. It may also delete PVCs; Retain volumes can remain in AWS.

Run only the uninstall commands for releases that appear in your list:

```bash
helm uninstall monitoring -n monitoring
helm uninstall vault -n vault
helm uninstall cert-manager -n cert-manager
helm uninstall istiod -n istio-system
helm uninstall istio-base -n istio-system
helm uninstall aws-load-balancer-controller -n kube-system
```

If Argo was installed:

```bash
kubectl delete namespace argocd
```

A release/namespace that was never installed does not need cleanup. Stop traffic generators and port-forwards when no longer needed.

## Step 7 — Review retained EBS volumes

Open AWS Console → EC2 → Volumes. Match each retained volume to the IDs you saved in Step 3.

1. Confirm it belongs to Bookinfo/Vault.
2. Confirm you have any backup you need.
3. Wait until it is `available` and no longer attached.
4. Delete that specific volume if it is no longer needed.

If still attached, complete the node/cluster cleanup and return to this step. Do not force-detach a volume that is still in use. Check snapshots separately; deleting a volume does not delete its snapshots.

## Step 8 — Empty the four course ECR repositories

Terraform intentionally refuses to delete repositories containing images.

Open ECR → Private repositories. Inspect these exact repositories in your lab account/region:

- `devops-course-develop/productpage`
- `devops-course-develop/details`
- `devops-course-develop/ratings`
- `devops-course-develop/reviews`

If you no longer need the images, open each repository, select its images and delete them. Check all pages/tags until each repository is empty. Leave the repositories themselves for Terraform to delete.

Do not delete images used by another environment you intend to keep.

## Step 9 — Destroy the main infrastructure

```bash
terraform -chdir=infra/main plan -destroy -var-file=../environments/develop.tfvars
```

Review the resource list. If it contains only the intended lab resources:

```bash
terraform -chdir=infra/main destroy -var-file=../environments/develop.tfvars
```

Review again and enter `yes`. If an ECR repository is not empty, return to Step 8. If a network dependency blocks deletion, check load balancers and ENIs from Step 5. Do not erase Terraform state to hide errors.

## Step 10 — Remove Knowledge Base resources if created

```bash
terraform -chdir=infra/knowledge-base output documents_bucket
```

Open that exact documents bucket in S3. Remove the uploaded lab runbooks after retaining any copies you need. Do not empty your Terraform state bucket.

```bash
terraform -chdir=infra/knowledge-base plan -destroy
terraform -chdir=infra/knowledge-base destroy
```

This uses the separate KB state. Review the Knowledge Base, data source, vector resources and document bucket before confirming.

## Step 11 — Remove optional AgentCore resources

Delete the runtime using the last step of the AgentCore lab. Wait for deletion, then inspect and remove only its unused resources:

1. ECR repository `devops-course-agentcore` and its images.
2. IAM role `devops-course-agentcore-runtime` after deleting its inline policies `course-runtime` and `course-model-inference`.
3. Its CloudWatch log group under `/aws/bedrock-agentcore/runtimes/devops_course_incident-*`, after exporting any logs you need.

These were created separately from the EKS Terraform stack.

## Step 12 — Remove the standalone investigator role

In IAM → Roles → `devops-course-investigator`, inspect the role you created in Lesson 9. Delete its course inline policies and then the role if no longer needed. It is outside the main Terraform stack.

## Step 13 — Check remaining costs

- EKS control plane and node group have been deleted.
- Lab NAT gateways, EIPs, NLBs and unused ENIs are removed.
- Retained EBS volumes and snapshots have been reviewed.
- ECR images, KB, runtime and logs are removed or intentionally retained.
- Any separate EC2 workstation is stopped/terminated as appropriate.
- Any Atlas deployment is managed separately in Atlas; Terraform here does not delete it.
- Local Compose is stopped. Delete local volumes only if their data is no longer needed.
- The protected bootstrap state bucket is intentionally retained for state history and may still incur storage charges.

Review Billing/Cost Explorer after usage data updates. A Budget notification is an alert, not a hard spending cap.

**Checkpoint:** you have a sanitized portfolio and know exactly which resources remain.
