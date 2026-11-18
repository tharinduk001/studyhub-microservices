from django.urls import path
from . views import login, logout, register, profile, profileUpdate, profileDelete

urlpatterns = [
    path('login/', login, name = 'login'),
    path('logout/', logout, name = 'logout'),
    path('register/', register, name = 'register'),

    path('profile/<str:username>/', profile, name = 'profile'),
    path('profile/<str:username>/update/', profileUpdate, name = 'profile-update'),
    path('profile/<str:username>/delete/', profileDelete, name = 'profile-delete'),
]
