import json
import time

from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import AppUser
from .sessionauth import current_user, log_in, log_out


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
    return JsonResponse({"service": "user-service", "status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    data = _body(request)
    username = (data.get("username") or "").strip().lower()
    email = data.get("email")
    password = data.get("password") or ""

    if not (3 <= len(username) <= 30):
        return JsonResponse({"detail": "username must be 3-30 characters"}, status=422)
    if not email:
        return JsonResponse({"detail": "email is required"}, status=422)
    if len(password) < 6:
        return JsonResponse({"detail": "password must be at least 6 characters"}, status=422)

    try:
        user = AppUser.objects.create(
            username=username, email=email, password_hash=make_password(password), created=time.time()
        )
    except IntegrityError:
        return JsonResponse({"detail": "Username already taken"}, status=409)

    log_in(request, user)
    return JsonResponse({"user": user.public()}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    data = _body(request)
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    user = AppUser.objects.filter(username=username).first()
    if not user or not check_password(password, user.password_hash):
        return JsonResponse({"detail": "Invalid username or password"}, status=401)

    log_in(request, user)
    return JsonResponse({"user": user.public()})


@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    log_out(request)
    return JsonResponse({"detail": "Logged out"})


@require_http_methods(["GET"])
def list_users(request):
    return JsonResponse([u.public() for u in AppUser.objects.order_by("id")], safe=False)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def me(request):
    payload, error = _current_user_or_401(request)
    if error:
        return error

    user = AppUser.objects.filter(id=payload["user_id"]).first()
    if not user:
        return JsonResponse({"detail": "User not found"}, status=404)

    if request.method == "PUT":
        data = _body(request)
        if data.get("email") is not None:
            user.email = data["email"]
        if data.get("bio") is not None:
            user.bio = data["bio"][:300]
        user.save()

    return JsonResponse(user.public())


@require_http_methods(["GET"])
def get_user(request, user_id):
    user = AppUser.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"detail": "User not found"}, status=404)
    return JsonResponse(user.public())
