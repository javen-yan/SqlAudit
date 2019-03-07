import json

from django.shortcuts import render
from django.http import JsonResponse

# Create your views here.
from django.views import View
from sqlorders.models import SysConfig
from apps.externd.utils import new_add_config


class CommonSetting(View):
    def get(self, request):
        configs = SysConfig.objects.all().values('name', 'key', 'value', 'is_enabled')
        fronted = {
            "configs": list(configs)
        }
        return render(request, 'settings/common.html', fronted)


class SysSettings(View):
    def post(self, request):
        received_json_data = request.POST.get("configs")
        status = new_add_config(json.loads(received_json_data))
        if not status:
            return JsonResponse({"status": "400", "msg": "添加配置失败"})
        else:
            return JsonResponse({"status": "0", "msg": "添加配置成功"})