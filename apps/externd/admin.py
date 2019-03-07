from django.contrib import admin


from externd.models import  DataMaskingColumns, DataMaskingRules
# 脱敏字段页面定义


@admin.register(DataMaskingColumns)
class DataMaskingColumnsAdmin(admin.ModelAdmin):
    list_display = (
        'column_id', 'rule_type', 'active', 'instance_name', 'table_schema', 'table_name', 'column_name',
        'create_time',)
    search_fields = ['table_name', 'column_name']
    list_filter = ('rule_type', 'active', 'instance_name')


# 脱敏规则页面定义
@admin.register(DataMaskingRules)
class DataMaskingRulesAdmin(admin.ModelAdmin):
    list_display = (
        'rule_type', 'rule_regex', 'hide_group', 'rule_desc', 'sys_time',)