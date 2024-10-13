import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Status(models.IntegerChoices):
    OFFLINE = 0, _("Offline")
    ONLINE = 1, _("Online")
    AWAY = 2, _("Away")
    BUSY = 3, _("Busy")


class UserStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="status")
    status = models.IntegerField(choices=Status.choices, default=Status.OFFLINE)
    last_changed = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_status"


class ChatGroup(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(User, related_name="chat_groups")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_group"


class MessageType(models.IntegerChoices):
    TEXT = 1, _("Text")
    IMAGE = 2, _("Image")
    FILE = 3, _("File")
    AUDIO = 4, _("Audio")
    VIDEO = 5, _("Video")


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name="received_messages", null=True,
                                 blank=True)
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE,
                              related_name="messages", null=True, blank=True)
    content = models.TextField()
    message_type = models.IntegerField(choices=MessageType.choices,
                                       default=MessageType.TEXT)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message"
        indexes = [
            models.Index(fields=["sender", "receiver", "is_read"]),
        ]
