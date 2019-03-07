from django.db import models

# 脱敏字段配置
class DataMaskingColumns(models.Model):
    column_id = models.AutoField('字段id', primary_key=True)
    rule_type = models.IntegerField('规则类型',
                                    choices=((1, '手机号'), (2, '证件号码'), (3, '银行卡'), (4, '邮箱'), (5, '金额'), (6, '其他')))
    active = models.IntegerField('激活状态', choices=((0, '未激活'), (1, '激活')))
    instance_name = models.CharField('实例名称', max_length=50)
    table_schema = models.CharField('字段所在库名', max_length=64)
    table_name = models.CharField('字段所在表名', max_length=64)
    column_name = models.CharField('字段名', max_length=64)
    column_comment = models.CharField('字段描述', max_length=1024, default='', blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    sys_time = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'sqlaudit_data_masking_columns'
        verbose_name = u'脱敏字段配置'
        verbose_name_plural = u'脱敏字段配置'


# 脱敏规则配置
class DataMaskingRules(models.Model):
    rule_type = models.IntegerField('规则类型',
                                    choices=((1, '手机号'), (2, '证件号码'), (3, '银行卡'), (4, '邮箱'), (5, '金额'), (6, '其他')),
                                    unique=True)
    rule_regex = models.CharField('规则脱敏所用的正则表达式，表达式必须分组，隐藏的组会使用****代替', max_length=255)
    hide_group = models.IntegerField('需要隐藏的组')
    rule_desc = models.CharField('规则描述', max_length=100, default='', blank=True)
    sys_time = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'sqlaudit_data_masking_rules'
        verbose_name = u'脱敏规则配置'
        verbose_name_plural = u'脱敏规则配置'