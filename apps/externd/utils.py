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


def modify_config(params):
    tmp_dict = {}
    for cds in params:
        if not tmp_dict.get(cds.get("key").split("-")[0]):
            tmp_dict.setdefault(cds.get("key").split("-")[0], {cds.get("key").split("-")[1]: cds.get("value")})
        else:
            tmp_dict[cds.get("key").split("-")[0]][cds.get("key").split("-")[1]] = cds.get("value")

    tmp_list = []
    for k, v in tmp_dict.items():
        tmp = {"key": k}
        v.update(tmp)
        tmp_list.append(v)

    for row in tmp_list:
        try:
            sys_config = SysConfig.objects.get(key=row["key"])
            if row["is_enabled"] == "true":
                row["is_enabled"] = "0"
            if row["is_enabled"] == "false":
                row["is_enabled"] = "1"
            sys_config.is_enabled = row["is_enabled"]
            sys_config.value = row["value"]
            sys_config.save()
        except Exception as e:
            print(e.__str__())
            return {
                "status": False,
                "msg": e.__str__()
            }
    return {
                "status": True,
                "msg":  "修改成功"
            }
