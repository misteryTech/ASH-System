from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from .models import User


class SingleSessionMiddleware:
    """Log out any session that is no longer the account's active session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            session_key = request.session.session_key
            if not user.active_session_key:
                # Sessions created before this feature existed: adopt the current one.
                User.objects.filter(pk=user.pk).update(active_session_key=session_key)
            elif user.active_session_key != session_key:
                logout(request)
                messages.warning(
                    request, "You were signed out because this account was logged in on another device."
                )
                return redirect("accounts:login")
        return self.get_response(request)
