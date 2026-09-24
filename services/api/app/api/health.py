"""Liveness and readiness probes (ALB target group + docker-compose healthchecks)."""

from fastapi import APIRouter, Request, Response, status

from app.db.engine import ping

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Process is up. Never touches dependencies, so a DB outage doesn't kill the task."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request, response: Response) -> dict[str, str]:
    """Process can serve traffic: database reachable (the only condition that returns 503).

    `assistant` reports whether questions can be answered. A missing LLM key or knowledge index
    doesn't fail readiness, because login and chat history still work, but it's visible here
    instead of looking healthy.
    """
    state = request.app.state
    db_ok = await ping(state.engine)
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    if getattr(state, "llm", None) is None:
        assistant = "disabled: no LLM provider configured"
    elif getattr(state, "knowledge", None) is None:
        assistant = "disabled: knowledge layer unavailable"
    else:
        assistant = "ready"
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "assistant": assistant,
    }
