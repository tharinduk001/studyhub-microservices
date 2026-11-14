from django.db import models


class AppUser(models.Model):
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField()
    password_hash = models.CharField(max_length=255)
    bio = models.CharField(max_length=300, blank=True, default="")
    created = models.FloatField()

    def public(self) -> dict:
        return {"id": self.id, "username": self.username, "email": self.email, "bio": self.bio}
