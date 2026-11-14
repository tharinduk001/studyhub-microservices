import json
import time

import requests
from django.conf import settings
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Room
from .sessionauth import current_user


def _body(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _current_user_or_401(request):
    user = current_user(request)
    if user is None:
        return None, JsonResponse({"detail": "Not logged in"}, status=401)
    return user, None


def _validate_room_body(data: dict):
    name = data.get("name") or ""
    topic = data.get("topic") or ""
    if not (1 <= len(name) <= 100):
        return None, JsonResponse({"detail": "name must be 1-100 characters"}, status=422)
    if not (1 <= len(topic) <= 50):
        return None, JsonResponse({"detail": "topic must be 1-50 characters"}, status=422)
    return {"name": name, "topic": topic, "description": data.get("description") or ""}, None


def publish_event(type_: str, user: dict, detail: str):
    """Best-effort: a broken activity-service must never break room-service."""
    try:
        requests.post(
            f"{settings.ACTIVITY_URL}/events",
            json={"type": type_, "user_id": user["user_id"], "username": user["username"], "detail": detail},
            headers={"X-Internal-Key": settings.INTERNAL_KEY},
            timeout=2,
        )
    except requests.RequestException:
        pass


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"service": "room-service", "status": "ok"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def rooms_collection(request):
    if request.method == "GET":
        q = request.GET.get("q", "")
        rooms = Room.objects.filter(Q(name__icontains=q) | Q(topic__icontains=q)).order_by("-id")
        return JsonResponse([r.public() for r in rooms], safe=False)

    payload, error = _current_user_or_401(request)
    if error:
        return error

    body, error = _validate_room_body(_body(request))
    if error:
        return error

    room = Room.objects.create(
        name=body["name"],
        description=body["description"],
        topic=body["topic"],
        host_id=payload["user_id"],
        host_name=payload["username"],
        created=time.time(),
    )
    publish_event("room_created", payload, f"created room '{room.name}'")
    return JsonResponse(room.public(), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def room_detail(request, room_id):
    room = Room.objects.filter(id=room_id).first()
    if not room:
        return JsonResponse({"detail": "Room not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(room.public())

    payload, error = _current_user_or_401(request)
    if error:
        return error
    if room.host_id != payload["user_id"]:
        return JsonResponse({"detail": "Only the host can edit this room"}, status=403)

    if request.method == "PUT":
        body, error = _validate_room_body(_body(request))
        if error:
            return error
        room.name, room.topic, room.description = body["name"], body["topic"], body["description"]
        room.save()
        return JsonResponse(room.public())

    room.delete()
    return JsonResponse(None, status=204, safe=False)


@require_http_methods(["GET"])
def list_topics(request):
    topics = Room.objects.values("topic").annotate(rooms=Count("id")).order_by("-rooms")
    return JsonResponse([{"name": t["topic"], "rooms": t["rooms"]} for t in topics], safe=False)
