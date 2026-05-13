from fastapi.middleware.cors import CORSMiddleware
from server.config import get_settings


def setup_cors(app):
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
