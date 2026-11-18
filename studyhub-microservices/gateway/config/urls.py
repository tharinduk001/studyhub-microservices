from django.urls import path, re_path

from api import views

urlpatterns = [
    path("", views.index),
    path("health", views.health),
    re_path(r"^api/(?P<resource>[a-z-]+)(?:/(?P<path>.*))?$", views.proxy),
]
