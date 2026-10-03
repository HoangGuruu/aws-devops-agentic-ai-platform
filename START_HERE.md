# Start here

## What you will build

**Project 1:** Docker → Terraform → EKS → HTTPS → CI/CD → GitOps → monitoring → incident recovery.

**Project 2:** Bedrock → read-only tools → runbooks → recovery proposal → human approval → GitOps → verification.

The same Bookinfo application is used throughout both projects.

## How to follow a lesson

1. Read the goal and prerequisites.
2. Open the file named in the step.
3. Replace the example values with your own values.
4. Run the command from the project root.
5. Check the expected result before continuing.

Run one code block at a time. Do not paste an entire lesson into the terminal.

A `bash` block contains terminal commands. A `yaml`, `hcl`, `json` or `dotenv` block shows file content: paste it into the specified file, not into your terminal.

Values such as `YOUR_ACCOUNT_ID` and `YOUR_GITHUB_REPO` are placeholders. Replace them before running the command. Account IDs such as `111122223333` and domains such as `example.com` are examples.

## Editing a file

The lessons use `nano`. For example:

```bash
nano infra/environments/develop.tfvars
```

Edit the file. Press **Ctrl+O**, then **Enter** to save. Press **Ctrl+X** to close. You can use VS Code instead if you prefer.

## Terminals used in the course

| Terminal | Purpose |
|---|---|
| A — Operator | Terraform, Git and Kubernetes administration |
| B — Application | Keep the productpage port-forward running |
| C — Metrics | Keep the Prometheus port-forward running |
| D — Interface | Open Grafana or Argo CD |
| E — Traffic | Run the load test |
| F — Agent | Use the restricted AWS and Kubernetes identities |

A port-forward keeps running until you press Ctrl+C. Leave that terminal open and use another terminal for the next command. If a deployment replaces its Pod, restart the application port-forward.

## Choose your path

- **Local practice:** Lessons 1–2 and the offline demo in Lesson 9. No AWS account is needed for those exercises.
- **Project 1:** Lessons 1–8. Skip Lesson 5 if you do not have a domain; use port-forward instead.
- **Project 2:** Complete Project 1, then follow Lessons 9–11.
- **Optional:** Add databases, Vault, Knowledge Base and AgentCore after the basic path works.
- **Finish:** Follow Lesson 12. Closing a terminal does not delete AWS resources.

Start with [Lesson 1](docs/01-getting-started.md).
