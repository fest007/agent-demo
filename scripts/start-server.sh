#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/agent-demo-server"
AGENT_DIR="$ROOT_DIR/agent-demo-agent"

cd "$PROJECT_DIR"

if [ ! -f "$AGENT_DIR/.env" ]; then
  echo "[server] Missing $AGENT_DIR/.env. Create it with: cd $AGENT_DIR && cp .env.example .env"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "[server] Missing .env. Create it with: cp .env.example .env"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[server] uv is required. Install uv first."
  exit 1
fi

echo "[server] Starting FastAPI server from $PROJECT_DIR"
echo "[server] URL: http://localhost:8000"
echo "[server] Docs: http://localhost:8000/docs"
uv run python -m server.main
