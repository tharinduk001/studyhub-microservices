import json
import time

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Message
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


def fire_and_forget(url: str, payload: dict):
    """Best-effort call to a non-critical service (graceful degradation)."""
    try:
        requests.post(url, json=payload, headers={"X-Internal-Key": settings.INTERNAL_KEY}, timeout=2)
    except requests.RequestException:
        pass


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"service": "message-service", "status": "ok"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def messages_collection(request):
    if request.method == "GET":
        room_id = request.GET.get("room_id")
        limit = int(request.GET.get("limit", 100))
        messages = Message.objects.all()
        if room_id is not None:
            messages = messages.filter(room_id=room_id)
        messages = messages.order_by("-id")[:limit]
        return JsonResponse([m.public() for m in messages], safe=False)

    payload, error = _current_user_or_401(request)
    if error:
        return error

    data = _body(request)
    room_id = data.get("room_id")
    body = data.get("body") or ""
    if room_id is None or not (1 <= len(body) <= 2000):
        return JsonResponse({"detail": "room_id and body (1-2000 chars) are required"}, status=422)

    # 1. Critical dependency: the room must exist (synchronous call to room-service)
    try:
        r = requests.get(f"{settings.ROOM_URL}/rooms/{room_id}", timeout=3)
    except requests.RequestException:
        return JsonResponse({"detail": "room-service unavailable"}, status=503)
    if r.status_code == 404:
        return JsonResponse({"detail": "Room not found"}, status=404)
    room = r.json()

    message = Message.objects.create(
        room_id=room_id, user_id=payload["user_id"], username=payload["username"], body=body, created=time.time()
    )

    # 2. Non-critical side effects: notify the room host, record activity
    if room.get("host_id") != payload["user_id"]:
        fire_and_forget(
            f"{settings.NOTIFICATION_URL}/notifications",
            {"user_id": room["host_id"], "message": f"{payload['username']} posted in '{room['name']}'"},
        )
    fire_and_forget(
        f"{settings.ACTIVITY_URL}/events",
        {
            "type": "message_posted",
            "user_id": payload["user_id"],
            "username": payload["username"],
            "detail": f"posted in '{room['name']}'",
        },
    )
    return JsonResponse(message.public(), status=201)


@csrf_exempt
@require_http_methods(["DELETE"])
def message_detail(request, message_id):
    payload, error = _current_user_or_401(request)
    if error:
        return error

    message = Message.objects.filter(id=message_id).first()
    if not message:
        return JsonResponse({"detail": "Message not found"}, status=404)
    if message.user_id != payload["user_id"]:
        return JsonResponse({"detail": "You can only delete your own messages"}, status=403)

    message.delete()
    return JsonResponse(None, status=204, safe=False)
