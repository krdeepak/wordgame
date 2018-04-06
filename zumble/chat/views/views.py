from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import TemplateView, CreateView
from django.views import View
from django.shortcuts import render

from chat.models import Room


class HomeView(View):
    template_name = 'home.html'

    def get(self, request):
        rooms = Room.objects.all()
        return render(request, self.template_name, {'rooms': rooms})


class CreateUserView(CreateView):
    template_name = 'register.html'
    form_class = UserCreationForm
    success_url = '/'

    def form_valid(self, form):
        valid = super(CreateUserView, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid
