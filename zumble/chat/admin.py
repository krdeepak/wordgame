from django.contrib import admin
from chat.models import Room, Question, Answer, Score

admin.site.register(Room)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Score)

