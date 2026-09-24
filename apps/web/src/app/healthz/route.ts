// Liveness probe for the web container (ALB target group + compose healthcheck).
// Deliberately not under /api: that prefix belongs to the FastAPI service.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" });
}
