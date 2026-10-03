# Optional lab — Store database credentials in Vault

**Goal:** inject a database connection into ratings from Vault.

**Before you start:** EBS CSI and `course-gp3` are ready, a MongoDB/Atlas database works, and you understand the database lab. Use the operator terminal.

## Step 1 — Install Vault

```bash
source reports/lab.env
source platform/versions.env
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update hashicorp
helm upgrade --install vault hashicorp/vault \
  --version "$VAULT_CHART_VERSION" \
  -n vault --create-namespace \
  -f platform/security/vault-values.yaml
kubectl -n vault get pods,pvc
```

A sealed Vault Pod is not Ready yet. This lab uses one Raft replica and manual unsealing.

## Step 2 — Initialize Vault once

Run this privately: its output contains the unseal key and initial root token.

```bash
kubectl -n vault exec -it vault-0 -- vault operator init -key-shares=1 -key-threshold=1
```

Store the key and token in your password manager, not Git. If Vault is already initialized, use the existing key; do not initialize it again.

## Step 3 — Unseal and log in

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal
kubectl -n vault exec -it vault-0 -- vault login
kubectl -n vault exec vault-0 -- vault status
```

Enter the key/token at the interactive prompts. **Expected:** Initialized true and Sealed false. After restarting Vault, unseal it again.

## Step 4 — Enable secret storage and Kubernetes authentication

```bash
kubectl -n vault exec vault-0 -- vault secrets enable -path=secret kv-v2
kubectl -n vault exec vault-0 -- vault auth enable kubernetes
```

If a mount is already enabled, inspect it and keep the correct existing mount rather than trying to recreate it.

Apply the supplied narrow policy:

```bash
kubectl -n vault exec -i vault-0 -- vault policy write ratings-policy - < platform/security/ratings-policy.hcl
```

Configure authentication from inside the Pod, where the Kubernetes token and CA are available:

```bash
kubectl -n vault exec vault-0 -- vault write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc:443
kubectl -n vault exec vault-0 -- vault write auth/kubernetes/role/bookinfo-ratings \
  bound_service_account_names=bookinfo-ratings \
  bound_service_account_namespaces=bookinfo-develop \
  policies=ratings-policy \
  ttl=1h
```

## Step 5 — Create a local JSON secret file

```bash
nano reports/vault-ratings.json
```

Enter your actual URI in this structure:

```json
{
  "MONGO_DB_URL": "YOUR_MONGODB_OR_ATLAS_CONNECTION_URI"
}
```

Keep valid JSON. This file is local and ignored by Git.

```bash
chmod 600 reports/vault-ratings.json
kubectl -n vault exec -i vault-0 -- sh -c 'umask 077; cat > /tmp/course-ratings.json' < reports/vault-ratings.json
kubectl -n vault exec vault-0 -- vault kv put secret/ratings @/tmp/course-ratings.json
kubectl -n vault exec vault-0 -- rm /tmp/course-ratings.json
rm reports/vault-ratings.json
```

The first command inside the Pod writes the supplied JSON to a private temporary file. Vault imports it, then both temporary copies are removed. Do not print the stored secret in a shared terminal.

## Step 6 — Add the Vault injection patch

```bash
cp platform/security/vault-ratings-patch.yaml gitops/overlays/develop/ratings-vault.yaml
nano gitops/overlays/develop/kustomization.yaml
```

Set the patch list to:

```yaml
patches:
- path: release.yaml
- path: ratings-vault.yaml
```

Remove the direct database patch entry. Keep the existing resources/images.

## Step 7 — Review and deploy through Git

```bash
kubectl kustomize gitops/overlays/develop > reports/vault-rendered.yaml
git diff -- gitops/overlays/develop
git add gitops/overlays/develop
git commit -m "Read ratings credentials from Vault"
git push -u origin HEAD
```

Use a lab branch and a reviewed PR when main is protected. After merging, wait for Argo to sync.

## Step 8 — Verify the application

```bash
kubectl -n bookinfo-develop get pods -l app=ratings
kubectl -n bookinfo-develop rollout status deployment/ratings-v1 --timeout=300s
kubectl -n bookinfo-develop logs deployment/ratings-v1 -c ratings --tail=40
kubectl -n bookinfo-develop port-forward svc/ratings 9081:9080
```

In another terminal, request `http://127.0.0.1:9081/ratings/0`. Expect rating JSON.

If initialization is stuck, inspect the ratings Pod's `vault-agent-init` logs. Check Vault is unsealed and the service account, namespace, auth role and policy path match. Do not display `/vault/secrets/db.json` to prove injection; prove it by the successful DB request.

## Step 9 — Understand rotation and finish

The app reads the JSON file at process startup. Coordinate a real database password change with Vault, then restart and verify the app. Updating only Vault does not change the database password.

To return to the incident baseline, remove the Vault patch entry, keep only `release.yaml`, and deploy the Git change. Verify in-memory ratings works before removing Vault.

The private lab uses internal HTTP, one replica and manual unseal. Production needs its own TLS, availability, auto-unseal, audit and backup design.
