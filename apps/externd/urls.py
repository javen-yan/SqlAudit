from django.contrib.auth.decorators import login_required
from django.urls import path

from externd.views import CommonSetting, SysSettings

urlpatterns = [
    path(r'common_set/', login_required(CommonSetting.as_view()), name='p_common_set'),
    path(r'add_config/', login_required(SysSettings.as_view()), name='p_add_config'),
]
