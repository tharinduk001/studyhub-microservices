"""api-gateway (port 8000) - the single entry point for clients.
Routes /api/<resource>/... to the owning microservice, aggregates health, serves the web UI.
"""
import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

SERVICES = {
    "user-service": os.getenv("USER_URL", "http://127.0.0.1:8001"),
    "room-service": os.getenv("ROOM_URL", "http://127.0.0.1:8002"),
    "message-service": os.getenv("MESSAGE_URL", "http://127.0.0.1:8003"),
    "notification-service": os.getenv("NOTIFICATION_URL", "http://127.0.0.1:8004"),
    "activity-service": os.getenv("ACTIVITY_URL", "http://127.0.0.1:8005"),
}

# first path segment after /api/  ->  owning service
ROUTES = {
    "auth": "user-service",
    "users": "user-service",
    "rooms": "room-service",
    "topics": "room-service",
    "messages": "message-service",
    "notifications": "notification-service",
    "activity": "activity-service",
}

app = FastAPI(title="API Gateway", description="Single entry point for all microservices")


@app.get("/health")
async def health():
    result = {}
    async with httpx.AsyncClient(timeout=2) as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(f"{url}/health")
                result[name] = "up" if r.status_code == 200 else "down"
            except httpx.HTTPError:
                result[name] = "down"
    return {"gateway": "up", "services": result}


@app.api_route("/api/{resource}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/api/{resource}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(resource: str, request: Request, path: str = ""):
    service = ROUTES.get(resource)
    if not service:
        return Response('{"detail":"Unknown resource"}', status_code=404, media_type="application/json")
    # internal endpoints must never be reachable from outside the gateway
    if resource == "activity" and path.startswith("events"):
        return Response('{"detail":"Not found"}', status_code=404, media_type="application/json")
    url = f"{SERVICES[service]}/{resource}" + (f"/{path}" if path else "")
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("authorization", "content-type")}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.request(
                request.method, url, params=request.query_params, content=await request.body(), headers=headers
            )
    except httpx.HTTPError:
        return Response(
            f'{{"detail":"{service} unavailable"}}', status_code=503, media_type="application/json"
        )
    return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type"))


# web UI (must be mounted last)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="ui")
