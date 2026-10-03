#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source platform/versions.env
command -v kubectl >/dev/null
command -v helm >/dev/null
component="${1:?Choose argocd, metrics, monitoring, gateway or vault}"
case "$component" in
load-balancer)
  : "${CLUSTER_NAME:?Set Terraform cluster_name output}"
  : "${VPC_ID:?Set Terraform vpc_id output}"
  : "${AWS_REGION:?Set region}"
  helm repo add eks https://aws.github.io/eks-charts
  helm repo update eks
  helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller --version "$AWS_LB_CHART_VERSION" -n kube-system --set clusterName="$CLUSTER_NAME" --set region="$AWS_REGION" --set vpcId="$VPC_ID" --set serviceAccount.name=aws-load-balancer-controller --wait
  ;;
argocd)
  kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply --server-side -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml"
  kubectl rollout status deployment/argocd-server -n argocd --timeout=300s
  ;;
metrics)
  kubectl apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/$METRICS_SERVER_VERSION/components.yaml"
  kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
  ;;
monitoring)
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm repo update prometheus-community
  helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --version "$KUBE_PROMETHEUS_CHART_VERSION" -n monitoring --create-namespace -f platform/monitoring/values.yaml --wait --timeout 10m
  kubectl apply -f platform/monitoring/bookinfo.yaml
  ;;
gateway)
  kubectl apply --server-side -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/$GATEWAY_API_VERSION/standard-install.yaml"
  helm repo add istio https://istio-release.storage.googleapis.com/charts
  helm repo add jetstack https://charts.jetstack.io
  helm repo update istio jetstack
  helm upgrade --install istio-base istio/base --version "$ISTIO_VERSION" -n istio-system --create-namespace --wait
  helm upgrade --install istiod istio/istiod --version "$ISTIO_VERSION" -n istio-system --wait
  helm upgrade --install cert-manager jetstack/cert-manager --version "$CERT_MANAGER_VERSION" -n cert-manager --create-namespace --set crds.enabled=true --set config.enableGatewayAPI=true --wait
  ;;
vault)
  helm repo add hashicorp https://helm.releases.hashicorp.com
  helm repo update hashicorp
  helm upgrade --install vault hashicorp/vault --version "$VAULT_CHART_VERSION" -n vault --create-namespace -f platform/security/vault-values.yaml
  echo 'Vault is intentionally sealed. Follow docs/labs/vault.md to initialize/unseal.'
  ;;
*) echo 'Unknown component' >&2; exit 2;;
esac
