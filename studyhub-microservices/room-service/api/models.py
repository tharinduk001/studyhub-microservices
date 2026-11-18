from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    topic = models.CharField(max_length=50)
    host_id = models.BigIntegerField()
    host_name = models.CharField(max_length=150)
    created = models.FloatField()

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "topic": self.topic,
            "host_id": self.host_id,
            "host_name": self.host_name,
            "created": self.created,
        }
