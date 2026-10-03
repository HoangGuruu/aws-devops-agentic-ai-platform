# Troubleshooting

First check that you are in the project root and using the correct identity.

- Operator terminal: `source reports/lab.env` and your normal operator kubeconfig.
- Agent terminal: `source reports/agent.env` and the reader kubeconfig.
- Leaving the agent terminal does not change settings in other terminals.

| Problem | Check | Next step |
|---|---|---|
| Python module missing | Virtual environment | Activate `.venv` and install the lesson's requirements |
| Docker permission denied | User groups | Log out/in after joining the Docker group |
| Cannot connect to Docker | Daemon/Desktop | Start Docker and check the Server section of `docker version` |
| Port already in use | Old Compose/port-forward | Stop the relevant process in its own terminal |
| AWS SSO token expired | `aws sts get-caller-identity` | Sign in again with `aws sso login --profile course-lab` |
| AWS AssumeRole denied | Operator ARN, trust and permissions | Correct the intended role/profile; ask the account administrator when needed |
| Terraform checksum mismatch | Lockfile, source and cache | Use a trusted registry/cache; do not disable verification |
| Terraform provider startup error | OS, architecture and plugin version | Resolve the workstation/plugin issue before apply |
| kubectl timeout | Public IP and API CIDR | Update the allowed CIDR and apply; check VPN/network |
| kubectl Unauthorized | Operator IAM ARN or reader token | Use the intended access entry; renew the reader token if expired |
| Reader cannot access Secrets | RBAC | Expected restriction; do not grant Secrets to bypass it |
| ImagePullBackOff | Pod Events, image URL/tag and node IAM | Confirm the image exists and the node can pull it |
| CrashLoopBackOff | Current/previous container logs | Fix configuration or dependency errors rather than guessing |
| PVC Pending | PVC events, CSI and scheduling | Check EBS permissions/class/AZ and the consumer Pod |
| Gateway has no address | LB controller and IAM | Confirm the Terraform flag, service account and subnet configuration |
| Certificate stays Pending | DNS, HTTP-01 challenge and routes | Fix DNS/port 80 and solver routing before production issuance |
| Browser rejects staging cert | Issuer | Expected; switch to production only after staging succeeds |
| Argo cannot read the repo | URL and repository credential | Use the correct URL and read-only credential for private repos |
| Argo Healthy but HTTP500 | Application metrics and logs | A healthy process may still serve errors; inspect the release flag |
| HPA does not scale | CPU requests/usage, target and Argo | Check actual utilization and avoid competing replica controllers |
| Prometheus returns no data | Targets and ServiceMonitor | Verify namespace/labels/port and wait for enough samples |
| Alert not Firing yet | Threshold and duration | Generate sufficient traffic and observe the configured window |
| Slack does not receive alerts | Webhook, channel and AlertmanagerConfig | Confirm the alert matches the course routing labels |
| Vault remains sealed | Vault status | Unseal with the stored key; do not reinitialize |
| Vault injection stuck | Init-container logs | Check unsealed Vault, auth role, service account and secret policy |
| DB authentication fails | Actual database credential | Updating a Kubernetes Secret does not rotate a database user |
| Agent has tool errors | Trace entries | Restore the missing evidence source before trusting the conclusion |
| Proposal stale/expired | Git HEAD and timestamps | Inspect current evidence and generate a new proposal |
| Recovery verification fails | Report fields | Wait for the correct revision, flag off, available replicas and HTTP200 |

Useful operator commands:

```bash
kubectl -n bookinfo-develop get pods,deploy,svc
kubectl -n bookinfo-develop get events --sort-by=.lastTimestamp
kubectl -n bookinfo-develop logs deployment/productpage-v1 -c productpage --tail=60
kubectl -n argocd get application bookinfo-develop -o yaml
```

Redact private information before sharing logs or reports. Do not dump Secrets, tokens or all environment variables.
