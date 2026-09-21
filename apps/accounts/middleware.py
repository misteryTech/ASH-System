from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

from .models import User

ACTIVITY_WRITE_INTERVAL = timedelta(seconds=60)


class SingleSessionMiddleware:
    """Keep one live session per account and track its last activity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            session_key = request.session.session_key
            now = timezone.now()
            if not user.active_session_key:
                # Sessions created before this feature existed: adopt the current one.
                User.objects.filter(pk=user.pk).update(active_session_key=session_key, last_activity=now)
            elif user.active_session_key != session_key:
                logout(request)
                messages.warning(
                    request, "You were signed out because this account was logged in on another device."
                )
                return redirect("accounts:login")
            elif not user.last_activity or now - user.last_activity > ACTIVITY_WRITE_INTERVAL:
                User.objects.filter(pk=user.pk).update(last_activity=now)
        return self.get_response(request)
