import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseServerError, HttpResponseForbidden
from . forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm, SafePasswordResetForm
from django.contrib import messages
from django.contrib.auth.models import User, auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views

from django.db import transaction
from django.db.utils import OperationalError
from botocore.exceptions import ClientError

from services.message_service.models import Message
from services.room_service.models import Topic

logger = logging.getLogger(__name__)


def csrf_failure(request, reason=""):
    """
    Custom CSRF failure handler, wired up via CSRF_FAILURE_VIEW in settings.py.
    Django calls this instead of returning its default 403 page whenever
    CsrfViewMiddleware rejects a request. Setting request.log_tag here lets
    RequestLoggingMiddleware pick it up and emit it in the standard
    TAG "METHOD path" status log format, same as every other view.
    """
    request.log_tag = "CSRF_FAILURE"
    return HttpResponseForbidden("<h1>Forbidden 403!</h1>")


def login(request):
    if request.user.is_authenticated:
        messages.info(request, "You Have Already Loged-In!")
        request.log_tag = "LOGIN_FINISHED"
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            auth_user = auth.authenticate(username=username, password=password)
        except OperationalError:
            request.log_tag = "LOGIN_FAILED: database unavailable"
            return HttpResponse("Service Unavailable", status=503)
        except Exception as e:
            request.log_tag = f"LOGIN_FAILED: {str(e)}"
            return HttpResponseServerError("Internal Server Error")

        if auth_user is not None:
            auth.login(request, auth_user)
            messages.success(request, "Successfully Loged-In!")
            request.log_tag = "LOGIN_SUCCESS"
            return redirect('home')
        else:
            messages.error(request, "User Doesn't Exist!")
            request.log_tag = "INVALID_REQUEST"
            return render(request, 'user_service/login.html', status=401)

    request.log_tag = "LOGIN_ACCESSED"
    return render(request, 'user_service/login.html')


def logout(request):
    if not (request.user.is_authenticated):
        messages.info(request, "You Have Not Loged-In!")
        request.log_tag = "LOGOUT_FINISHED"
        return redirect('home')

    username = request.user.username
    try:
        auth.logout(request)
    except OperationalError:
        request.log_tag = "LOGOUT_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"LOGOUT_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")

    messages.success(request, "Successfully Loged Out!")
    request.log_tag = "LOGOUT_SUCCESS"
    return redirect('home')


def register(request):
    form = UserRegistrationForm()
    status_code = 200

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            try:
                new_user = form.save(commit=False)
                new_user.username = new_user.username.lower()
                new_user.save()
            except OperationalError:
                request.log_tag = "REGISTER_FAILED: database unavailable"
                return HttpResponse("Service Unavailable", status=503)
            except Exception as e:
                request.log_tag = f"REGISTER_FAILED: {str(e)}"
                return HttpResponseServerError("Internal Server Error")

            messages.success(request, "Account Created Successfully!")
            auth.login(request, new_user)
            request.log_tag = "REGISTER_SUCCESS"
            return redirect('home')
        else:
            request.log_tag = "INVALID_REQUEST"
            status_code = 400

    if not hasattr(request, 'log_tag'):
        request.log_tag = "REGISTER_ACCESSED"
    context = {'form': form}
    return render(request, 'user_service/register.html', context, status=status_code)


def profile(request, username):
    try:
        current_user = User.objects.get(username=username)
        rooms = current_user.room_set.all()
        activities = Message.objects.all()
        topics = Topic.objects.all()

        request.log_tag = "PROFILE_ACCESSED"
        context = {'current_user': current_user, 'rooms': rooms, 'activities': activities, 'topics': topics}
        return render(request, 'user_service/profile.html', context)
    except OperationalError:
        request.log_tag = "PROFILE_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"PROFILE_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


@login_required
def profileUpdate(request, username):
    status_code = 200
    try:
        current_user = User.objects.get(username=username)
        if current_user != request.user:
            request.log_tag = "FORBIDDEN_ACCESS"
            return HttpResponse("<h1>Forbidden 403!</h1>", status=403)

        form = UserUpdateForm(instance=current_user)
        p_form = ProfileUpdateForm(instance=current_user.profile)

        if request.method == 'PUT':
            form = UserUpdateForm(request.POST, instance=current_user)
            p_form = ProfileUpdateForm(request.POST, request.FILES, instance=current_user.profile)

            if form.is_valid() and p_form.is_valid():
                try:
                    with transaction.atomic():
                        alt_user = form.save(commit=False)
                        alt_user.username = alt_user.username.lower()
                        alt_user.save()
                        p_form.save()
                except ClientError:
                    request.log_tag = "PROFILEUPDATE_FAILED: storage unavailable"
                    return HttpResponse("Bad Gateway", status=502)
                except OperationalError:
                    request.log_tag = "PROFILEUPDATE_FAILED: database unavailable"
                    return HttpResponse("Service Unavailable", status=503)

                messages.success(request, "Profile Updated Successfully!")
                request.log_tag = "PROFILEUPDATE_SUCCESS"
                return redirect('profile', username=alt_user.username)
            else:
                request.log_tag = "INVALID_REQUEST"
                status_code = 400

        if not hasattr(request, 'log_tag'):
            request.log_tag = "PROFILEUPDATE_ACCESSED"
        context = {'current_user': current_user, 'form': form, 'p_form': p_form}
        return render(request, 'user_service/profile_update.html', context, status=status_code)
    except OperationalError:
        request.log_tag = "PROFILEUPDATE_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"PROFILEUPDATE_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


@login_required
def profileDelete(request, username):
    try:
        current_user = User.objects.get(username=username)
        if request.user != current_user:
            request.log_tag = "FORBIDDEN_ACCESS"
            return HttpResponse("<h1>Forbidden 403!</h1>", status=403)

        if request.method == 'DELETE':
            current_user.delete()
            messages.success(request, "Account Deleted Successfully!")
            request.log_tag = "PROFILEDELETE_SUCCESS"
            return redirect('home')

        request.log_tag = "PROFILEDELETE_ACCESSED"
        context = {'current_user': current_user}
        return render(request, 'user_service/profile_delete.html', context)
    except OperationalError:
        request.log_tag = "PROFILEDELETE_FAILED: database unavailable"
        return HttpResponse("Service Unavailable", status=503)
    except Exception as e:
        request.log_tag = f"PROFILEDELETE_FAILED: {str(e)}"
        return HttpResponseServerError("Internal Server Error")


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'user_service/reset_password.html'
    form_class = SafePasswordResetForm

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except OperationalError:
            self.request.log_tag = "PASSWORDRESET_FAILED: database unavailable"
            return HttpResponse("Service Unavailable", status=503)
        except RuntimeError:
            self.request.log_tag = "PASSWORDRESET_EMAIL_FAILED"
            return HttpResponseServerError("<h1>Internal Server Error 500!</h1>")
        except Exception as e:
            self.request.log_tag = f"PASSWORDRESET_FAILED: {str(e)}"
            return HttpResponseServerError("Internal Server Error")
        self.request.log_tag = "PASSWORDRESET_ACCESSED"
        return response

    def form_invalid(self, form):
        self.request.log_tag = "INVALID_REQUEST"
        response = super().form_invalid(form)
        response.status_code = 400
        return response


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'user_service/reset_password_confirm.html'

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except OperationalError:
            self.request.log_tag = "PASSWORDRESETCONFIRM_FAILED: database unavailable"
            return HttpResponse("Service Unavailable", status=503)
        except Exception as e:
            self.request.log_tag = f"PASSWORDRESETCONFIRM_FAILED: {str(e)}"
            return HttpResponseServerError("Internal Server Error")
        self.request.log_tag = "PASSWORDRESETCONFIRM_ACCESSED"
        return response

    def form_invalid(self, form):
        self.request.log_tag = "INVALID_REQUEST"
        response = super().form_invalid(form)
        response.status_code = 400
        return response
