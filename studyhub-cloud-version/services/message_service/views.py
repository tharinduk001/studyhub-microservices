import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseServerError
from . models import Message
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.db.utils import OperationalError

from services.room_service.models import Room

logger = logging.getLogger(__name__)


@login_required
def room(request, pk):
    try:
        room = Room.objects.get(id=pk)
        room_messages = room.message_set.all().order_by('-created')
        members = room.participants.all()

        if request.method == 'POST':
            new_msg = request.POST.get('body')

            if new_msg != '':
                Message.objects.create(
                    user=request.user,
                    room=room,
                    body=new_msg
                )
                room.participants.add(request.user)
                request.log_tag = "ROOM_SUCCESS"
                return redirect('room', pk=room.id)
            else:
                request.log_tag = "INVALID_REQUEST"
                context = {'room': room, 'room_messages': room_messages, 'members': members}
                return render(request, 'message_service/room.html', context, status=400)

        request.log_tag = "ROOM_ACCESSED"
        context = {'room': room, 'room_messages': room_messages, 'members': members}
        return render(request, 'message_service/room.html', context)
    except OperationalError:
        request.log_tag = "ROOM_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"ROOM_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


@login_required
def deleteMessage(request, pk):
    try:
        msg = Message.objects.get(id=pk)
        room = msg.room
        current_user = request.user

        if request.user != msg.user:
            request.log_tag = "FORBIDDEN_ACCESS"
            return HttpResponse("<h1>Forbidden 403!</h1>", status=403)

        if request.method == 'DELETE':
            msg.delete()

            count = Message.objects.filter(room=room, user=current_user).count()
            if count == 0:
                room.participants.remove(current_user)

            messages.success(request, "Message Deleted Successfully!")
            request.log_tag = "DELETEMESSAGE_SUCCESS"
            return redirect('room', pk=room.pk)

        request.log_tag = "DELETEMESSAGE_ACCESSED"
        context = {'msg': msg, 'room': room}
        return render(request, 'message_service/message_delete.html', context)
    except OperationalError:
        request.log_tag = "DELETEMESSAGE_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"DELETEMESSAGE_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")
