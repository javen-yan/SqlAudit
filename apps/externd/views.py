import json

from django.shortcuts import render
from django.http import JsonResponse

# Create your views here.
from django.views import View
from sqlorders.models import SysConfig
from externd.utils import modify_config


class CommonSetting(View):
    def get(self, request):
        configs_rows = SysConfig.objects.all().values('name', 'key', 'value', 'is_enabled')
        return render(request, 'settings/common.html', {"configs": configs_rows})

    def post(self, request):
        received_json_data = request.POST.get("configs")
        status = modify_config(json.loads(received_json_data))
        if status["status"]:
            return JsonResponse({"status": 0, "msg": "配置修改成功"})
        else:
            return JsonResponse({"status": 2, "msg": status["msg"]})