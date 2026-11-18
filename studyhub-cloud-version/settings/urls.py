from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views
from services.user_service.views import CustomPasswordResetView, CustomPasswordResetConfirmView


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include('services.room_service.urls')),
    path('', include('services.message_service.urls')),
    path('', include('services.activity_service.urls')),
    path('', include('services.user_service.urls')),
    # path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    # path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name = 'user_service/reset_password_sent.html'), name='password_reset_done'),
    # path('password_reset_confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    # path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(template_name = 'user_service/reset_password_complete.html'), name='password_reset_complete'),
]

urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
