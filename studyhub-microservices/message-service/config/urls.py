from django.urls import path

from api import views

urlpatterns = [
    path("health", views.health),
    path("messages", views.messages_collection),
    path("messages/<int:message_id>", views.message_detail),
]
