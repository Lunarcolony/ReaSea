#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/root/research-feed"
PUBLIC_URL="${PUBLIC_URL:-https://jithesh.hackclub.app}"
HTTP_PORT="${HTTP_PORT:-80}"

echo "==> Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv nginx wget ca-certificates gnupg

if ! command -v node >/dev/null 2>&1 || [[ "$(node -v 2>/dev/null || echo v0)" < "v18" ]]; then
  echo "==> Installing Node.js 20..."
  wget -qO- https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

echo "==> Python: $(python3 --version)"
echo "==> Node: $(node -v)"
echo "==> npm: $(npm -v)"

cd "$APP_DIR"
mkdir -p data logs

echo "==> Python virtualenv + deps..."
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r deploy/requirements-demo.txt

echo "==> Building frontend..."
cd frontend
export NEXT_PUBLIC_API_URL="/api"
npm install --silent
npm run build
cd ..

echo "==> Configuring nginx on port ${HTTP_PORT}..."
cat > /etc/nginx/sites-available/research-feed <<'NGINX'
server {
    listen HTTP_PORT_PLACEHOLDER;
    server_name _;

    location /api/ {
        rewrite ^/api/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /_next/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX
sed -i "s/HTTP_PORT_PLACEHOLDER/${HTTP_PORT}/" /etc/nginx/sites-available/research-feed
ln -sf /etc/nginx/sites-available/research-feed /etc/nginx/sites-enabled/research-feed
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "==> Starting services..."
export DATABASE_URL="sqlite:///${APP_DIR}/data/papers.db"
export CORS_ORIGINS="${PUBLIC_URL}"
export SECRET_KEY="${SECRET_KEY:-demo-research-feed-secret}"

pkill -f "uvicorn api.main:app" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true
sleep 1

source .venv/bin/activate
nohup uvicorn api.main:app --host 127.0.0.1 --port 8000 > logs/api.log 2>&1 &
echo $! > logs/api.pid

cd frontend
nohup npm start -- -p 3000 -H 127.0.0.1 > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
cd ..

nginx -s reload 2>/dev/null || nginx

sleep 3
echo "==> Health check..."
wget -qO- "http://127.0.0.1:${HTTP_PORT}/health" >/dev/null && echo " API OK" || echo " API check failed (see logs/api.log)"
wget -qO- "http://127.0.0.1:${HTTP_PORT}/" >/dev/null && echo " Frontend OK" || echo " Frontend check failed (see logs/frontend.log)"

echo ""
echo "Deployed at: ${PUBLIC_URL}"
echo "Logs: tail -f ${APP_DIR}/logs/api.log ${APP_DIR}/logs/frontend.log"
