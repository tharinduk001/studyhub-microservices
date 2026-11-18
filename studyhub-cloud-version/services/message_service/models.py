from django.db import models
from django.contrib.auth.models import User

from services.room_service.models import Room


class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.body[:3]

    class Meta:
        ordering = ['-created']
