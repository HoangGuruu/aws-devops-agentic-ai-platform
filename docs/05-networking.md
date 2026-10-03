# 5 — Add a domain and HTTPS

**Goal:** open Bookinfo at `https://bookinfo.your-domain.com/productpage`.

**Before you start:** Bookinfo works in EKS, and you control a domain in Cloudflare. You can skip this lesson and keep using port-forward if you do not have a domain.

## Step 1 — Load the settings and check the VPC

```bash
source reports/lab.env
source platform/versions.env
terraform -chdir=infra/main output vpc_id
```

`platform/versions.env` contains the addon versions used in this lab. Copy the VPC ID from the Terraform output:

```bash
export VPC_ID=YOUR_VPC_ID
```

## Step 2 — Install the AWS Load Balancer Controller

Lesson 3 enabled its IAM and Pod Identity configuration. Install the Kubernetes controller:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version "$AWS_LB_CHART_VERSION" \
  -n kube-system \
  --set clusterName=devops-course-develop \
  --set region="$AWS_REGION" \
  --set vpcId="$VPC_ID" \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait
```

```bash
kubectl -n kube-system rollout status deployment/aws-load-balancer-controller --timeout=300s
```

**Expected:** rollout succeeds. A running controller also needs the IAM permissions from Terraform to create AWS resources.

## Step 3 — Install Gateway API and Istio

```bash
kubectl apply --server-side -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/$GATEWAY_API_VERSION/standard-install.yaml"
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio
helm upgrade --install istio-base istio/base --version "$ISTIO_VERSION" -n istio-system --create-namespace --wait
helm upgrade --install istiod istio/istiod --version "$ISTIO_VERSION" -n istio-system --wait
kubectl get gatewayclass
```

**Expected:** an Istio GatewayClass is present.

## Step 4 — Install cert-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update jetstack
helm upgrade --install cert-manager jetstack/cert-manager \
  --version "$CERT_MANAGER_VERSION" \
  -n cert-manager --create-namespace \
  --set crds.enabled=true \
  --set config.enableGatewayAPI=true \
  --wait
```

```bash
kubectl -n cert-manager get pods
```

**Expected:** cert-manager Pods are ready. Gateway API support allows cert-manager to create an HTTP-01 challenge route.

## Step 5 — Restart Bookinfo to add sidecars

The supplied namespace has the Istio injection label. Pods created before Istio was installed need to be recreated:

```bash
kubectl -n bookinfo-develop rollout restart deployment
kubectl -n bookinfo-develop rollout status deployment/productpage-v1 --timeout=300s
kubectl -n bookinfo-develop get pods
```

Check that the application Pods now include the sidecar, usually showing `2/2` Ready. Restart terminal B's port-forward if its old Pod was replaced.

## Step 6 — Edit your hostname and email

```bash
nano platform/networking/gateway.yaml
```

Replace **every** `bookinfo.example.com` with `bookinfo.your-real-domain.com`. This includes the listeners and HTTPRoutes. Do not change the resource names.

```bash
nano platform/networking/certificate.yaml
```

Replace `admin@example.com` with your email and `bookinfo.example.com` with the same hostname. Keep the staging issuer for the first test.

## Step 7 — Create the Gateway

```bash
kubectl apply -f platform/networking/gateway.yaml
kubectl -n bookinfo-develop get gateway bookinfo
kubectl -n bookinfo-develop get svc
```

Wait for the load balancer address:

```bash
kubectl -n bookinfo-develop get gateway bookinfo -o jsonpath='{.status.addresses[0].value}{"\n"}'
```

Copy the NLB DNS hostname. The HTTPS listener may report that its certificate Secret is missing until the next steps finish.

## Step 8 — Create the Cloudflare DNS record

Open your domain in Cloudflare → DNS → Add record:

| Field | Value |
|---|---|
| Type | CNAME |
| Name | bookinfo |
| Target | The NLB DNS hostname from Step 7 |
| Proxy status | DNS only |
| TTL | Auto |

Do not include `https://` or a path in the target.

Set your actual hostname in the terminal:

```bash
export BOOKINFO_HOST=bookinfo.your-real-domain.com
dig +short "$BOOKINFO_HOST"
curl -I "http://$BOOKINFO_HOST/productpage"
```

DNS should resolve to the load balancer. HTTP redirects to HTTPS. Port 80 must remain reachable for the certificate challenge.

## Step 9 — Test certificate issuance with staging

```bash
kubectl apply -f platform/networking/certificate.yaml
kubectl -n bookinfo-develop get certificate,issuer,order,challenge
kubectl -n bookinfo-develop wait --for=condition=Ready certificate/bookinfo --timeout=300s
```

**Expected:** the certificate becomes Ready. A staging certificate is intentionally not trusted by browsers.

If it does not become Ready:

```bash
kubectl -n bookinfo-develop describe certificate bookinfo
kubectl -n bookinfo-develop get challenge
kubectl -n cert-manager logs deployment/cert-manager --tail=60
```

Fix DNS, port 80 and route errors before requesting a production certificate.

## Step 10 — Request a trusted certificate

```bash
nano platform/networking/certificate.yaml
```

Change these four fields:

| Field | New value |
|---|---|
| Issuer `metadata.name` | `letsencrypt-production` |
| Issuer `spec.acme.server` | `https://acme-v02.api.letsencrypt.org/directory` |
| Issuer `spec.acme.privateKeySecretRef.name` | `letsencrypt-production-account` |
| Certificate `spec.issuerRef.name` | `letsencrypt-production` |

Keep your hostname, email and `secretName: bookinfo-tls` unchanged.

```bash
kubectl apply -f platform/networking/certificate.yaml
kubectl -n bookinfo-develop describe certificate bookinfo
```

Wait for the replacement certificate. Then verify without disabling TLS validation:

```bash
curl -f -o /dev/null -w '%{http_code}\n' "https://$BOOKINFO_HOST/productpage"
```

**Expected:** `200`, with a certificate your browser trusts. A stale Ready condition alone is not enough; check the actual HTTPS request.

## Step 11 — Try version routing (optional)

```bash
kubectl apply -f platform/networking/reviews-canary.yaml
kubectl -n bookinfo-develop describe httproute reviews-split
```

Inspect Accepted/ResolvedRefs. The route uses weights 90 and 10 for reviews-v1 and reviews-v2. This requires support for Service-attached HTTPRoute in the installed implementation. A few browser refreshes are not a statistical test of the traffic ratio.

Remove the optional route after the exercise:

```bash
kubectl delete -f platform/networking/reviews-canary.yaml
```

## Step 12 — Save your configuration

```bash
git add platform/networking
git commit -m "Configure the Bookinfo domain and certificate"
git push origin main
```

If your branch already requires pull requests, use the PR procedure in Lesson 6 instead of direct push.

Grafana, Vault and Argo CD remain private and use port-forward in this course.

**Checkpoint:** the Bookinfo HTTPS endpoint returns 200 with a trusted certificate.

Next: [Automate delivery](06-delivery.md).
