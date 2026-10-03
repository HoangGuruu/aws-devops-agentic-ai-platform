# Capacity, restart and unavailable pods
Read namespace-scoped pods/events, requests/limits and node capacity before acting.
A restart can help a transient process fault but will not fix a bad image, secret, or insufficient capacity.
Scale proposals are limited to 1..4 productpage replicas. Disable the HPA lab and let GitOps own replicas before using the scale exercise; otherwise the two controllers conflict.
Do not scale a deployment that has a deterministic http500 fault. Keep node scaling separate in Terraform.
Escalate missing permissions, inaccessible metrics and unknown causes to a human.
The agent cannot create, delete, exec into pods, change IAM, or read Kubernetes Secrets.
