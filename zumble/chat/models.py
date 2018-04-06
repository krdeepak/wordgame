from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Room(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    scoring_positions = models.PositiveSmallIntegerField(default=1)
    """ max scoring positions for the puzzle """

    scoring = JSONField()
    """ points scored for each position 
    e.g. {1:10, 2:6, 3:4}
    """

    is_live = models.BooleanField(default=True)
    players = models.IntegerField(default=0)
    timeout = models.IntegerField(default=10)
    """ timeout for questions 
    
    If it gets 'scoring_positions' answers before this time, it will move to the next question 
    """

    def __str__(self):
        return self.name


class Question(BaseModel):
    room = models.ForeignKey(Room)
    word = models.CharField(max_length=100)
    jumble = models.CharField(max_length=100)
    answer_count = models.IntegerField(default=0)

    def __str__(self):
        return 'puzzle {} for word {}'.format(self.jumble, self.word)


class Answer(BaseModel):
    user = models.ForeignKey(User)
    question = models.ForeignKey(Question)
    rank = models.IntegerField()

    def __str__(self):
        return '{} for question {} got rank {}'.format(self.user.first_name, self.question.jumble, self.rank)
