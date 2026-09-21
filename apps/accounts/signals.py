from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone

from .models import User


@receiver(user_logged_in)
def claim_account_session(sender, request, user, **kwargs):
    """Record this session as the account's active one.

    Login forms already refuse a second live session; if one slips through (e.g. the
    previous session was idle), the old session is ended here.
    """
    new_key = request.session.session_key or ""
    old_key = user.active_session_key
    if old_key and old_key != new_key:
        Session.objects.filter(session_key=old_key).delete()
    now = timezone.now()
    User.objects.filter(pk=user.pk).update(active_session_key=new_key, last_activity=now)
    user.active_session_key = new_key
    user.last_activity = now


@receiver(user_logged_out)
def release_account_session(sender, request, user, **kwargs):
    """Free the account so it can log in elsewhere right after logging out."""
    if user is not None and request is not None:
        User.objects.filter(pk=user.pk, active_session_key=request.session.session_key).update(
            active_session_key=""
        )
