#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/agent-demo-agent"

cd "$PROJECT_DIR"

if [ ! -f ".env" ]; then
  echo "[agent] Missing .env. Create it with: cp .env.example .env"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[agent] uv is required. Install uv first."
  exit 1
fi

echo "[agent] Starting Agent CLI from $PROJECT_DIR"
echo "[agent] Tip: Web mode does not require this process; this is for CLI debugging."
uv run python -m agent.main
