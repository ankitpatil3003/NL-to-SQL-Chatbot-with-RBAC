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
    """Process can serve traffic: database reachable."""
    db_ok = await ping(request.app.state.engine)
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable"}
