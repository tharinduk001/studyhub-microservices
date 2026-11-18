import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseServerError
from . models import Topic, Room
from . forms import RoomForm
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from django.db import connections
from django.db.utils import OperationalError

from services.message_service.models import Message

logger = logging.getLogger(__name__)


def home(request):
    try:
        q = request.GET.get('q') if request.GET.get('q') else ''

        rooms = Room.objects.distinct().filter(
            Q(topic__name__icontains=q) |
            Q(name__icontains=q)
        )
        rooms_count = rooms.count()
        topics = Topic.objects.all()[:5]
        activities = Message.objects.all()

        request.log_tag = "HOME_SEARCH" if q else "HOME_ACCESSED"

        context = {'rooms': rooms, 'topics': topics, 'rooms_count': rooms_count, 'activities': activities}
        return render(request, 'room_service/index.html', context)
    except OperationalError:
        request.log_tag = "HOME_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"HOME_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


@login_required
def createRoom(request):
    topics = Topic.objects.all()
    form = RoomForm()
    status_code = 200

    if request.method == 'POST':
        form = RoomForm(request.POST)

        if form.is_valid():
            try:
                new_room = form.save(commit=False)
                new_room.host = request.user

                topic_name = request.POST.get('topic')
                topic, created = Topic.objects.get_or_create(name=topic_name)
                new_room.topic = topic
                new_room.save()
            except OperationalError:
                request.log_tag = "CREATEROOM_FAILED: database unavailable"
                return HttpResponse("Service Unavailable", status=503)
            except Exception as e:
                request.log_tag = f"CREATEROOM_FAILED: {str(e)}"
                return HttpResponseServerError("Internal Server Error")

            messages.success(request, "Room Created Successfully!")
            request.log_tag = "CREATEROOM_SUCCESS"
            return redirect('room', pk=new_room.pk)
        else:
            request.log_tag = "INVALID_REQUEST"
            status_code = 400

    if not hasattr(request, 'log_tag'):
        request.log_tag = "CREATEROOM_ACCESSED"
    context = {'form': form, 'topics': topics}
    return render(request, 'room_service/room_create.html', context, status=status_code)


@login_required
def updateRoom(request, pk):
    status_code = 200
    try:
        topics = Topic.objects.all()
        room = Room.objects.get(id=pk)
        current_topic = room.topic

        if request.user != room.host:
            request.log_tag = "FORBIDDEN_ACCESS"
            return HttpResponse("<h1>Forbidden 403!</h1>", status=403)

        form = RoomForm(instance=room)
        if request.method == 'PUT':
            form = RoomForm(request.POST, instance=room)

            if form.is_valid():
                alt_room = form.save(commit=False)

                topic_name = request.POST.get('topic')
                topic, created = Topic.objects.get_or_create(name=topic_name)
                alt_room.topic = topic
                alt_room.save()

                count = current_topic.room_set.all().count()
                if count == 0:
                    current_topic.delete()

                messages.success(request, "Room Updated Successfully!")
                request.log_tag = "UPDATEROOM_SUCCESS"
                return redirect('room', pk=room.pk)
            else:
                request.log_tag = "INVALID_REQUEST"
                status_code = 400

        if not hasattr(request, 'log_tag'):
            request.log_tag = "UPDATEROOM_ACCESSED"
        context = {'form': form, 'room': room, 'topics': topics}
        return render(request, 'room_service/room_update.html', context, status=status_code)
    except OperationalError:
        request.log_tag = "UPDATEROOM_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"UPDATEROOM_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


@login_required
def deleteRoom(request, pk):
    try:
        room = Room.objects.get(id=pk)
        current_topic = room.topic

        if request.user != room.host:
            request.log_tag = "FORBIDDEN_ACCESS"
            return HttpResponse("<h1>Forbidden 403!</h1>", status=403)

        if request.method == 'DELETE':
            room.delete()

            count = current_topic.room_set.all().count()
            if count == 0:
                current_topic.delete()

            messages.success(request, "Room Deleted Successfully!")
            request.log_tag = "DELETEROOM_SUCCESS"
            return redirect('home')

        request.log_tag = "DELETEROOM_ACCESSED"
        context = {'room': room}
        return render(request, 'room_service/room_delete.html', context)
    except OperationalError:
        request.log_tag = "DELETEROOM_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"DELETEROOM_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


def topicView(request):
    try:
        q = request.GET.get('q') if request.GET.get('q') else ''
        topics = Topic.objects.filter(
            Q(name__icontains=q)
        )[:5]

        request.log_tag = "TOPICVIEW_SEARCH" if q else "TOPICVIEW_ACCESSED"

        context = {'topics': topics}
        return render(request, 'room_service/topics.html', context)
    except OperationalError:
        request.log_tag = "TOPICVIEW_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"TOPICVIEW_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


def start(request):
    try:
        request.log_tag = "START_SUCCESS"
        return HttpResponse("Started", status=200)
    except Exception:
        request.log_tag = "START_FAILED"
        return HttpResponse("Start Failed", status=503)


def ready(request):
    for db_name in connections:
        try:
            connections[db_name].cursor()
        except OperationalError:
            request.log_tag = "READY_FAILED"
            return HttpResponse("Status: DB Down", status=503)
    request.log_tag = "READY_SUCCESS"
    return HttpResponse("Ready", status=200)


def live(request):
    try:
        request.log_tag = "LIVE_SUCCESS"
        return HttpResponse("Live", status=200)
    except Exception:
        request.log_tag = "LIVE_FAILED"
        return HttpResponse("Live Failed", status=503)
