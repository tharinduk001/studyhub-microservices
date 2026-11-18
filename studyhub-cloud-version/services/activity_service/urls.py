from django.urls import path
from . views import activityView

urlpatterns = [
    path('activities/', activityView, name = 'activity-view'),
]
