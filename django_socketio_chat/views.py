from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from rest_framework_simplejwt.tokens import AccessToken

from .adapter import CustomUserAdapter

User = get_user_model()


class ChatView(TemplateView):
    template_name = "django_socketio_chat/index.html"
    site_title = _("NOCOEM")
    site_header = _("NOCOEM")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chat_data = cache.get("CHAT_DATA", [])
        context.update({
            # "title": self.title,
            "site_title": self.site_title,
            "site_header": self.site_header,
            "token": str(AccessToken.for_user(self.request.user)),
            "users": self.get_users(),
            "chat_data": chat_data,
            "user": self.request.user,
            **(self.extra_context or {})
        })
        return context

    def get_users(self):
        return CustomUserAdapter().get_users(self.request.user)

    @method_decorator(csrf_protect)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
