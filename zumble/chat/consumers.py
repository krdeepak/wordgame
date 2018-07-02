from django.conf import settings
from asyncio import sleep
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from .redis_connect import redis_conn

from chat.models import Room

##### Project-specific settings

NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS = True

MSG_TYPE_MESSAGE = 0  # For standard messages
MSG_TYPE_WARNING = 1  # For yellow messages
MSG_TYPE_ALERT = 2  # For red & dangerous alerts
MSG_TYPE_MUTED = 3  # For just OK information that doesn't bother users
MSG_TYPE_ENTER = 4  # For just OK information that doesn't bother users
MSG_TYPE_LEAVE = 5  # For just OK information that doesn't bother users

MSG_SERVER_QUESTION = 102
MSG_SERVER_RIGHT_ANSWER_SELF = 103
MSG_SERVER_WRONG_ANSWER = 104
MSG_SERVER_RIGHT_ANSWER_OTHER = 105
MSG_SERVER_ANSWER_ECHO = 106

MESSAGE_TYPES_CHOICES = (
    (MSG_TYPE_MESSAGE, 'MESSAGE'),
    (MSG_TYPE_WARNING, 'WARNING'),
    (MSG_TYPE_ALERT, 'ALERT'),
    (MSG_TYPE_MUTED, 'MUTED'),
    (MSG_TYPE_ENTER, 'ENTER'),
    (MSG_TYPE_LEAVE, 'LEAVE'),
)

MESSAGE_TYPES_LIST = [
    MSG_TYPE_MESSAGE,
    MSG_TYPE_WARNING,
    MSG_TYPE_ALERT,
    MSG_TYPE_MUTED,
    MSG_TYPE_ENTER,
    MSG_TYPE_LEAVE,
]


class AnswerConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
        else:
            await self.accept()

        self.rooms = set()

    async def receive_json(self, content, **kwargs):
        user_name = self.scope['user'].username
        user_id = self.scope['user'].id

        command = content.get('command', None)
        try:
            room_id = content['room']

            if command == 'join':
                await self.join_room(content['room'])
                current_question = redis_conn.get('jumble_question')
                leaderboard = redis_conn.zrevrange('leaderboard', 0, 10, withscores=True)
                my_score = await database_sync_to_async(self.get_user_score)(room_id, user_id)

                await self.send_json(
                    {
                        'room': room_id,
                        'message': current_question,
                        'username': 'jumble',
                        'msg_type': MSG_SERVER_QUESTION,
                        'leaderboard': leaderboard,
                        'my_score': my_score,
                    }
                )

            elif command == 'leave':
                await self.leave_room(content['room'])

            elif command == 'send':
                await self.send_json(
                    {
                        "msg_type": MSG_SERVER_ANSWER_ECHO,
                        "room": room_id,
                        "username": 'jumble',
                        "message": content['message'],
                    },
                )
                # room = await database_sync_to_async(self.get_room)(room_id)
                current_answer = redis_conn.get('jumble_answer')
                if current_answer == content['message']:

                    await database_sync_to_async(self.save_winner)(room_id, user_id)

                    my_score = await database_sync_to_async(self.get_user_score)(room_id, user_id)
                    leaderboard = redis_conn.zrevrange('leaderboard', 0, 10, withscores=True)
                    await self.send_json(
                        {
                            "msg_type": MSG_SERVER_RIGHT_ANSWER_SELF,
                            "room": room_id,
                            "username": 'jumble',
                            "message": "{} is correct".format(current_answer),
                            "leaderboard": leaderboard,
                            'my_score': my_score,
                        },
                    )
                    # send update to room that someone took position p
                    await self.send_room(
                        room_id,
                        '{} - correct answer by {}'.format(current_answer.upper(), user_name),
                        MSG_SERVER_RIGHT_ANSWER_OTHER,
                        leaderboard=leaderboard,
                        my_score=my_score
                    )

                    room = await database_sync_to_async(self.get_room)(room_id)
                    await database_sync_to_async(room.publish_new_question)()

                else:
                    await self.send_json(
                        {
                            "msg_type": MSG_SERVER_WRONG_ANSWER,
                            "room": room_id,
                            "username": 'jumble',
                            "message": "wrong",
                        },
                    )
                # await self.send_room(content['room'], content['message'], MSG_TYPE_MESSAGE)
        except Exception as e:
            print(e)
            await self.send_json({'error': str(e)})

    async def disconnect(self, code):
        for room_id in list(self.rooms):
            try:
                await self.leave_room(room_id)
            except Exception as e:
                pass

    async def join_room(self, room_id):
        self.rooms.add(room_id)

        room = await database_sync_to_async(self.get_room)(room_id)

        await self.channel_layer.group_add(room.name, self.channel_name)

        await self.send_json({
            'join': str(room_id),
            'title': room.name,
        })

    async def leave_room(self, room_id):
        self.rooms.discard(room_id)

        room = await database_sync_to_async(self.get_room)(room_id)

        # Remove them from the group so they no longer get room messages
        await self.channel_layer.group_discard(
            room.name,
            self.channel_name,
        )

        await self.send_json({
            'leave': str(room_id)
        })

    async def send_room(self, room_id, message, message_type, leaderboard='', my_score=''):
        room = await database_sync_to_async(self.get_room)(room_id)

        await self.channel_layer.group_send(
            room.name,
            {
                'type': 'chat.message',
                'room_id': room_id,
                'message': message,
                'username': self.scope['user'].username,
                'message_type': message_type,
                'leaderboard': leaderboard,
                'my_score': my_score,
            }
        )

    async def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """

        live_users = redis_conn.zcard('asgi3::group:medium')

        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": event['message_type'],
                "room": event["room_id"],
                "username": event["username"],
                "message": event["message"],
                "leaderboard": event["leaderboard"],
                "live_users": live_users,
            },
        )

    def get_room(self, room_id):
        return Room.objects.get(pk=room_id)

    def save_winner(self, room_id, user_id):
        room = Room.objects.get(pk=room_id)
        room.save_winner(user_id)

    def get_user_score(self, room_id, user_id):
        room = self.get_room(room_id)
        return room.user_score_for_user_id(user_id)
