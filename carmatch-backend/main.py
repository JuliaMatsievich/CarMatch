from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.routers import auth, chat

app = FastAPI(
    title="CarMatch API",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Регистрация и вход"},
        {"name": "chat", "description": "Чат с GigaChat"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.on_event("startup")
def _log_routes():
    """При старте выводит все зарегистрированные пути (для проверки, что chat подключён)."""
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                if method != "HEAD":
                    print(f"  {method:6} {route.path}")
