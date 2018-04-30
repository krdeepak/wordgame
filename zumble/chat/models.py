import random

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User
from django.db.models import ObjectDoesNotExist
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from chat.words import words


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Room(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    scoring_positions = models.PositiveSmallIntegerField(default=1)
    """ max scoring positions for the puzzle """

    scoring = JSONField(null=True, blank=True)
    """ points scored for each position 
    e.g. {1:10, 2:6, 3:4}
    """

    current_question = models.ForeignKey('Question', null=True, on_delete=models.SET_NULL, related_name='current_question')

    is_live = models.BooleanField(default=True)
    players = models.IntegerField(default=0)
    timeout = models.IntegerField(default=10)
    """ timeout for questions 
    
    If it gets 'scoring_positions' answers before this time, it will move to the next question 
    """

    def new_question(self):
        word = random.choice(words)
        word_characters = list(word)
        random.shuffle(word_characters)
        jumble = ''.join(word_characters)
        question = Question(room=self, word=word, jumble=jumble)
        question.save()
        return question

    def publish_new_question(self):
        question = self.new_question()
        self.current_question = question
        self.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            self.name, {
                'type': 'chat.message',
                'room_id': self.id,
                'message': question.jumble,
                'username': 'jumble',
                'message_type': 102
            }
        )

    def __str__(self):
        return self.name


class Question(BaseModel):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    word = models.CharField(max_length=100)
    jumble = models.CharField(max_length=100)
    answer_count = models.IntegerField(default=0)
    last_rank = models.IntegerField(default=0)

    def submit_user_answer(self, user, answer_string):
        if answer_string == self.word:
            answer, created = self.add_correct_answer(user)
            if created:
                return True, answer
            else:
                return False, 'already submitted correct answer'
        else:
            return False, 'wrong answer, please try again'

    def add_correct_answer(self, user):
        """
        Add correct answer for user and give correct rank

        This should be in a transaction
        """

        try:
            existing_answer = Answer.objects.get(user=user, question=self)
            return existing_answer, False
        except ObjectDoesNotExist:
            pass

        rank = self.last_rank + 1
        answer = Answer(user=user, question=self, rank=rank)
        answer.save()
        self.last_rank += 1
        self.answer_count += 1
        self.save()
        return answer, True

    def __str__(self):
        return '{} -> {}'.format(self.jumble, self.word)


class Answer(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    rank = models.IntegerField(default=0)

    def __str__(self):
        return '{} for question {} got rank {}'.format(self.user.username, self.question.jumble, self.rank)


class Score(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)

    def __str__(self):
        return 'user {} has {} points in room {}'.format(self.user.first_name, self.points, self.room.name)
