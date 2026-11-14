import json
import time

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Event


def _body(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"service": "activity-service", "status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def record_event(request):
    if request.headers.get("X-Internal-Key") != settings.INTERNAL_KEY:
        return JsonResponse({"detail": "Internal endpoint"}, status=403)

    data = _body(request)
    event = Event.objects.create(
        type=data.get("type", ""),
        user_id=data.get("user_id"),
        username=data.get("username", ""),
        detail=data.get("detail", ""),
        created=time.time(),
    )
    return JsonResponse({"id": event.id}, status=201)


@require_http_methods(["GET"])
def feed(request):
    limit = int(request.GET.get("limit", 20))
    events = Event.objects.order_by("-id")[:limit]
    return JsonResponse([e.public() for e in events], safe=False)


@require_http_methods(["GET"])
def stats(request):
    by_type = {r["type"]: r["n"] for r in Event.objects.values("type").annotate(n=Count("id"))}
    top = list(
        Event.objects.values("username").annotate(events=Count("id")).order_by("-events")[:5]
    )
    return JsonResponse({"total_events": sum(by_type.values()), "by_type": by_type, "most_active_users": top})
