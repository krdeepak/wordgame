from .models import Score
from .redis_connect import redis_conn


def redis_load_user_data():
    for score in Score.objects.all():
        redis_conn.zadd('leaderboard', score.points, score.user.username)
