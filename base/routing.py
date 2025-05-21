from django.urls import re_path
from . import consumers

# Debug print
print("Loading WebSocket routing patterns...")

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]

print(f"WebSocket patterns loaded: {websocket_urlpatterns}")
