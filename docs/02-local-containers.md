# 2 — Run Bookinfo with Docker

**Goal:** build four services and open Bookinfo locally.

**Before you start:** complete Lesson 1. The installation commands below are for Ubuntu x86_64.

## Step 1 — Install Docker

If you already use Docker Desktop with WSL integration, enable integration for your Ubuntu distribution and skip the Engine installation below. Do not install a second daemon on top of that setup.

For Ubuntu without Docker, add Docker's package repository:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo nano /etc/apt/sources.list.d/docker.list
```

For **Ubuntu 24.04 on x86_64**, paste this single line into the file:

```text
deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable
```

Save the file, then install Docker:

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and log in again so the group change takes effect. The Docker group gives powerful access to this workstation; use your lab account.

## Step 2 — Check Docker

Return to the project root:

```bash
docker version
docker compose version
docker run --rm hello-world
```

**Expected:** Docker shows both Client and Server, and hello-world completes. If you see `permission denied`, log in again. If you see `Cannot connect`, start Docker Engine or Docker Desktop.

## Step 3 — Understand the application

| Service | Language | Responsibility |
|---|---|---|
| productpage | Python | Web page that calls details and reviews |
| details | Ruby | Book information |
| reviews | Java | Reviews, optionally including ratings |
| ratings | Node.js | Rating data |

Open the Compose file:

```bash
nano compose.yaml
```

Each `build` field points to a service directory. Only productpage publishes a port on your workstation. The services communicate through their Compose service names.

## Step 4 — Set the session secret

```bash
cp .env.example .env
openssl rand -hex 32
nano .env
```

Copy the generated value into `SESSION_SECRET` and leave the fault disabled:

```dotenv
SESSION_SECRET=PASTE_YOUR_GENERATED_VALUE
LAB_FAULT_MODE=off
```

Save the file. Do not share the generated value or commit `.env`. Only copy the example file on your first run; keep your existing settings on later runs.

## Step 5 — Build the images

```bash
docker compose build
```

**Expected:** productpage, details, reviews and ratings all build successfully. Read the failing service's build output if a dependency installation fails.

## Step 6 — Start the application

```bash
docker compose up -d
docker compose ps
```

The services may need a little time to start. `depends_on` starts dependencies first; it does not prove they are ready.

## Step 7 — Check the result

```bash
curl -f http://127.0.0.1:9080/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
```

**Expected:** the page returns `200`. Open `http://127.0.0.1:9080/productpage` in your browser. You should see the book and reviews.

If it fails:

```bash
docker compose logs --tail=60 productpage
docker compose logs --tail=60 reviews
```

## Step 8 — Try the application fault

```bash
nano .env
```

Change only this line:

```dotenv
LAB_FAULT_MODE=http500
```

Recreate productpage with that setting:

```bash
docker compose up -d --no-deps productpage
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/health
```

**Expected:** productpage returns `500`, while health still returns `200`. A running process is not the same as a working user experience.

## Step 9 — Restore the application

Open `.env`, set `LAB_FAULT_MODE=off`, save, then run:

```bash
docker compose up -d --no-deps productpage
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9080/productpage
```

**Expected:** `200` again.

## Step 10 — Stop local containers

```bash
docker compose down
```

This frees port 9080 for Kubernetes later. Do not add `-v` if you need to keep database volumes from an optional lab.

**Checkpoint:** all four services build; the page works; you can enable and disable the fault.

Next: [Create AWS infrastructure](03-infrastructure.md).
