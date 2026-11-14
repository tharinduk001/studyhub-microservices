from django.db import models


class Notification(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    message = models.CharField(max_length=300)
    is_read = models.BooleanField(default=False)
    created = models.FloatField()

    def public(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message": self.message,
            "is_read": int(self.is_read),
            "created": self.created,
        }
