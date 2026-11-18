import json
import time

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Notification
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


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"service": "notification-service", "status": "ok"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def notifications_collection(request):
    """POST = internal create (message-service). GET = the logged-in user's notifications."""
    if request.method == "POST":
        if request.headers.get("X-Internal-Key") != settings.INTERNAL_KEY:
            return JsonResponse({"detail": "Internal endpoint"}, status=403)
        data = _body(request)
        if data.get("user_id") is None or not data.get("message"):
            return JsonResponse({"detail": "user_id and message are required"}, status=422)
        n = Notification.objects.create(user_id=data["user_id"], message=data["message"][:300], created=time.time())
        return JsonResponse({"id": n.id}, status=201)

    user, error = _current_user_or_401(request)
    if error:
        return error
    items = Notification.objects.filter(user_id=user["user_id"])
    if request.GET.get("unread_only") in ("1", "true", "True"):
        items = items.filter(is_read=False)
    return JsonResponse([n.public() for n in items.order_by("-id")], safe=False)


@require_http_methods(["GET"])
def unread_count(request):
    user, error = _current_user_or_401(request)
    if error:
        return error
    return JsonResponse({"unread": Notification.objects.filter(user_id=user["user_id"], is_read=False).count()})


@csrf_exempt
@require_http_methods(["POST"])
def mark_all_read(request):
    user, error = _current_user_or_401(request)
    if error:
        return error
    updated = Notification.objects.filter(user_id=user["user_id"], is_read=False).update(is_read=True)
    return JsonResponse({"updated": updated})


@csrf_exempt
@require_http_methods(["POST"])
def mark_read(request, notification_id):
    user, error = _current_user_or_401(request)
    if error:
        return error
    updated = Notification.objects.filter(id=notification_id, user_id=user["user_id"]).update(is_read=True)
    if not updated:
        return JsonResponse({"detail": "Notification not found"}, status=404)
    return JsonResponse({"id": notification_id, "is_read": 1})
