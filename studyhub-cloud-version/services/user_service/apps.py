from django.apps import AppConfig


class UserServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'services.user_service'
    label = 'user_service'

    def ready(self):
        import services.user_service.signals
