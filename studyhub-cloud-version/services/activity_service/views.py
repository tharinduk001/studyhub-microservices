import logging
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError
from django.db.utils import OperationalError

from services.message_service.models import Message

logger = logging.getLogger(__name__)


def activityView(request):
    try:
        activities = Message.objects.all()
        request.log_tag = "ACTIVITYVIEW_ACCESSED"
        context = {'activities': activities}
        return render(request, 'activity_service/activity.html', context)
    except OperationalError:
        request.log_tag = "ACTIVITYVIEW_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"ACTIVITYVIEW_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")
