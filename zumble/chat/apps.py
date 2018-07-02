from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = 'chat'

    def ready(self):
        from .utils import redis_load_user_data
        # load users to redis
        redis_load_user_data()
