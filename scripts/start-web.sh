#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR/agent-demo-web"

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck source=/dev/null
  . "$NVM_DIR/nvm.sh"
  nvm use 23
else
  echo "[web] nvm not found at $NVM_DIR/nvm.sh"
  echo "[web] Please install/load nvm, then run: nvm use 23"
  exit 1
fi

cd "$PROJECT_DIR"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "[web] pnpm is required. Enable corepack or install pnpm first."
  exit 1
fi

if [ ! -d "node_modules" ]; then
  echo "[web] node_modules missing. Run: cd $PROJECT_DIR && nvm use 23 && pnpm install"
  exit 1
fi

echo "[web] Starting Vite dev server from $PROJECT_DIR"
echo "[web] URL: http://localhost:3000"
echo "[web] API proxy target: http://localhost:8000"
pnpm dev
