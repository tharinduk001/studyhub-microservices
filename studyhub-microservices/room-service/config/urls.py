from django.urls import path

from api import views

urlpatterns = [
    path("health", views.health),
    path("rooms", views.rooms_collection),
    path("rooms/<int:room_id>", views.room_detail),
    path("topics", views.list_topics),
]
