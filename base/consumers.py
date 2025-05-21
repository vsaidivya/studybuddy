import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Room

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get room_id from URL route
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Debug prints
        print(f"WebSocket connect attempt - room_id: {self.room_id}, group: {self.room_group_name}")
        print(f"Connection scope: {self.scope}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f"WebSocket connection accepted for room: {self.room_id}")

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data['message']
            user_id = data['user_id']
            room_id = data['room_id']

            print(f"Received message: {message} from user: {user_id} in room: {room_id}")

            # Save message to database
            message_obj = await self.save_message(user_id, room_id, message)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user_id': user_id,
                    'username': message_obj['username'],
                    'user_avatar': message_obj['user_avatar'],
                    'message_id': message_obj['id'],
                    'created': message_obj['created'],
                }
            )
            print(f"Message sent to group: {self.room_group_name}")
        except Exception as e:
            print(f"Error in receive: {str(e)}")
            # Send error message back to client
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        user_id = event['user_id']
        username = event['username']
        user_avatar = event['user_avatar']
        message_id = event['message_id']
        created = event['created']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user_id': user_id,
            'username': username,
            'user_avatar': user_avatar,
            'message_id': message_id,
            'created': created,
        }))

    @database_sync_to_async
    def save_message(self, user_id, room_id, message):
        user = User.objects.get(id=user_id)
        room = Room.objects.get(id=room_id)
        
        # Add user to participants
        room.participants.add(user)
        
        # Create message
        message_obj = Message.objects.create(
            user=user,
            room=room,
            body=message
        )
        
        # Handle case where avatar might be None
        avatar_url = user.avatar.url if user.avatar else '/static/images/avatar.svg'
        
        return {
            'id': message_obj.id,
            'username': user.username,
            'user_avatar': avatar_url,
            'created': message_obj.created.strftime("%b %d, %Y, %I:%M %p"),
        }
