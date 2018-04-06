from django.contrib import admin
from chat.models import Room, Question, Answer

admin.site.register(Room)
admin.site.register(Question)
admin.site.register(Answer)

