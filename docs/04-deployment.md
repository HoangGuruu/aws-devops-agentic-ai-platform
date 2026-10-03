# 4 — Deploy Bookinfo to EKS

**Goal:** build the service images, upload them to ECR and deploy Bookinfo.

**Before you start:** complete Lesson 3. Stop local Compose so port 9080 is available.

## Step 1 — Create your GitHub repository

On GitHub, create an empty repository using the `OWNER/REPO` recorded in `reports/lab.env`. Do not initialize it with another README.

In terminal A, from the project root:

```bash
source reports/lab.env
git init -b main
git config user.name "YOUR_NAME"
git config user.email "YOUR_EMAIL"
git status --short
```

Replace the name and email first. Check that `.env`, `reports/`, real tfvars and state files are not listed. They are ignored by the supplied `.gitignore`.

```bash
git add .
git diff --cached --stat
git commit -m "Initialize the Bookinfo course lab"
git remote add origin "https://github.com/$GITHUB_REPO.git"
git push -u origin main
```

Authenticate using your Git credential manager, GitHub token prompt or SSH setup. Never embed a token in the repository URL.

If Git is already initialized, inspect `git status` and `git remote -v` instead of repeating init/add remote. CI may fail on this initial push because Lesson 6 has not configured its environment yet.

## Step 2 — Set an image tag

```bash
git rev-parse HEAD
```

Copy the full 40-character commit SHA. Set it as the image tag:

```bash
export IMAGE_TAG=PASTE_THE_FULL_COMMIT_SHA
export REGISTRY="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo "$REGISTRY"
echo "$IMAGE_TAG"
```

The registry must match your AWS account and region. A commit tag identifies the source used for the build.

## Step 3 — Sign in to ECR

```bash
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
```

**Expected:** `Login Succeeded`. The command passes the short-lived ECR password to Docker without printing it.

## Step 4 — Build each service

Run these commands individually. Each final directory is the Docker build context:

```bash
docker build -t "$REGISTRY/devops-course-develop/productpage:$IMAGE_TAG" bookinfo/src/productpage
```

```bash
docker build -t "$REGISTRY/devops-course-develop/details:$IMAGE_TAG" bookinfo/src/details
```

```bash
docker build -t "$REGISTRY/devops-course-develop/ratings:$IMAGE_TAG" bookinfo/src/ratings
```

```bash
docker build -t "$REGISTRY/devops-course-develop/reviews:$IMAGE_TAG" bookinfo/src/reviews
```

**Check:** all four builds finish successfully. The productpage Docker build includes its unit-test stage.

## Step 5 — Push the images

```bash
docker push "$REGISTRY/devops-course-develop/productpage:$IMAGE_TAG"
docker push "$REGISTRY/devops-course-develop/details:$IMAGE_TAG"
docker push "$REGISTRY/devops-course-develop/ratings:$IMAGE_TAG"
docker push "$REGISTRY/devops-course-develop/reviews:$IMAGE_TAG"
```

Open ECR in the AWS Console. Check each repository contains the same source tag. ECR tags are immutable: do not overwrite a published tag. For a new build, commit the source change and use its new SHA.

This manual upload bootstraps the application. Lesson 6 adds security scans before subsequent releases.

## Step 6 — Edit the image references

```bash
nano gitops/overlays/develop/kustomization.yaml
```

Keep `resources`, `patches` and `namespace`. In the `images` section:

1. Replace `111122223333` with your account ID in all four `newName` values.
2. Replace the region if you chose a different one.
3. Replace every `REPLACE_WITH_COMMIT_SHA` with the tag from Step 2.
4. Keep the `name` fields unchanged; Kustomize uses them to match the base images.

One entry should have this structure:

```yaml
- name: course/productpage
  newName: YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/devops-course-develop/productpage
  newTag: YOUR_FULL_COMMIT_SHA
```

YAML does not expand `$ACCOUNT_ID` or `$IMAGE_TAG`. Paste the actual values into the file.

## Step 7 — Create the namespace and session Secret

```bash
kubectl create namespace bookinfo-develop
```

If it already exists, continue. Generate a local secret file:

```bash
openssl rand -hex 32 > reports/session-secret.txt
chmod 600 reports/session-secret.txt
kubectl -n bookinfo-develop create secret generic productpage-session --from-file=secret=reports/session-secret.txt
rm reports/session-secret.txt
```

Create the Secret only once. On later runs, keep the existing Secret rather than rotating it accidentally. Do not print or commit secret values.

## Step 8 — Review and apply the manifests

```bash
kubectl kustomize gitops/overlays/develop > reports/bookinfo-rendered.yaml
nano reports/bookinfo-rendered.yaml
```

Check the namespace and image URLs. Close the file and deploy:

```bash
kubectl apply -k gitops/overlays/develop
kubectl -n bookinfo-develop get deployments
kubectl -n bookinfo-develop get pods
```

Wait for each deployment:

```bash
kubectl -n bookinfo-develop rollout status deployment/productpage-v1 --timeout=300s
kubectl -n bookinfo-develop rollout status deployment/details-v1 --timeout=300s
kubectl -n bookinfo-develop rollout status deployment/ratings-v1 --timeout=300s
kubectl -n bookinfo-develop rollout status deployment/reviews-v1 --timeout=300s
kubectl -n bookinfo-develop rollout status deployment/reviews-v2 --timeout=300s
kubectl -n bookinfo-develop rollout status deployment/reviews-v3 --timeout=300s
```

All six deployments should become available. The three reviews versions reuse the reviews image with different settings.

## Step 9 — Open the application

In **terminal B**, from the project root:

```bash
source reports/lab.env
kubectl -n bookinfo-develop port-forward svc/productpage 9080:9080
```

Leave terminal B running. In terminal A:

```bash
curl -f http://127.0.0.1:9080/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
```

**Expected:** HTTP `200`. Open `http://127.0.0.1:9080/productpage` in your browser.

If a Pod has `ImagePullBackOff`, inspect it with `kubectl describe pod POD_NAME -n bookinfo-develop`. Check the image URL/tag, ECR contents and node IAM/network access.

## Step 10 — Save the release configuration

```bash
git add gitops/overlays/develop/kustomization.yaml
git commit -m "Set the initial Bookinfo image tags"
git push origin main
```

The main path uses ratings without a database. Try the [database lab](labs/databases.md) separately when ready.

**Checkpoint:** all deployments are available, the page returns 200 and Git contains the deployed image references.

Next: [HTTPS](05-networking.md), or skip to [CI/CD](06-delivery.md) if you do not have a domain.
