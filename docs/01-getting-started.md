# 1 — Prepare your workstation

**Goal:** open the source code and prepare a terminal for the labs.

## Step 1 — Choose a workstation

Use Ubuntu 24.04 x86_64, either directly or inside WSL2 on Windows. A machine with at least 4 CPU cores and 8 GB RAM is a useful starting point for the local builds. Java builds may need more memory.

On WSL, keep the source under your Linux home directory, such as `~/courses/`, rather than `/mnt/c/`.

You may also use an Ubuntu EC2 workstation. Connect through SSM or SSH restricted to your own IP. Use an instance role approved for the lab. This guide's default authentication path is local AWS SSO; the EC2 alternative is explained in Lesson 3.

## Step 2 — Extract and open the project

Extract the ZIP. Open a terminal in the extracted parent directory:

```bash
cd devops-aws-ai-course-v2
pwd
ls
```

**Check:** you can see `README.md`, `bookinfo`, `infra`, `gitops`, `agent` and `docs`. This is the **project root**. All lesson commands start here unless a step says otherwise.

## Step 3 — Install basic utilities

```bash
sudo apt-get update
sudo apt-get install -y curl ca-certificates unzip git jq nano openssl python3 python3-venv dnsutils
```

These utilities download files, edit configuration, inspect JSON and run the Python agent.

## Step 4 — Create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

`.venv` keeps project dependencies separate from the operating system. In a new terminal, activate it again before using the Python commands.

## Step 5 — Create a local working folder

```bash
mkdir -p reports
```

Use `reports/` for local settings, investigation output and temporary files. Git ignores this folder. Do not place secrets in tracked manifests.

## Step 6 — Check the source

```bash
python scripts/validate.py
```

**Expected:** a `PASS` message. This checks source structure; it does not deploy or test AWS.

## If your workstation is EC2

When the lessons say `http://127.0.0.1:9080`, that address belongs to the workstation. On your own computer, open a separate terminal and create an SSH tunnel. Replace the key path and EC2 DNS name first:

```bash
ssh -i /path/to/your-key.pem -N \
  -L 9080:127.0.0.1:9080 \
  -L 9090:127.0.0.1:9090 \
  -L 3000:127.0.0.1:3000 \
  -L 8080:127.0.0.1:8080 \
  ubuntu@YOUR_EC2_PUBLIC_DNS
```

Keep the tunnel open. The browser on your computer can then reach the forwarded ports. If you use SSM instead, configure SSM port forwarding for the required port.

**Checkpoint:** you are in the project root, Python is ready and the source check passes.

Next: [Run Bookinfo locally](02-local-containers.md).
