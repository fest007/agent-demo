from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 项目根目录（agent-demo-server/）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'data' / 'server.db'}"
    agent_module_path: str = "../agent-demo-agent"
    desktop_mode: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ]

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
