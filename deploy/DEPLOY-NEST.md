# Deploy Research Feed on Hack Club Nest

Host: `jithesh@hackclub.app`

## 1. SSH access (required first)

You shared a **public** key. The server must have that key in `~/.ssh/authorized_keys` for the user you log in as, and your PC needs the matching **private** key.

On your Windows machine (PowerShell):

```powershell
# If you don't have a key yet:
ssh-keygen -t ed25519 -C "jegan@JSNUC"

# Show your public key (add this on the Nest host):
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

On the Nest container (via Hack Club console or an account that already has access):

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOiN260eEQOaFSusYNYOPgS0HNLmKYxCyQxKyEykMi2a jegan@JSNUC' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Test from your PC:

```powershell
ssh jithesh@hackclub.app
```

## 2. Upload the project + database

From your project folder on Windows (Git Bash or WSL recommended):

```bash
cd /c/Users/jegan/OneDrive/Desktop/ailearning-main

# Exclude heavy/unnecessary paths
rsync -avz --progress \
  --exclude node_modules --exclude .venv --exclude __pycache__ \
  --exclude frontend/.next --exclude .git \
  ./ jithesh@hackclub.app:~/research-feed/
```

Or with `scp`:

```powershell
scp -r api crawlers data deploy frontend pipeline recommender scripts utils *.py requirements.txt docker-compose.demo.yml Dockerfile.api jithesh@hackclub.app:~/research-feed/
```

**Important:** include `data/papers.db` so the demo already has papers.

## 3. Start on the server (Docker — recommended)

```bash
ssh jithesh@hackclub.app
cd ~/research-feed
chmod +x deploy/install-on-nest.sh

# Use your Nest public URL (from Hack Club dashboard)
export PUBLIC_URL=https://YOUR-SUBDOMAIN.hackclub.app
export HTTP_PORT=8080   # or the port Nest maps to your container

./deploy/install-on-nest.sh
```

In the Hack Club Nest dashboard, point your service to **port 8080** (nginx serves the whole app: UI + `/api`).

## 4. Verify

- Open your Nest URL in a browser.
- Header should show paper count (from `/api/stats`).
- Try refresh feed and open a paper.

Logs:

```bash
docker compose -f docker-compose.demo.yml logs -f
```

## 5. Without Docker

If the container has Python 3.11+ and Node 20+ only:

```bash
export PUBLIC_URL=https://YOUR-SUBDOMAIN.hackclub.app
chmod +x deploy/install-without-docker.sh
./deploy/install-without-docker.sh
```

Configure Nest to proxy `/` → 3000 and `/api` → 8000.

## Architecture (demo stack)

```
Browser → Nest proxy → nginx:8080
                         ├─ /      → Next.js (frontend)
                         ├─ /api/* → FastAPI (api)
                         └─ crawler keeps adding papers (optional)
```

SQLite database: `data/papers.db` (persisted on disk).
