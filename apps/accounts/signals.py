from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver

from .models import User


@receiver(user_logged_in)
def enforce_single_session(sender, request, user, **kwargs):
    """Only one active session per account: a new login ends the previous one."""
    new_key = request.session.session_key
    old_key = user.active_session_key
    if old_key and old_key != new_key:
        Session.objects.filter(session_key=old_key).delete()
    User.objects.filter(pk=user.pk).update(active_session_key=new_key or "")
    user.active_session_key = new_key or ""
