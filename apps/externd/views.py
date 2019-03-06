from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View

from webshell.models import WebShellInfo


class CommonSetting(View):
    def get(self, request):
        return render(request, 'settings/common.html')


class HotSetting(View):
    def get(self, request):
        return render(request, 'settings/hot_settings.html')