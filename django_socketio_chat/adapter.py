from allauth_ui.adapter import DefaultUserAdapter
from django.db.models import Count, Case, When, Q, IntegerField
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from django_socketio_chat.models import Status

User = get_user_model()


class CustomUserAdapter(DefaultUserAdapter):

    def get_app_list(self, user):
        app_list = super().get_app_list(user)
        app_list.append(dict(
            name=_("Chat"),
            app_label=_("Chat"),
            app_url=reverse_lazy("account_home"),
            has_module_perms=True,
            models=[{
                "name": "Chat",
                "admin_url": reverse_lazy("chat_index"),
                "view_only": True,
            }],
        ))
        return app_list

    def get_users(self, user, search=""):
        users = User.objects.exclude(id=user.id)
        if search:
            users = users.filter(username__icontains=search)
        users = users.annotate(
            total_unread=Count("received_messages",
                               filter=Q(received_messages__receiver=user,
                                        received_messages__is_read=False)),
            status_order=Case(
                When(status__status=Status.ONLINE, then=0),
                When(status__status=Status.OFFLINE, then=1),
                default=2,
                output_field=IntegerField()
            )
        ).order_by("-status__status", "username")
        return [
            {
                "user": {
                    "id": u.id,
                    "username": u.username,
                    "status": getattr(
                        u.status, "status",Status.OFFLINE
                    ) if hasattr(u, "status") else Status.OFFLINE,
                },
                "total_unread": u.total_unread,
            }
            for u in users
        ]
