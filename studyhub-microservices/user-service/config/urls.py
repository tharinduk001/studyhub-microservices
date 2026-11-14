from django.urls import path

from api import views

urlpatterns = [
    path("health", views.health),
    path("auth/register", views.register),
    path("auth/login", views.login),
    path("auth/logout", views.logout),
    path("users", views.list_users),
    path("users/me", views.me),
    path("users/<int:user_id>", views.get_user),
]
