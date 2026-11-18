from django.urls import path
from . views import *

urlpatterns = [
    path('room/<int:pk>/', room, name = 'room'),

    path('delete-message/<int:pk>/', deleteMessage, name = 'delete-message'),
]
