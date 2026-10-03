# 3 — Create AWS infrastructure with Terraform

**Goal:** create state storage, a VPC, private worker nodes, EKS, ECR and a GitHub CI role.

**Before you start:** use an AWS lab account and an operator role allowed to create the required IAM, VPC, EKS, ECR and S3 resources. Read [cleanup](12-portfolio-cleanup.md) first. EKS, EC2, NAT and other resources incur charges.

## Step 1 — Install the AWS tools

These commands target Linux x86_64. Check first:

```bash
uname -m
mkdir -p reports/tools
```

**Expected:** `x86_64`. Use the official ARM packages instead if your machine has another architecture.

Install AWS CLI v2:

```bash
curl -fL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o reports/tools/awscliv2.zip
unzip -q -o reports/tools/awscliv2.zip -d reports/tools
sudo reports/tools/aws/install --update
aws --version
```

Install the Terraform version used by this lab:

```bash
curl -fL https://releases.hashicorp.com/terraform/1.13.3/terraform_1.13.3_linux_amd64.zip -o reports/tools/terraform.zip
unzip -q -o reports/tools/terraform.zip -d reports/tools/terraform
sudo install -m 0755 reports/tools/terraform/terraform /usr/local/bin/terraform
terraform version
```

Install kubectl:

```bash
curl -fL https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl -o reports/tools/kubectl
curl -fL https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl.sha256 -o reports/tools/kubectl.sha256
sha256sum reports/tools/kubectl
cat reports/tools/kubectl.sha256
```

Compare the two SHA256 values. They must match before installing:

```bash
sudo install -m 0755 reports/tools/kubectl /usr/local/bin/kubectl
kubectl version --client
```

Install Helm:

```bash
curl -fL https://get.helm.sh/helm-v3.19.0-linux-amd64.tar.gz -o reports/tools/helm.tar.gz
tar -xzf reports/tools/helm.tar.gz -C reports/tools
sudo install -m 0755 reports/tools/linux-amd64/helm /usr/local/bin/helm
helm version --short
```

## Step 2 — Sign in to AWS

For IAM Identity Center/SSO, use the start URL and role supplied by your account administrator:

```bash
aws configure sso --profile course-lab
aws sso login --profile course-lab
export AWS_PROFILE=course-lab
aws sts get-caller-identity
```

**Check:** the Account and Arn belong to your lab account.

**EC2 alternative:** if your workstation already has an approved instance role, skip SSO. Run `unset AWS_PROFILE`, then `aws sts get-caller-identity`. Do not put long-lived access keys in course files.

## Step 3 — Save a few terminal settings

```bash
cp examples/lab.env.example reports/lab.env
nano reports/lab.env
```

Edit the file directly:

```bash
export AWS_PROFILE=course-lab
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export ACCOUNT_ID=YOUR_12_DIGIT_ACCOUNT_ID
export GITHUB_REPO=YOUR_GITHUB_USERNAME/YOUR_REPOSITORY
```

Use the Account value from Step 2. Choose the GitHub repository you will create in Lesson 4. Keep `us-east-1` throughout this walkthrough, or consistently replace it in all AWS files if you choose another region.

If using an EC2 instance role, replace the first line with `unset AWS_PROFILE`.

Load the file:

```bash
source reports/lab.env
aws sts get-caller-identity
```

`source` runs these five settings in the current terminal. Use it again in each new **operator** terminal. It does not create AWS resources or edit Terraform files. `reports/lab.env` is ignored by Git.

## Step 4 — Find your operator role ARN and public IP

Open AWS Console → IAM → Roles → the role used in Step 2. Copy its full **IAM role ARN**, including any path.

Use an ARN starting with `arn:aws:iam::`. Do not paste an STS session ARN starting with `arn:aws:sts::`. If you use an IAM user, use that user's IAM ARN. Do not use root.

Find the workstation's public egress IP:

```bash
curl https://checkip.amazonaws.com
```

Write down the result. For example, IP `203.0.113.10` becomes CIDR `203.0.113.10/32`. Use your real IP, not that example.

## Step 5 — Prepare the state bucket configuration

```bash
cp infra/bootstrap/terraform.tfvars.example infra/bootstrap/terraform.tfvars
nano infra/bootstrap/terraform.tfvars
```

Set these values:

```hcl
region             = "us-east-1"
state_bucket       = "YOUR-GLOBALLY-UNIQUE-STATE-BUCKET"
create_github_oidc = true
```

Choose a unique lowercase bucket name, for example `devops-course-state-<your-account>-<your-name>` without the angle brackets.

Before creating the GitHub OIDC provider, check IAM → Identity providers. If `token.actions.githubusercontent.com` already exists in this account, set `create_github_oidc = false`. Reuse that provider; do not create a duplicate.

## Step 6 — Create the state bucket and OIDC provider

```bash
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap validate
terraform -chdir=infra/bootstrap plan
```

Read the plan. If the account and resources are correct:

```bash
terraform -chdir=infra/bootstrap apply
```

Type `yes` when you approve the displayed plan.

**Expected:** Terraform finishes successfully. This bootstrap uses a local state file. Back up `infra/bootstrap/terraform.tfstate` to secure storage; never commit it. The bucket has a deletion guard.

## Step 7 — Prepare the EKS settings

```bash
cp infra/environments/develop.tfvars.example infra/environments/develop.tfvars
nano infra/environments/develop.tfvars
```

Edit these fields in the existing file:

| Field | What to enter |
|---|---|
| `region` | Your selected AWS region |
| `allowed_api_cidrs` | Your egress IP with `/32` |
| `admin_principal_arn` | The full IAM ARN from Step 4 |
| `github_repository` | Your `OWNER/REPO` |
| `github_oidc_provider_arn` | Replace the example account ID with your account ID |

Keep `name = "devops-course"` and `environment = "develop"` so later names match. Keep two nodes for the basic lab. Add these two lines at the end:

```hcl
enable_load_balancer_controller = true
enable_storage                  = false
```

Storage will be enabled in the optional database/Vault labs. The lab uses one NAT gateway as a cost/availability trade-off.

Check EKS version availability:

```bash
aws eks describe-cluster-versions --cluster-versions 1.35
```

If your region does not support the configured version, stop and check the EKS support information in [Sources](SOURCES.md). Select compatible EKS/kubectl versions before proceeding.

## Step 8 — Configure remote state

```bash
cp infra/environments/develop.backend.hcl.example infra/main/backend.hcl
nano infra/main/backend.hcl
```

Edit only the bucket and region as needed:

```hcl
bucket       = "YOUR-GLOBALLY-UNIQUE-STATE-BUCKET"
key          = "develop/platform.tfstate"
region       = "us-east-1"
encrypt      = true
use_lockfile = true
```

The bucket must be the one created in Step 6. Keep the state key stable. Each environment needs its own key; do not point another environment at this one.

## Step 9 — Validate and review the infrastructure

```bash
terraform -chdir=infra/main init -backend-config=backend.hcl
terraform -chdir=infra/main validate
terraform -chdir=infra/main plan -var-file=../environments/develop.tfvars
```

**Check:** the plan creates the lab resources. It must not unexpectedly delete existing resources. Terraform variables in `.tfvars` are literal values; they do not automatically read the names in `reports/lab.env`.

## Step 10 — Create the infrastructure

```bash
terraform -chdir=infra/main apply -var-file=../environments/develop.tfvars
```

Review the plan and enter `yes`. EKS provisioning can take several minutes.

## Step 11 — Connect to EKS

```bash
terraform -chdir=infra/main output cluster_name
aws eks update-kubeconfig --name devops-course-develop --region "$AWS_REGION"
kubectl get nodes -o wide
terraform -chdir=infra/main output ecr_urls
```

**Expected:** two nodes become `Ready` and Terraform shows four ECR URLs.

If kubectl times out, verify your current public IP matches `allowed_api_cidrs`. If it says Unauthorized, verify the IAM ARN matches the identity running kubectl. Do not open the API to `0.0.0.0/0` as a workaround.

## Step 12 — Know what to keep

Keep the Terraform provider lockfiles. Do not commit real `.tfvars`, backend settings or state. When you change networks, update the CIDR in the tfvars file and run plan/apply again.

**Checkpoint:** EKS nodes are Ready, ECR repositories exist and the operator can use kubectl.

Next: [Deploy Bookinfo](04-deployment.md).
