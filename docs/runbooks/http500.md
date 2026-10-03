# Productpage HTTP 500 after a release
Scope: isolated Bookinfo development lab. Alert: BookinfoHighErrorRate.

Symptoms: /productpage returns 500 while /health and Kubernetes readiness remain green.
Argo CD may be Synced and Healthy. That does not prove the business endpoint works.

1. Record the alert time and last release revision.
2. Inspect productpage deployment and LAB_FAULT_MODE (the only allowlisted env field).
3. Query productpage 5xx ratio. Read bounded productpage logs.
4. If LAB_FAULT_MODE=http500 and logs contain `lab_incident`, the injected release is the likely cause.
5. Propose rollback of the latest isolated release.yaml commit to its parent, where fault mode is off.
6. A human reviews the exact diff and approves its SHA256 digest within 15 minutes.
7. The operator commits/pushes the recovery; Argo CD syncs Git. Never use kubectl rollout undo under auto-sync.
8. Verify Argo Synced, Deployment available, LAB_FAULT_MODE=off and /productpage HTTP 200.
9. Continue traffic for at least two minutes, inspect metrics and confirm alert resolves.
10. Report impact, evidence, cause, recovery commit, time to recover and prevention.

Do not restart or scale as a substitute for reverting a deterministic application fault.
Do not claim recovery from a successful git push alone.
