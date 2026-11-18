from django.db import models


class Event(models.Model):
    type = models.CharField(max_length=50)
    user_id = models.BigIntegerField()
    username = models.CharField(max_length=150)
    detail = models.CharField(max_length=300, blank=True, default="")
    created = models.FloatField()

    def public(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "user_id": self.user_id,
            "username": self.username,
            "detail": self.detail,
            "created": self.created,
        }
