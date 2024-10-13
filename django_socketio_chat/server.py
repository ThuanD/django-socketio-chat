import logging
from functools import wraps
from typing import Optional, Dict, Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.db.models import Q
from rest_framework_simplejwt.tokens import AccessToken
from socketio import Server

from .adapter import CustomUserAdapter
from .models import UserStatus, Status, Message

logger = logging.getLogger(__name__)

User = get_user_model()


class CacheKey:
    AUTH_TOKEN = "CHAT:SID_{}"
    SIDS = "CHAT:UID_{}"


class SocketEvent:
    USER_STATUS = "user_status"
    MESSAGES = "messages"
    CHAT_HISTORY = "chat_history"
    USERS = "users"
    ERROR = "error"


class ChatRoom:
    ACTIVE = "active"


class ChatServer:
    def __init__(self):
        self.sio = Server(
            async_mode="eventlet",
            cors_allowed_origins="*",
            logger=True
        )
        self.setup_events()

    def setup_events(self):
        self.sio.on('connect', self.connect)
        self.sio.on('disconnect', self.auth_required(self.disconnect))
        self.sio.on('search_users', self.auth_required(self.search_users))
        self.sio.on('get_chat_history', self.auth_required(self.get_chat_history))
        self.sio.on('send_message', self.auth_required(self.send_message))

    def auth_required(self, event_handler):
        @wraps(event_handler)
        def wrapper(sid: str, *args: Any, **kwargs: Any) -> Optional[Any]:
            token = cache.get(CacheKey.AUTH_TOKEN.format(sid)) or kwargs.get('token')
            if not token:
                return None
            user = self.get_user_from_token(token)
            if not user or not user.id:
                return None
            return event_handler(user, sid, *args, **kwargs)

        return wrapper

    @staticmethod
    def get_user_from_token(raw_token: str) -> User:
        try:
            data = AccessToken(raw_token)
            return User.objects.get(pk=data["user_id"], is_active=True)
        except Exception:
            return AnonymousUser()

    def update_status(self, user: User, status: str) -> None:
        user_status, _ = UserStatus.objects.get_or_create(user=user)
        user_status.status = status
        user_status.save()
        data = {"user_id": user.id, "status": user_status.status}
        self.sio.emit(SocketEvent.USER_STATUS, data, room=ChatRoom.ACTIVE)

    def connect(self, sid: str, environ: Dict[str, Any], auth: Dict[str, Any]) -> None:
        token = auth.get("token")
        if not token or not isinstance(token, str):
            return self.sio.disconnect(sid)

        user = self.get_user_from_token(token)
        if not user or not user.id:
            return self.sio.disconnect(sid)

        self.update_status(user, Status.ONLINE)
        cache.set(CacheKey.AUTH_TOKEN.format(sid), token)
        self.sio.enter_room(sid, ChatRoom.ACTIVE)

        sids = cache.get(CacheKey.SIDS.format(user.id), [])
        sids.append(sid)
        cache.set(CacheKey.SIDS.format(user.id), sids)

    def disconnect(self, user: User, sid: str) -> None:
        cache.delete(CacheKey.AUTH_TOKEN.format(sid))
        sids = cache.get(CacheKey.SIDS.format(user.id), [])
        if sid in sids:
            sids.remove(sid)
            cache.set(CacheKey.SIDS.format(user.id), sids)
        self.update_status(user, Status.OFFLINE)
        self.sio.leave_room(sid, ChatRoom.ACTIVE)

    def search_users(self, user: User, sid: str, data: Dict[str, Any]) -> None:
        search = data.get("search", "")
        if not isinstance(search, str):
            error_data = {"code": "search", "message": "search must be a string"}
            return self.sio.emit(SocketEvent.ERROR, error_data, to=sid)

        adapter = CustomUserAdapter()
        data = adapter.get_users(user, search=search)
        self.sio.emit(SocketEvent.USERS, data, to=sid)

    def get_chat_history(self, user: User, sid: str, data: Dict[str, Any]) -> None:
        partner_id = data.get("partner_id")
        if not isinstance(partner_id, int):
            error_data = {"code": "partner_id",
                          "message": "partner_id must be an integer"}
            return self.sio.emit(SocketEvent.ERROR, error_data, to=sid)

        partner = User.objects.filter(id=partner_id).first()
        if not partner:
            error_data = {"code": "partner_id", "message": "partner does not exist"}
            return self.sio.emit(SocketEvent.ERROR, error_data, to=sid)

        messages = Message.objects.filter(
            Q(sender_id=user.id, receiver_id=partner_id) |
            Q(sender_id=partner_id, receiver_id=user.id)
        ).order_by("-created_at")[:50]

        result = {
            "user": {"id": user.id, "username": user.username},
            "partner": {"id": partner.id, "username": partner.username},
            "messages": [
                {
                    "id": message.id.__str__(),
                    "sender_id": message.sender_id,
                    "receiver_id": message.receiver_id,
                    "content": message.content,
                    "created_at": int(message.created_at.timestamp()),
                    "sender_name": message.sender.username,
                    "receiver_name": message.receiver.username,
                    "is_read": message.is_read,
                }
                for message in reversed(messages)
            ]
        }
        self.sio.emit(SocketEvent.CHAT_HISTORY, result, to=sid)
        Message.objects.filter(sender_id=partner_id, receiver_id=user.id).update(
            is_read=True)

    def send_message(self, user: User, sid: str, data: Dict[str, Any]) -> None:
        partner_id = data.get("partner_id")
        if not isinstance(partner_id, int):
            error_data = {"code": "partner_id",
                          "message": "partner_id must be an integer"}
            return self.sio.emit(SocketEvent.ERROR, error_data, to=sid)

        partner = User.objects.filter(id=partner_id).first()
        if not partner:
            error_data = {"code": "partner_id", "message": "partner does not exist"}
            return self.sio.emit(SocketEvent.ERROR, error_data, to=sid)

        content = data.get("content")
        if not isinstance(content, str):
            error_data = {"code": "content", "message": "content must be a string"}
            return self.sio.emit(SocketEvent.ERROR, error_data, to=sid)

        message = Message.objects.create(
            sender_id=user.id,
            receiver_id=partner_id,
            content=content,
        )
        result = {
            "user": {"id": user.id, "username": user.username},
            "partner": {"id": partner.id, "username": partner.username},
            "message": {
                "sender_id": message.sender_id,
                "receiver_id": message.receiver_id,
                "content": message.content,
                "created_at": int(message.created_at.timestamp()),
                "sender_name": message.sender.username,
                "receiver_name": message.receiver.username,
                "is_read": message.is_read,
            }
        }

        self.sio.emit(SocketEvent.MESSAGES, result, to=sid)
        sids = cache.get(CacheKey.SIDS.format(partner_id), [])
        for sid in sids:
            self.sio.emit(SocketEvent.MESSAGES, result, to=sid)
        Message.objects.filter(receiver_id=user.id, is_read=False).update(is_read=True)
