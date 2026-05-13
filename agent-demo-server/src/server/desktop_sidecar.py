"""Desktop sidecar entrypoint.

This is packaged by PyInstaller and started by the Tauri shell. It binds only to
127.0.0.1 and stores runtime data under the user's app-data directory.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


def _app_data_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "AgentDemo"
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Demo desktop sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Desktop sidecar must bind to localhost only")

    data_dir = _app_data_dir()
    os.environ.setdefault("DESKTOP_MODE", "true")
    os.environ.setdefault("SERVER_HOST", "127.0.0.1")
    os.environ.setdefault("SERVER_PORT", str(args.port))
    os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{data_dir / 'server.db'}")
    os.environ.setdefault("SHORT_TERM_DB", str(data_dir / "memory.db"))
    os.environ.setdefault("LONG_TERM_DB", str(data_dir / "long_term.db"))
    os.environ.setdefault("CHROMA_PERSIST_DIR", str(data_dir / "chroma"))
    os.environ.setdefault("ENABLE_DANGEROUS_TOOLS", "false")
    os.environ.setdefault(
        "TOOL_WORKSPACE_ROOT",
        str(Path.home() / "Documents"),
    )
    os.environ.setdefault(
        "CORS_ORIGINS",
        '["http://tauri.localhost","https://tauri.localhost","http://127.0.0.1:3000","http://localhost:3000"]',
    )

    uvicorn.run(
        "server.main:app",
        host="127.0.0.1",
        port=args.port,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
