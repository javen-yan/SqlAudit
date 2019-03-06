# -*- coding:utf-8 -*-
# edit by fuzongfei
import logging

from django.db import models

# Create your models here.

# sql工单环境定义
from users.models import UserAccounts

logger = logging.getLogger('django')


class SqlOrdersEnvironment(models.Model):
    envi_id = models.AutoField(primary_key=True, null=False, verbose_name=u'环境ID')
    envi_name = models.CharField(max_length=30, default='', null=False, verbose_name=u'环境')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name=u'更新时间')

    def __str__(self):
        return self.envi_name

    class Meta:
        verbose_name = u'工单环境'
        verbose_name_plural = verbose_name

        db_table = 'sqlaudit_sqlorder_environment'


type_choice = ((0, '查询_只读'), (1, 'SQL审核'), (2, '查询_读写'))
character_choice = (('utf8', 'utf8'), ('utf8mb4', 'utf8mb4'))
database_type = ((0, '非阿里云RDS'), (1, '阿里云RDS'))


class MysqlConfig(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    host = models.CharField(max_length=128, null=False, verbose_name=u'地址')
    port = models.IntegerField(null=False, default=3306, verbose_name=u'端口')
    user = models.CharField(max_length=32, default='', null=False, verbose_name=u'用户名')
    password = models.CharField(max_length=64, default='', null=False, verbose_name=u'密码')
    character = models.CharField(max_length=32, null=False, choices=character_choice, default='utf8',
                                 verbose_name=u'库表字符集')
    envi = models.ForeignKey(SqlOrdersEnvironment, default=None, to_field='envi_id', on_delete=models.CASCADE,
                             verbose_name=u'环境')
    is_type = models.SmallIntegerField(choices=type_choice, default=0, verbose_name=u'用途')
    database_type = models.SmallIntegerField(choices=database_type, default=0, verbose_name=u'数据库的类型')
    comment = models.CharField(max_length=128, null=True, verbose_name=u'主机描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name=u'更新时间')

    def __str__(self):
        return self.comment

    class Meta:
        verbose_name = u'MySQL配置'
        verbose_name_plural = verbose_name

        default_permissions = ()
        db_table = 'sqlaudit_mysql_config'
        unique_together = (('host', 'port'),)


class MysqlSchemas(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    cid = models.ForeignKey(MysqlConfig, default=None, to_field='id', on_delete=models.CASCADE, verbose_name=u'主机')
    user = models.CharField(max_length=30, null=False, verbose_name=u'用户名')
    password = models.CharField(max_length=30, null=False, verbose_name=u'密码')
    host = models.CharField(max_length=128, null=False, verbose_name=u'地址')
    port = models.IntegerField(null=False, default=3306, verbose_name=u'端口')
    schema = models.CharField(null=False, max_length=64, default='', verbose_name=u'schema信息')
    character = models.CharField(max_length=32, null=False, default='utf8', verbose_name=u'库表字符集')
    envi = models.ForeignKey(SqlOrdersEnvironment, default=None, to_field='envi_id', on_delete=models.CASCADE)
    is_type = models.SmallIntegerField(choices=type_choice, default=0, verbose_name=u'用途')
    comment = models.CharField(max_length=128, null=True, verbose_name=u'主机描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name=u'更新时间')

    class Meta:
        verbose_name = u'MySQL集群汇总库'
        verbose_name_plural = verbose_name

        default_permissions = ()
        db_table = 'sqlaudit_mysql_schemas'
        unique_together = (('host', 'port', 'schema'),)


# 审核进度选择
progress_choices = (
    ('0', u'待批准'),
    ('1', u'未批准'),
    ('2', u'已批准'),
    ('3', u'处理中'),
    ('4', u'已完成'),
    ('5', u'已关闭'),
    ('6', u'已勾住')
)

# 操作类型选择
# OPS为运维工单
sql_type_choice = (
    ('DDL', u'DDL'),
    ('DML', u'DML'),
    ('OPS', u'OPS')
)


class SqlOrdersContents(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    title = models.CharField(max_length=100, verbose_name=u'标题')
    description = models.CharField(max_length=2048, default='', null=False, verbose_name=u'需求')
    sql_type = models.CharField(max_length=5, default='DML', choices=sql_type_choice,
                                verbose_name=u'工单类型')
    envi = models.ForeignKey(SqlOrdersEnvironment, default=None, to_field='envi_id', on_delete=models.CASCADE)
    proposer = models.CharField(max_length=30, default='', verbose_name=u'申请人')
    auditor = models.CharField(max_length=30, default='', verbose_name=u'审核人')
    audit_time = models.DateTimeField(auto_now_add=True, verbose_name=u'审核时间')
    email_cc = models.CharField(max_length=4096, default='', verbose_name=u'抄送人')
    host = models.CharField(null=False, default='', max_length=128, verbose_name=u'主机')
    port = models.IntegerField(null=False, default=3306, verbose_name=u'端口')
    database = models.CharField(null=False, default='', max_length=80, verbose_name=u'库名')
    progress = models.CharField(max_length=10, default='0', choices=progress_choices, verbose_name=u'任务进度')
    remark = models.CharField(max_length=32, default='', null=False, verbose_name=u'备注')
    task_version = models.CharField(max_length=256, default='', verbose_name=u'上线任务版本')
    close_user = models.CharField(max_length=30, default='', verbose_name=u'关闭记录的用户')
    close_reason = models.CharField(max_length=1024, default='', verbose_name=u'关闭原因')
    close_time = models.DateTimeField(auto_now_add=True, verbose_name=u'关闭时间')
    contents = models.TextField(default='', verbose_name=u'提交的内容')
    export_file_format = models.CharField(max_length=30, choices=(('xlsx', 'xlsx'), ('csv', 'csv'), ('txt', 'txt')),
                                          default='xlsx', verbose_name=u'导出的文件格式')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name=u'更新时间')

    def __str__(self):
        return self.title

    def proposer_avatar_file(self):
        return UserAccounts.objects.get(username=self.proposer).avatar_file

    class Meta:
        verbose_name = u'工单记录'
        verbose_name_plural = verbose_name

        db_table = 'sqlaudit_sqlorders_contents'


exec_progress = (
    ('0', u'未执行'),
    ('1', u'已完成'),
    ('2', u'处理中'),
    ('3', u'失败'),
    ('4', u'异常')
)


class SqlOrdersExecTasks(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    uid = models.IntegerField(null=False, default=0, verbose_name=u'申请用户uid')
    user = models.CharField(max_length=30, null=False, verbose_name=u'申请用户')
    executor = models.CharField(max_length=30, null=False, default='', verbose_name=u'工单执行人')
    execition_time = models.DateTimeField(auto_now=True, verbose_name=u'工单执行时间')
    runtime = models.CharField(max_length=1024, null=False, default='0.00', verbose_name=u'任务运行时间，单位s')
    taskid = models.CharField(null=False, max_length=128, verbose_name=u'任务号')
    related_id = models.IntegerField(null=False, default=0, verbose_name=u'关联SqlOrdersContents的主键id')
    envi = models.ForeignKey(SqlOrdersEnvironment, default=None, to_field='envi_id', on_delete=models.CASCADE)
    host = models.CharField(null=False, max_length=128, verbose_name=u'操作目标数据库主机')
    database = models.CharField(null=False, max_length=80, verbose_name=u'操作目标数据库')
    port = models.IntegerField(null=False, default=3306, verbose_name=u'端口')
    sql = models.TextField(verbose_name=u'执行的SQL', default='')
    sql_type = models.CharField(max_length=5, default='DML', choices=sql_type_choice,
                                verbose_name=u'SQL类型')
    is_ghost = models.IntegerField(choices=((0, '否'), (1, '是')), default=0, verbose_name=u'是否启用ghost改表')
    ghost_pid = models.IntegerField(null=False, default=0, verbose_name=u'ghost进程pid')
    exec_status = models.CharField(max_length=10, default='0', choices=exec_progress, verbose_name=u'执行进度')
    affected_row = models.IntegerField(null=False, default=0, verbose_name=u'影响行数')
    exec_log = models.TextField(verbose_name=u'执行的记录', default='')
    rollback_sql = models.TextField(verbose_name=u'回滚的SQL', default='')
    export_file_format = models.CharField(max_length=30, choices=(('xlsx', 'xlsx'), ('csv', 'csv'), ('txt', 'txt')),
                                          default='xlsx', verbose_name=u'导出的文件格式')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name=u'生成时间')

    class Meta:
        verbose_name = u'工单执行任务'
        verbose_name_plural = verbose_name

        default_permissions = ()
        db_table = 'sqlaudit_sql_orders_execute_tasks'


class SqlOrdersTasksVersions(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    username = models.CharField(default='', null=False, max_length=128, verbose_name=u'创建用户')
    tasks_version = models.CharField(default='', null=False, max_length=128, verbose_name=u'任务版本')
    expire_time = models.DateTimeField(default='2000-11-01 01:01:01', verbose_name=u'任务截止上线日期')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')

    def __str__(self):
        return self.tasks_version

    class Meta:
        verbose_name = u'SQL工单上线任务版本'
        verbose_name_plural = verbose_name

        db_table = 'sqlaudit_sql_orders_tasks_versions'
        unique_together = ('tasks_version',)


class SysConfig(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    name = models.CharField(max_length=256, default='', null=False, verbose_name=u'名称')
    key = models.CharField(max_length=256, default='', null=False, verbose_name=u'key')
    value = models.TextField(max_length=256, null=True, blank=True, verbose_name=u'值')
    is_enabled = models.CharField(max_length=2, choices=(('0', '启用'), ('1', '禁用')), default='1', verbose_name=u'是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')

    class Meta:
        verbose_name = u'系统配置'
        verbose_name_plural = verbose_name

        default_permissions = ()
        db_table = 'sqlaudit_sys_config'


class SqlOrderReply(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键')
    reply = models.ForeignKey(SqlOrdersContents, on_delete=models.CASCADE, null=False, default='')
    user = models.ForeignKey(UserAccounts, on_delete=models.CASCADE, null=False, default='')
    reply_contents = models.TextField(default='', verbose_name=u'回复内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=u'回复时间')

    class Meta:
        verbose_name = u'工单回复'
        verbose_name_plural = verbose_name

        default_permissions = ()
        db_table = 'sqlaudit_sql_order_reply'

    def reply_id(self):
        return self.reply.id

    def user_id(self):
        return self.user.uid


class SqlExportFiles(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=u'主键id')
    task = models.ForeignKey(SqlOrdersExecTasks, on_delete=models.CASCADE, null=False, default='',
                             verbose_name=u'关联执行任务的主键id')
    file_name = models.CharField(max_length=256, default='', verbose_name=u'文件名')
    file_size = models.IntegerField(default=0, verbose_name=u'文件大小，单位B')
    files = models.FileField(upload_to='files/%Y/%m/%d/')
    content_type = models.CharField(max_length=100, default='', verbose_name=u'文件的类型')

    def size(self):
        return ''.join((str(round(self.file_size / 1024 / 1024, 2)), 'MB')) if self.file_size > 1048576 else ''.join(
            (str(round(self.file_size / 1024, 2)), 'KB'))

    class Meta:
        verbose_name = u'数据导出'
        verbose_name_plural = verbose_name

        default_permissions = ()
        db_table = 'sqlaudit_sql_export_excel'
