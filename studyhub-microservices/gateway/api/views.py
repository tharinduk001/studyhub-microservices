import time
from collections import defaultdict, deque
from pathlib import Path

import requests
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

_hits = defaultdict(deque)  # ip -> timestamps of recent requests (in-memory rate limiter)
FORWARD_HEADERS = ("cookie", "content-type")


def _rate_limited(ip: str) -> bool:
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.RATE_LIMIT_PER_MINUTE:
        return True
    q.append(now)
    return False


def index(request):
    return FileResponse(open(Path(__file__).parent / "static" / "index.html", "rb"), content_type="text/html")


def health(request):
    services = {}
    for name, url in settings.SERVICES.items():
        try:
            services[name] = "up" if requests.get(f"{url}/health", timeout=2).status_code == 200 else "down"
        except requests.RequestException:
            services[name] = "down"
    return JsonResponse({"gateway": "up", "services": services})


@csrf_exempt
def proxy(request, resource, path=None):
    service = settings.ROUTES.get(resource)
    if not service:
        return JsonResponse({"detail": "Unknown resource"}, status=404)
    # internal endpoint: only other services may call it, never the outside world
    if resource == "activity" and (path or "").startswith("events"):
        return JsonResponse({"detail": "Not found"}, status=404)
    if _rate_limited(request.META.get("REMOTE_ADDR", "?")):
        return JsonResponse({"detail": "Too many requests"}, status=429)

    url = f"{settings.SERVICES[service]}/{resource}" + (f"/{path}" if path else "")
    headers = {k: v for k, v in request.headers.items() if k.lower() in FORWARD_HEADERS}
    try:
        r = requests.request(request.method, url, params=request.GET, data=request.body, headers=headers, timeout=10)
    except requests.RequestException:
        return JsonResponse({"detail": f"{service} unavailable"}, status=503)

    response = HttpResponse(r.content, status=r.status_code, content_type=r.headers.get("content-type"))
    # pass the (shared Redis) session cookie from user-service through to the browser
    for raw in r.raw.headers.getlist("Set-Cookie"):
        response.cookies.load(raw)
    return response
