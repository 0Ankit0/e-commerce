"""
ASGI config for project.

It exposes the ASGI callable as a module-level variable named ``application``.
Supports both HTTP (REST API) and WebSocket connections.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from config.routing import application as ws_application  # noqa

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ws_application.get("websocket"),
    }
)
