from django.contrib.auth.decorators import login_required
from django.urls import path

from externd.views import CommonSetting

urlpatterns = [
    path(r'common_set/', login_required(CommonSetting.as_view()), name='p_common_set')
]
