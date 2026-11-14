from django.urls import path

from api import views

urlpatterns = [
    path("health", views.health),
    path("notifications", views.notifications_collection),
    path("notifications/count", views.unread_count),
    path("notifications/read-all", views.mark_all_read),
    path("notifications/<int:notification_id>/read", views.mark_read),
]
