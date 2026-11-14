from django.urls import path

from api import views

urlpatterns = [
    path("health", views.health),
    path("events", views.record_event),
    path("activity", views.feed),
    path("activity/stats", views.stats),
]
