from django.db import models


class Message(models.Model):
    room_id = models.BigIntegerField()
    user_id = models.BigIntegerField()
    username = models.CharField(max_length=150)
    body = models.TextField()
    created = models.FloatField()

    def public(self) -> dict:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "username": self.username,
            "body": self.body,
            "created": self.created,
        }
