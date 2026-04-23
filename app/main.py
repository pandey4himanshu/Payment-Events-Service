from __future__ import annotations

import os
from threading import Thread

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.init_db import init_db
from app.routes.events import router as events_router
from app.routes.health import router as health_router
from app.routes.reconciliation import router as reconciliation_router
from app.routes.transactions import router as transactions_router
from scripts.seed_if_empty import main as seed_if_empty


settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A production-minded backend service for ingesting payment lifecycle events and reconciliation reporting.",
    )

    init_db()

    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(transactions_router)
    app.include_router(reconciliation_router)

    @app.on_event("startup")
    def startup_seed() -> None:
        if os.getenv("AUTO_SEED_DATA", "false").lower() == "true":
            Thread(target=seed_if_empty, daemon=True).start()

    return app


app = create_app()
