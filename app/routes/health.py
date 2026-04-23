from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict[str, object]:
    return {
        "service": "Setu Reconciliation Service",
        "status": "ok",
        "docs_url": "/docs",
        "health_url": "/health",
        "key_endpoints": [
            "/events",
            "/transactions",
            "/reconciliation/summary",
            "/reconciliation/discrepancies",
        ],
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
