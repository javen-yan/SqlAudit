# -*- coding:utf-8 -*-
# edit by fuzongfei

"""
status = 0: 推送执行结果
status = 1: 推送执行进度
status = 2: 推送inception processlist
"""

import ast
import logging
import os
import time
from datetime import datetime

import pymysql
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone

from sqlorders.api.executeStatementApi import ExecuteSql
from sqlorders.models import SqlOrdersExecTasks, SqlOrdersContents, MysqlSchemas, MysqlConfig
from sqlorders.msgNotice import SqlOrdersMsgPull
from sqlorders.utils import ExportToFiles

channel_layer = get_channel_layer()
logger = logging.getLogger('django')


@shared_task
def sync_schemas():
    """
    定时任务
    同步sqlaudit_mysql_config表中配置数据库实例的元数据信息到表sqlaudit_mysql_schemas
    """
    ignored_params = ('information_schema', 'mysql', 'percona', 'performance_schema', 'sys', 'test')
    schema_filter_query = f"select schema_name from information_schema.schemata " \
                          f"where schema_name not in {ignored_params}"

    collect_from_host = []
    for row in MysqlConfig.objects.all():
        collect_from_host.append({
            'id': row.id,
            'user': row.user,
            'password': row.password,
            'db_host': row.host,
            'db_port': row.port,
            'character': row.character,
            'envi_id': row.envi_id,
            'is_type': row.is_type,
            'comment': row.comment
        })

    for row in collect_from_host:
        try:
            cnx = pymysql.connect(user=row['user'],
                                  password=row['password'],
                                  host=row['db_host'],
                                  port=row['db_port'],
                                  charset='utf8mb4',
                                  cursorclass=pymysql.cursors.DictCursor)

            try:
                with cnx.cursor() as cursor:
                    cursor.execute(schema_filter_query)
                    for i in cursor.fetchall():
                        MysqlSchemas.objects.update_or_create(
                            cid_id=row['id'], host=row['db_host'], port=row['db_port'], schema=i['schema_name'],
                            defaults={'user': row['user'],
                                      'password': row['password'],
                                      'host': row['db_host'],
                                      'port': row['db_port'],
                                      'schema': i['schema_name'],
                                      'character': row['character'],
                                      'envi_id': row['envi_id'],
                                      'is_type': row['is_type'],
                                      'comment': row['comment']}
                        )
            finally:
                cnx.close()
        except Exception as err:
            logger.error(err.args[1])
            continue


def save_rbsql_as_file(rollbacksql):
    """当备份的数据太大时，数据库由于max_allowed_packet问题无法保存，此时保存到文件"""
    if not os.path.exists(r'media/rbsql'):
        os.makedirs('media/rbsql')
    filename = f"media/rbsql/rbsql_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.sql"
    with open(filename, 'w') as f:
        f.write(rollbacksql)
    return filename


def upd_current_task_status(id=None, exec_result=None, exec_status=None):
    """更新当前任务的进度"""
    # exec_result的数据格式
    # {'status': 'success', 'rollbacksql': [sql,], 'affected_rows': 1, 'runtime': '1.000s', 'exec_log': ''}
    # 或
    # {'status': 'fail', 'exec_log': ''}
    data = SqlOrdersExecTasks.objects.get(id=id)
    if exec_result['status'] in ['fail', 'warn']:
        # 标记为失败
        data.exec_status = '5'
        data.exec_log = exec_result.get('exec_log')
        data.save()
    elif exec_result['status'] == 'success':
        # 执行状态为处理中时，状态变为已完成
        if exec_status == '2':
            rbsql = exec_result.get('rollbacksql')
            affected_rows = int(exec_result.get('affected_rows'))
            runtime = exec_result.get('runtime')
            exec_log = exec_result.get('exec_log')
            try:
                data.rollback_sql = rbsql
                data.save()
            except Exception as err:
                filename = save_rbsql_as_file(rbsql)
                data.rollback_sql = '\n'.join([
                    '数据超出max_allowed_packet，写入到数据库失败',
                    '备份数据已经以文本的形式进行了保存',
                    '存储路径：',
                    filename
                ])
            finally:
                data.runtime = runtime
                data.exec_log = exec_log
                data.exec_status = '1'
                data.affected_row = affected_rows
                data.save()


def update_audit_content_progress(username, taskid):
    # 当点击全部执行时有效
    # 检查任务是否都执行完成，如果执行完成，将父任务进度设置为已完成
    obj = SqlOrdersExecTasks.objects.filter(taskid=taskid)
    exec_status = obj.values_list('exec_status', flat=True)
    related_id = obj.first().related_id

    if related_id:
        if all([False for i in list(exec_status) if i != '1']):
            data = SqlOrdersContents.objects.get(id=related_id)
            if data.progress != '4':
                data.progress = '4'
                data.updated_at = timezone.now()
                data.save()
                # 发送邮件
                msg_pull = SqlOrdersMsgPull(id=related_id, user=username, type='feedback')
                msg_pull.run()


@shared_task
def async_execute_sql(id=None, username=None, sql=None, host=None, port=None, database=None, exec_status=None):
    """执行SQL"""
    queryset = MysqlSchemas.objects.get(host=host, port=port, schema=database)
    database_type = MysqlConfig.objects.get(host=host, port=port).database_type

    execute_sql = ExecuteSql(host=host,
                             port=port,
                             user=queryset.user,
                             password=queryset.password,
                             charset=queryset.character,
                             database=database,
                             database_type=database_type,
                             username=username)
    result = execute_sql.run_by_sql(sql)

    # 更新任务进度
    upd_current_task_status(id=id, exec_result=result, exec_status=exec_status)


@shared_task
def async_execute_multi_sql(username, query, key):
    """
    批量执行SQL
    串行执行
    """
    taskid = key
    for row in SqlOrdersExecTasks.objects.raw(query):
        id = row.id
        host = row.host
        port = row.port
        database = row.database
        sql = row.sql + ';'

        obj = SqlOrdersExecTasks.objects.get(id=id)
        if obj.exec_status not in ('1', '2'):
            # 将任务进度设置为: 处理中
            obj.executor = username
            obj.execition_time = timezone.now()
            obj.exec_status = '2'
            obj.save()

            # 执行SQL
            async_execute_sql.delay(
                username=username,
                id=id,
                sql=sql,
                host=host,
                port=port,
                database=database,
                exec_status='2')
        while SqlOrdersExecTasks.objects.get(id=id).exec_status == '2':
            time.sleep(0.2)
            continue
    cache.delete(key)
    # 更新父任务进度
    update_audit_content_progress(username, ast.literal_eval(taskid))


@shared_task
def async_export_tasks(user=None, id=None, sql=None, host=None, port=None, database=None):
    export_to_excel = ExportToFiles(id, user, sql, host, port, database)
    export_to_excel.run()
