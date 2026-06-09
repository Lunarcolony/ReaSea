#!/usr/bin/env bash
# Run on the Nest host after copying the project (e.g. ~/research-feed).
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$APP_DIR"

PUBLIC_URL="${PUBLIC_URL:-}"
HTTP_PORT="${HTTP_PORT:-8080}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 24 2>/dev/null || echo demo-secret-change-me)}"

if [[ -z "$PUBLIC_URL" ]]; then
  echo "Set PUBLIC_URL to your Nest public URL, e.g.:"
  echo "  export PUBLIC_URL=https://your-name.hackclub.app"
  exit 1
fi

export NEXT_PUBLIC_API_URL="${PUBLIC_URL}/api"
export CORS_ORIGINS="$PUBLIC_URL"
export HTTP_PORT
export SECRET_KEY

mkdir -p data

if [[ ! -f data/papers.db ]]; then
  echo "No data/papers.db found — API will create an empty database on first start."
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker or use deploy/install-without-docker.sh"
  exit 1
fi

COMPOSE="docker compose"
if ! $COMPOSE version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

echo "Building and starting Research Feed on port $HTTP_PORT ..."
$COMPOSE -f docker-compose.demo.yml build --build-arg NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL"
$COMPOSE -f docker-compose.demo.yml up -d

echo ""
echo "Research Feed is starting."
echo "  Site:  $PUBLIC_URL  (map Nest proxy to host port $HTTP_PORT)"
echo "  API:   $NEXT_PUBLIC_API_URL"
echo "  Logs:  $COMPOSE -f docker-compose.demo.yml logs -f"
echo "  Stop:  $COMPOSE -f docker-compose.demo.yml down"
