# 6 — Automate delivery with CI/CD and GitOps

**Goal:** GitHub Actions builds and scans images; a reviewed Git change tells Argo CD to deploy them.

**Before you start:** push your source to GitHub, create ECR with Terraform and deploy the initial application.

## Step 1 — Read the CI role ARN

```bash
source reports/lab.env
terraform -chdir=infra/main output github_ci_role_arn
```

Copy the role ARN without its surrounding quotes.

## Step 2 — Configure GitHub's develop environment

On GitHub, open your repository → Settings → Environments → New environment. Name it **develop**.

Add these **environment variables**:

| Name | Value |
|---|---|
| AWS_REGION | Your AWS region |
| AWS_CI_ROLE_ARN | The Terraform output from Step 1 |
| ECR_REGISTRY | `YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com` |
| ECR_PREFIX | `devops-course-develop` |

Use actual account/region values. Allow deployments only from `main`. Add required reviewers if your plan supports them.

Under Settings → Actions → General, allow GitHub Actions to create pull requests. Organization policies may require an administrator to enable this.

The workflow uses OIDC. Do not add static AWS keys or an admin kubeconfig to GitHub Secrets.

## Step 3 — Run the pipeline

Open Actions → **CI build and release proposal** → Run workflow → choose `main`.

Read the four service jobs in order:

1. Build/test the service.
2. Scan the image.
3. Authenticate to AWS using OIDC.
4. Push the image with the source commit tag.

**Expected:** all four jobs pass before the release job runs. Fix failed builds or vulnerability findings rather than disabling the gate.

If the same SHA was already uploaded manually, ECR may reject a duplicate immutable tag. Use a new source commit for the next release. Do not disable immutability.

## Step 4 — Review and merge the release PR

Open the generated `Release Bookinfo ...` pull request. The change should update image references in `gitops/overlays/develop/kustomization.yaml`.

Review the four image tags and merge the PR. Pull the result locally:

```bash
git switch main
git pull --ff-only origin main
```

PRs created using GITHUB_TOKEN may not trigger additional workflows automatically. If your protected branch requires those checks, use your organization's approved GitHub App/manual PR process. Do not remove required checks to force a merge.

## Step 5 — Install Argo CD

```bash
source platform/versions.env
kubectl create namespace argocd
kubectl apply --server-side -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml"
kubectl -n argocd rollout status deployment/argocd-server --timeout=300s
```

If the namespace already exists, skip its create command.

## Step 6 — Open Argo CD

In **terminal D**:

```bash
source reports/lab.env
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Open `https://127.0.0.1:8080`. The local Argo server uses a self-signed certificate. The username is `admin`.

In terminal A, retrieve the initial password privately:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 --decode
```

Log in and change the password. Do not include it in screenshots.

For a private repository: Settings → Repositories → Connect Repo. Add its HTTPS URL and a credential with read-only access to that repository. Public repositories do not need that credential.

## Step 7 — Set your repository URL

```bash
nano platform/argocd/project.yaml
```

Under `spec.sourceRepos`, replace the example URL with your GitHub repository URL, ending in `.git`.

```bash
nano platform/argocd/develop.yaml
```

Set the same URL under `spec.source.repoURL`. Keep `targetRevision: main` and `path: gitops/overlays/develop`.

## Step 8 — Create the Argo application

```bash
kubectl apply -f platform/argocd/project.yaml
kubectl apply -f platform/argocd/develop.yaml
kubectl -n argocd get application bookinfo-develop
```

In Argo's UI, inspect the resource tree, revision and diff. Wait for **Synced** and **Healthy**.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
```

Restart terminal B's port-forward if its Pod was replaced. The page should still return 200.

Save the Argo configuration:

```bash
git add platform/argocd/project.yaml platform/argocd/develop.yaml
git commit -m "Point Argo CD at the course repository"
git push origin main
```

If main is protected, use the PR procedure below.

## Step 9 — Observe self-healing

Before enabling HPA, temporarily change productpage from the default one replica to two:

```bash
kubectl -n bookinfo-develop scale deployment productpage-v1 --replicas=2
kubectl -n bookinfo-develop get deployment productpage-v1 -w
```

Argo should restore the replica count stored in Git. Press Ctrl+C after observing the result. If you changed the desired count earlier, choose a different temporary count for this exercise.

From now on, change the application through Git. `kubectl rollout undo` is not the recovery method for this auto-sync setup, because Argo can reapply the faulty Git state.

## Step 10 — Use this PR procedure for later lessons

Start from a clean main branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c lab/my-change
```

Make the lesson's file edit. Then stage the named file, commit and push the new branch. On GitHub, open a PR, review it and choose **Squash and merge**. Return locally:

```bash
git switch main
git pull --ff-only origin main
```

Use a new branch name for each exercise. Fault and recovery PRs must change only `release.yaml`; this produces the isolated commit required by the recovery policy.

## Environment note

The automatic publish workflow targets develop. The other overlays are examples. Promoting a release means reviewing and reusing the same scanned image references in another configured environment, not automatically creating four clusters.

**Checkpoint:** CI passes, the release PR is merged, Argo is Synced/Healthy and Bookinfo returns 200.

Next: [Monitor and scale](07-operations.md).
