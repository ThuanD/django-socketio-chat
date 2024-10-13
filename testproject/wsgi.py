import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproject.settings')
django.setup()

from socketio import WSGIApp  # NOQA NOSONAR
from django.core.wsgi import get_wsgi_application  # NOQA NOSONAR
from django_socketio_chat.server import ChatServer  # NOQA NOSONAR

application = WSGIApp(ChatServer().sio, get_wsgi_application())
