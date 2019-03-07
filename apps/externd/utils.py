from sqlorders.models import SysConfig


def new_add_config(params):
    try:
        sysconfig = SysConfig()
        sysconfig.name = params.get("name")
        sysconfig.key = params.get("key")
        sysconfig.value = params.get("value")
        sysconfig.is_enabled = params.get("is_enabled")
        sysconfig.save()
        return True
    except Exception as e:
        print(e.__str__())
        return False
