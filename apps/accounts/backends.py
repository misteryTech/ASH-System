from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")
        if username is None or password is None:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = (
                User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username))
                .order_by("id")
                .first()
            )

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
