# Optional lab — Connect a database

**Goal:** make ratings read from MongoDB, MySQL or MongoDB Atlas.

Complete Lesson 4 first. Try one database at a time. If Argo already manages the app, use the PR process from Lesson 6 for overlay changes.

## Part A — Try a database locally

### Step 1 — Stop the application port-forward

If terminal B uses port 9080, press Ctrl+C there before starting Compose.

### Step 2 — Start local MongoDB

```bash
docker compose -f compose.yaml -f compose.mongodb.yaml up --build -d
docker compose -f compose.yaml -f compose.mongodb.yaml logs --tail=60 mongodb ratings
```

Open the product page. Wait for database initialization if the first request fails. MongoDB is internal to the Compose network and has no authentication in this isolated lab.

Stop this variant before trying MySQL:

```bash
docker compose -f compose.yaml -f compose.mongodb.yaml down
```

### Step 3 — Set local MySQL passwords

Generate a random value for each password:

```bash
openssl rand -hex 24
openssl rand -hex 24
nano .env
```

Add these lines with two different generated values:

```dotenv
MYSQL_PASSWORD=YOUR_GENERATED_APP_PASSWORD
MYSQL_ROOT_PASSWORD=YOUR_GENERATED_ROOT_PASSWORD
```

### Step 4 — Start local MySQL

```bash
docker compose -f compose.yaml -f compose.mysql.yaml up --build -d
docker compose -f compose.yaml -f compose.mysql.yaml logs --tail=60 mysql ratings
```

Wait for MySQL to finish starting, then check the app. Stop it when finished:

```bash
docker compose -f compose.yaml -f compose.mysql.yaml down
```

A persistent volume keeps the existing database password. Changing `.env` does not automatically change a database user on an already initialized volume. Do not use `down -v` unless you intend to delete that data.

## Part B — Prepare EBS storage in EKS

### Step 1 — Enable the storage addon

```bash
source reports/lab.env
nano infra/environments/develop.tfvars
```

Change the existing setting to:

```hcl
enable_storage = true
```

### Step 2 — Apply and check

```bash
terraform -chdir=infra/main plan -var-file=../environments/develop.tfvars
terraform -chdir=infra/main apply -var-file=../environments/develop.tfvars
kubectl apply -f platform/security/storageclass.yaml
kubectl get storageclass course-gp3
kubectl -n kube-system get pods
```

Check that the EBS CSI components are running. The DB manifests explicitly use `course-gp3`; they do not require another default class. This lab's reclaim policy retains volumes after PVC deletion.

## Part C — MongoDB in Kubernetes

### Step 1 — Create MongoDB

```bash
kubectl apply -f platform/databases/mongodb.yaml
kubectl -n bookinfo-develop rollout status statefulset/mongodb --timeout=300s
kubectl -n bookinfo-develop get pvc
```

**Expected:** Pod Ready and PVC Bound. If Pending, inspect the PVC events and EBS CSI permissions.

### Step 2 — Add rating data

```bash
kubectl -n bookinfo-develop exec mongodb-0 -- mongosh test --eval 'db.ratings.replaceOne({ReviewID:1},{ReviewID:1,rating:3},{upsert:true})'
kubectl -n bookinfo-develop exec mongodb-0 -- mongosh test --eval 'db.ratings.replaceOne({ReviewID:2},{ReviewID:2,rating:4},{upsert:true})'
```

These upserts avoid duplicate records if repeated.

### Step 3 — Create the connection Secret

```bash
kubectl -n bookinfo-develop create secret generic ratings-database --from-literal=MONGO_DB_URL='mongodb://mongodb:27017/test'
```

This local lab database has no password and is not publicly exposed. If the Secret already exists, inspect which connection it represents before replacing it.

### Step 4 — Add the MongoDB patch

```bash
cp platform/databases/ratings-mongodb-patch.yaml gitops/overlays/develop/ratings-database.yaml
nano gitops/overlays/develop/kustomization.yaml
```

Make the `patches` section contain these entries:

```yaml
patches:
- path: release.yaml
- path: ratings-database.yaml
```

Keep the existing resources and images. Remove any Vault patch entry so only one database credential method is active. Continue to Part F.

## Part D — MySQL in Kubernetes

### Step 1 — Generate two password files

```bash
openssl rand -hex 24 | tr -d '\n' > reports/mysql-root.txt
openssl rand -hex 24 | tr -d '\n' > reports/mysql-password.txt
chmod 600 reports/mysql-root.txt reports/mysql-password.txt
```

`tr` removes the newline so it is not part of the password. Generate these only for a new database. Keep existing credentials when reusing an initialized PVC.

### Step 2 — Create the Secret and database

```bash
kubectl -n bookinfo-develop create secret generic mysql-credentials \
  --from-file=root-password=reports/mysql-root.txt \
  --from-file=password=reports/mysql-password.txt
kubectl apply -f platform/databases/mysql.yaml
kubectl -n bookinfo-develop rollout status statefulset/mysql --timeout=300s
kubectl -n bookinfo-develop logs mysql-0 --tail=40
```

Save the passwords in your password manager, then remove the local files when no longer needed. The manifest initializes database `test`, user `ratings` and its table.

### Step 3 — Select the MySQL patch

```bash
cp platform/databases/ratings-mysql-patch.yaml gitops/overlays/develop/ratings-database.yaml
nano gitops/overlays/develop/kustomization.yaml
```

Use the same two-entry `patches` section shown in Part C. The copied file now contains MySQL settings instead of MongoDB settings. Continue to Part F.

## Part E — MongoDB Atlas

### Step 1 — Create and prepare Atlas

In your Atlas account:

1. Create a project/deployment that fits your budget and wait until it is ready.
2. Create a database user with readWrite access to `test`.
3. In Data Explorer, create collection `test.ratings`.
4. Insert two documents: `{ "rating": 3 }` and `{ "rating": 4 }`.

### Step 2 — Allow the cluster's outbound IP

```bash
terraform -chdir=infra/main output vpc_id
```

In AWS Console, open VPC → NAT Gateways and find the NAT gateway for this VPC. Copy its public IP into Atlas Network Access as an allowed `/32`. If using multiple NAT gateways, add each actual egress IP.

Your laptop's public IP is not the EKS private nodes' outbound IP. Add a laptop IP only if needed for a separate import/test, then remove it when finished.

### Step 3 — Save the Atlas connection in a Secret

Atlas → Connect → Drivers. Copy the URI, insert the correct user/password, and use database `/test`. URL-encode special password characters as required.

Use hidden terminal input; paste the complete URI and press Enter:

```bash
read -r -s -p 'Atlas connection URI: ' MONGO_DB_URL
```

For a **new** ratings-database Secret:

```bash
kubectl -n bookinfo-develop create secret generic ratings-database --from-literal=MONGO_DB_URL="$MONGO_DB_URL"
unset MONGO_DB_URL
```

If switching from an existing MongoDB Secret in this isolated lab, first stop the exercise traffic and delete only that Secret, then repeat the hidden input/create commands. This briefly interrupts credentials and is a lab switch, not a zero-downtime rotation procedure.

```bash
kubectl -n bookinfo-develop delete secret ratings-database
```

Do not print or commit the URI. Copy/register the MongoDB patch as in Part C, then continue below.

## Part F — Deploy the selected database configuration

### Step 1 — Render and inspect

```bash
kubectl kustomize gitops/overlays/develop > reports/database-rendered.yaml
nano reports/database-rendered.yaml
git diff -- gitops/overlays/develop
```

Check ratings has the intended DB type and Secret reference. Do not apply the patch file as an independent Deployment.

### Step 2 — Deploy

Before Argo is installed:

```bash
kubectl apply -k gitops/overlays/develop
```

After Argo is installed, commit the overlay changes on a lab branch, push, review and merge the PR using Lesson 6. Then wait for sync.

```bash
git add gitops/overlays/develop
git commit -m "Configure the ratings database"
git push -u origin HEAD
```

Use a branch rather than direct main push if main is protected. Keep the selected configuration in Git in either deployment path.

### Step 3 — Test ratings directly

```bash
kubectl -n bookinfo-develop rollout status deployment/ratings-v1 --timeout=300s
kubectl -n bookinfo-develop logs deployment/ratings-v1 -c ratings --tail=40
kubectl -n bookinfo-develop port-forward svc/ratings 9081:9080
```

In another terminal:

```bash
curl -f http://127.0.0.1:9081/ratings/0
```

**Expected:** rating JSON. A productpage HTTP200 alone does not prove the database works.

If you changed only the Secret, restart ratings so its process reloads the environment:

```bash
kubectl -n bookinfo-develop rollout restart deployment/ratings-v1
```

## Part G — Return to the basic incident configuration

Open the overlay kustomization and remove the `ratings-database.yaml` and `ratings-vault.yaml` entries, if present. Keep:

```yaml
patches:
- path: release.yaml
```

Commit/review/merge, or apply directly only if Argo is not installed. Verify ratings works in memory again before removing the database.

You can delete the database resources with their original manifest, for example:

```bash
kubectl delete -f platform/databases/mongodb.yaml
```

PVCs and retained EBS volumes need separate cleanup. Follow [Lesson 12](../12-portfolio-cleanup.md).
