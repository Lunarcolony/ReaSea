#!/usr/bin/env bash
# Lightweight install when Docker is unavailable (Python 3.11+ and Node 20+).
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$APP_DIR"

PUBLIC_URL="${PUBLIC_URL:-}"
HTTP_PORT="${HTTP_PORT:-8080}"

if [[ -z "$PUBLIC_URL" ]]; then
  echo "Set PUBLIC_URL, e.g. export PUBLIC_URL=https://your-name.hackclub.app"
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p data logs

export DATABASE_URL="sqlite:///$(pwd)/data/papers.db"
export CORS_ORIGINS="$PUBLIC_URL"
export SECRET_KEY="${SECRET_KEY:-demo-secret}"

nohup uvicorn api.main:app --host 127.0.0.1 --port 8000 > logs/api.log 2>&1 &
echo $! > logs/api.pid

cd frontend
export NEXT_PUBLIC_API_URL="${PUBLIC_URL}/api"
npm install
npm run build
nohup npm start -- -p 3000 > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
cd ..

nohup python pipeline/cooperative.py > logs/crawler.log 2>&1 &
echo $! > logs/crawler.pid

echo "Started API (8000), frontend (3000), crawler."
echo "Point your Nest reverse proxy at port 3000 for the UI and /api -> 8000, or use deploy/nginx.demo.conf."
