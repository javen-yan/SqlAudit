# -*- coding:utf-8 -*-
# edit by fuzongfei

import ast
import datetime
import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import F, When, Value, CharField, Case
from django.http import HttpResponse, JsonResponse
# Create your views here.
from django.shortcuts import render
from django.views import View
from django.views.generic import FormView

from sqlorders.forms import GetTablesForm, SqlOrdersAuditForm, SqlOrderListForm, SyntaxCheckForm, BeautifySQLForm, \
    SqlOrdersApproveForm, SqlOrdersFeedbackForm, SqlOrdersCloseForm, HookSqlOrdersForm, \
    GeneratePerformTasksForm, SinglePerformTasksForm, FullPerformTasksForm, SqlOrdersTasksVersionForm, \
    PerformTasksOpForm, CommitOrderReplyForm, MyOrdersForm, ExecuteExportTasksForm
from sqlorders.models import SqlOrdersEnvironment, MysqlSchemas, SqlOrdersContents, SqlOrdersExecTasks, \
    SqlOrdersTasksVersions, SqlOrderReply, SqlExportFiles
from sqlorders.utils import check_incep_alive
from users.models import RolePermission, UserRoles, UserAccounts
from users.permissionsVerify import permission_required

logger = logging.getLogger('django')


class GetSqlOrdersEnviView(View):
    """获取工单环境"""

    def get(self, request):
        queryset = SqlOrdersEnvironment.objects.all().values('envi_id', 'envi_name')

        serialize_data = json.dumps(list(queryset), cls=DjangoJSONEncoder)
        return HttpResponse(serialize_data)


class RenderSqlDmlOrdersView(View):
    """渲染dml工单页面"""

    def get(self, request):
        return render(request, 'sqlorders/sql_dml_orders.html')


class RenderSqlDdlOrdersView(View):
    """渲染ddl工单页面"""

    def get(self, request):
        return render(request, 'sqlorders/sql_ddl_orders.html')


class RenderOpsOrdersView(View):
    """渲染运维工单"""

    def get(self, request):
        return render(request, 'sqlorders/ops_orders.html')


class GetAuditUserView(View):
    """获取有审核权限的用户"""

    def get(self, request):
        role_queryset = RolePermission.objects.filter(permission_name='can_audit_sql').values_list('role__role_name',
                                                                                                   flat=True)
        queryset = UserRoles.objects.filter(role_name__in=role_queryset).filter(
            user__username__isnull=False
        ).values(
            username=F('user__username'),
            displayname=F('user__displayname')
        ).order_by('username')
        serialize_data = json.dumps(list(queryset), cls=DjangoJSONEncoder)
        return HttpResponse(serialize_data)


class GetTargetSchemasView(View):
    """获取dml和ddl工单指定环境的schema列表"""

    @permission_required('can_commit_sql', 'can_audit_sql', 'can_execute_sql', 'can_commit_ops', 'can_audit_ops')
    def post(self, request):
        # envi_id = request.POST.get('envi_id')
        #
        # queryset = MysqlSchemas.objects.filter(
        #     envi_id=envi_id, is_type=1
        # ).values('host', 'port', 'schema', 'comment')
        # serialize_data = json.dumps(list(queryset), cls=DjangoJSONEncoder)
        # return HttpResponse(serialize_data)

        envi_id = request.POST.get('envi_id')
        purpose = request.POST.get('purpose')

        queryset = []
        if purpose in ('export', 'dbdict', 'soar'):
            # 数据导出或查询数据字典，选择只读库
            queryset = MysqlSchemas.objects.filter(envi_id=envi_id, is_type__in=(0, 2)).values('host', 'port',
                                                                                               'schema',
                                                                                               'comment')
        elif purpose in ('dml', 'ddl'):
            # DML和DDL工单选择SQL审核
            queryset = MysqlSchemas.objects.filter(envi_id=envi_id, is_type=1).values('host', 'port', 'schema',
                                                                                      'comment')
        serialize_data = json.dumps(list(queryset), cls=DjangoJSONEncoder)
        return HttpResponse(serialize_data)


class GetTablesView(View):
    """获取指定主机的所有表"""

    def post(self, request):
        form = GetTablesForm(request.POST)
        if form.is_valid():
            context = form.query()
        return HttpResponse(json.dumps(context))


class SyntaxCheckView(View):
    """SQL语法检查"""

    @check_incep_alive
    def post(self, request):
        form = SyntaxCheckForm(request.POST)
        if form.is_valid():
            context = form.query(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class BeautifySQLView(View):
    """
    美化SQL
    判断SQL类型（DML还是DDL），并分别进行美化
    最后合并返回
    """

    def post(self, request):
        form = BeautifySQLForm(request.POST)
        if form.is_valid():
            context = form.beautify()
        else:
            error = form.errors.as_json()
            error_msg = [value[0].get('message') for key, value in json.loads(error).items()][0]
            context = {'status': 2, 'msg': str(error_msg)}
        return HttpResponse(json.dumps(context))


class SqlOrdersAuditView(View):
    """DDL、DML工单提交、处理"""

    @permission_required('can_commit_sql', 'can_commit_ops')
    def post(self, request):
        form = SqlOrdersAuditForm(request.POST)
        if form.is_valid():
            context = form.save(request)
            return HttpResponse(json.dumps(context))
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}
            return HttpResponse(json.dumps(context))


class RenderSqlOrdersListView(View):
    """渲染工单列表页面"""

    def get(self, request, envi_id):
        envi_name = SqlOrdersEnvironment.objects.get(envi_id=envi_id).envi_name
        return render(request, 'sqlorders/sql_orders_list.html', {'envi_id': envi_id, 'envi_name': envi_name})


class SqlOrdersListView(View):
    """获取工单列表页面的工单数据"""

    def get(self, request):
        form = SqlOrderListForm(request.GET)
        context = {}
        if form.is_valid():
            context = form.query(request)

        return JsonResponse(context, safe=False)


class SqlOrdersDetailsView(View):
    """查看提交工单的详情"""

    def get(self, request, id):
        queryset = SqlOrdersContents.objects.annotate(
            progress_value=Case(
                When(progress='0', then=Value('待批准')),
                When(progress='1', then=Value('未批准')),
                When(progress='2', then=Value('已批准')),
                When(progress='3', then=Value('处理中')),
                When(progress='4', then=Value('已完成')),
                When(progress='5', then=Value('已关闭')),
                When(progress='6', then=Value('已勾住')),
                output_field=CharField(),
            ),
        ).get(id=id)

        return render(request, 'sqlorders/sql_orders_details.html', {'contents': queryset})


class SqlOrdersApproveView(FormView):
    """线上工单审批操作，需要can_audit权限"""
    form_class = SqlOrdersApproveForm

    def dispatch(self, request, *args, **kwargs):
        return super(SqlOrdersApproveView, self).dispatch(request, *args, **kwargs)

    @permission_required('can_audit_sql')
    @transaction.atomic
    def form_valid(self, form):
        context = form.save(self.request)
        return HttpResponse(json.dumps(context))

    def form_invalid(self, form):
        error = form.errors.as_text()
        context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class SqlOrdersFeedbackView(FormView):
    """线上工单反馈，反馈执行进度"""
    form_class = SqlOrdersFeedbackForm

    def dispatch(self, request, *args, **kwargs):
        return super(SqlOrdersFeedbackView, self).dispatch(request, *args, **kwargs)

    @permission_required('can_execute_sql', 'can_audit_sql')
    @transaction.atomic
    def form_valid(self, form):
        context = form.save(self.request)
        return HttpResponse(json.dumps(context))

    def form_invalid(self, form):
        error = form.errors.as_text()
        context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class SqlOrdersCloseView(FormView):
    """关闭记录"""
    form_class = SqlOrdersCloseForm

    def dispatch(self, request, *args, **kwargs):
        return super(SqlOrdersCloseView, self).dispatch(request, *args, **kwargs)

    @permission_required('can_commit_sql', 'can_execute_sql', 'can_audit_sql', 'can_commit_ops', 'can_audit_ops')
    @transaction.atomic
    def form_valid(self, form):
        context = form.save(self.request)
        return HttpResponse(json.dumps(context))

    def form_invalid(self, form):
        error = form.errors.as_text()
        context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class CommitOrderReplyView(FormView):
    """处理用户的回复的工单信息"""

    form_class = CommitOrderReplyForm

    def form_valid(self, form):
        context = form.is_save(self.request)
        return HttpResponse(json.dumps(context))

    def form_invalid(self, form):
        error = form.errors.as_json()
        error_msg = [value[0].get('message') for key, value in json.loads(error).items()][0]
        context = {'status': 2, 'msg': str(error_msg)}
        return HttpResponse(json.dumps(context))


class GetOrderReplyView(View):
    """获取用户的回复的工单信息"""

    def get(self, request):
        reply_id = request.GET.get('reply_id')
        queryset = SqlOrderReply.objects.annotate(
            username=F('user__username'),
            avatar_file=F('user__avatar_file'),
        ).filter(reply__id=reply_id).values('username', 'avatar_file', 'reply_contents', 'created_at').order_by(
            '-created_at')
        serialize_data = json.dumps(list(queryset), cls=DjangoJSONEncoder)
        context = {'status': 0, 'data': serialize_data}
        return HttpResponse(json.dumps(context))


class HookSqlOrdersView(View):
    """工单扭转, 处理钩子数据"""

    @permission_required('can_commit_sql', 'can_execute_sql', 'can_audit_sql', 'can_commit_ops', 'can_audit_ops')
    def post(self, request):
        form = HookSqlOrdersForm(request.POST)
        if form.is_valid():
            context = form.save(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}

        return HttpResponse(json.dumps(context))


class GeneratePerformTasksView(View):
    """工单转换成执行任务"""

    @permission_required('can_execute_sql')
    def post(self, request):
        form = GeneratePerformTasksForm(request.POST)
        if form.is_valid():
            context = form.save(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}

        return HttpResponse(json.dumps(context))


class RenderPerformTasksView(View):
    """渲染指定执行任务详情页面"""

    def get(self, request, taskid):
        return render(request, 'sqlorders/perform_tasks.html', {'taskid': taskid})


class PerformTasksDetailsView(View):
    """获取执行任务列表数据"""

    def get(self, request):
        taskid = ast.literal_eval(request.GET.get('taskid'))

        queryset = SqlOrdersExecTasks.objects.annotate(
            status=Case(
                When(exec_status='0', then=Value('未执行')),
                When(exec_status='1', then=Value('已完成')),
                When(exec_status='2', then=Value('处理中')),
                When(exec_status='5', then=Value('失败')),
                output_field=CharField(),
            )
        ).filter(taskid=taskid).values('id', 'user', 'sql', 'taskid', 'status', 'sql_type')

        i = 1
        task_details = []

        for row in queryset:
            result = {
                'sid': i,
                'id': row['id'],
                'user': row['user'],
                'sql': row['sql'],
                'taskid': row['taskid'],
                'exec_status': row['status'],
                'sql_type': row['sql_type']
            }
            if SqlExportFiles.objects.filter(task_id=row['id']).exists():
                file_path = SqlExportFiles.objects.get(task_id=row['id']).files.url
            else:
                file_path = None
            result['file_path'] = file_path
            task_details.append(result)
            i += 1
        return HttpResponse(json.dumps(task_details))


class GetSqlExecuteDetailsView(View):
    """获取每条SQL的执行详情"""

    def get(self, request):
        id = request.GET.get('id')
        queryset = SqlOrdersExecTasks.objects.annotate(
            status=Case(
                When(exec_status='0', then=Value('未执行')),
                When(exec_status='1', then=Value('已完成')),
                When(exec_status='2', then=Value('处理中')),
                When(exec_status='3', then=Value('回滚中')),
                When(exec_status='4', then=Value('已回滚')),
                When(exec_status='5', then=Value('失败')),
                When(exec_status='6', then=Value('异常')),
                output_field=CharField(),
            )
        ).filter(related_id=id).values('sql', 'status', 'affected_row', 'runtime', 'executor', 'execition_time')

        field = [{'field': 'sid', 'title': 'ID'},
                 {'field': 'sql', 'title': 'SQL'},
                 {'field': 'status', 'title': '状态'},
                 {'field': 'affected_row', 'title': '影响行数'},
                 {'field': 'runtime', 'title': '耗时(s)'},
                 {'field': 'executor', 'title': '执行人'},
                 {'field': 'execition_time', 'title': '执行时间'},
                 ]

        i = 1
        data = []
        for row in queryset:
            data.append({
                'sid': i,
                'sql': row['sql'][:50] + ' ...',
                'status': row['status'],
                'affected_row': row['affected_row'],
                'runtime': row['runtime'],
                'executor': row['executor'],
                'execition_time': (row['execition_time'] + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            })
            i += 1
        context = {'columns': field, 'data': data}
        return JsonResponse(context, safe=False)


class PerformTasksSQLPreView(View):
    """获取执行任务的SQL列表，进行预览展示"""

    def get(self, request):
        taskid = ast.literal_eval(request.GET.get('taskid'))
        queryset = SqlOrdersExecTasks.objects.filter(taskid=taskid).values_list('sql', flat=True)
        return HttpResponse(json.dumps(list(queryset)))


class FullPerformTasksView(View):
    """全部执行"""

    @permission_required('can_execute_sql')
    @transaction.atomic
    def post(self, request):
        form = FullPerformTasksForm(request.POST)
        if form.is_valid():
            context = form.exec(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class SinglePerformTasksView(View):
    """单条执行"""

    @permission_required('can_execute_sql')
    @transaction.atomic
    def post(self, request):
        form = SinglePerformTasksForm(request.POST)
        if form.is_valid():
            context = form.exec(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class PerformTasksOpView(View):
    """
    执行任务-操作，支持：暂停、恢复、终止
    只支持停止修改表结构的操作
    """

    @permission_required('can_execute_sql')
    @transaction.atomic
    def post(self, request):
        form = PerformTasksOpForm(request.POST)
        if form.is_valid():
            context = form.op(request)
        else:
            error = form.errors.as_json()
            error_msg = [value[0].get('message') for key, value in json.loads(error).items()][0]
            context = {'status': 2, 'msg': str(error_msg)}

        return HttpResponse(json.dumps(context))


class GetPerformTasksResultView(View):
    """获取执行任务的执行结果和备份信息"""

    def get(self, request):
        id = request.GET.get('id')
        queryset = SqlOrdersExecTasks.objects.get(id=id)
        exec_log = queryset.exec_log
        if queryset.exec_status in ('1', '4', '5'):
            if queryset.is_ghost == 1:
                data = {'rollback_log': '', 'exec_log': exec_log}
                context = {'status': 1, 'msg': '', 'data': data}
            else:
                rollback_sql = queryset.rollback_sql
                data = {'rollback_log': rollback_sql, 'exec_log': exec_log}
                context = {'status': 0, 'msg': '', 'data': data}
        else:
            context = {'status': 2, 'msg': '该SQL未被执行，无法查询状态信息'}
        return HttpResponse(json.dumps(context))


class RenderSqlOrdersTasksVersionView(View):
    """渲染上线版本页面"""

    def get(self, request):
        return render(request, 'sqlorders/sql_tasks_version.html')


class SqlOrdersTasksVersionView(View):
    """返回上线版本数据"""

    def get(self, request):
        data = SqlOrdersTasksVersions.objects.all().values('id', 'tasks_version', 'username', 'expire_time',
                                                           'created_at')
        return JsonResponse(list(data), safe=False)

    # 有can_commit权限的可以创建
    @permission_required('can_commit_sql', 'can_commit_ops')
    def post(self, request):
        form = SqlOrdersTasksVersionForm(request.POST)
        if form.is_valid():
            context = form.save(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class SqlOrdersTasksVersionListView(View):
    def get(self, request):
        """
        如果当前任务的提交时间大于任务设置的过期时间，不允许选择该任务
        is_disable：是否禁用，0：否，1：是
        """
        before_14_days = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
        query = f"select id,tasks_version,if(now()>expire_time,1,0) as is_disable from " \
            f"sqlaudit_sql_orders_tasks_versions " \
            f"where created_at >= '{before_14_days}' order by created_at desc"
        data = []
        for row in SqlOrdersTasksVersions.objects.raw(query):
            data.append({'tasks_version': row.tasks_version, 'is_disable': row.is_disable})

        return JsonResponse(data, safe=False)


class GetVersionOrdersList(View):
    """获取上线版本内的工单列表"""

    def get(self, request):
        tasks = request.GET.get('tasks')

        queryset = SqlOrdersEnvironment.objects.values('envi_id', 'envi_name').order_by('-envi_id')
        dynamic_columns_join = ''
        for row in queryset:
            dynamic_columns_join += f"max(if(envi_id={row['envi_id']}, progress, -1)) as {row['envi_name']},"

        # 获取任务下所有工单分别在各个环境中的状态
        # 此处的环境为动态环境
        query = f"select " + dynamic_columns_join + \
                "id,title,proposer,task_version " \
                    f"from sqlaudit_sqlorders_contents where task_version='{tasks}' group by title order by id desc"
        result = []

        data = SqlOrdersContents.objects.raw(query)
        dynamic_columns = list(data.columns)[:-4]

        # 获取列名并进行拼接
        columns_definition = [{'field': 'id', 'title': 'ID', 'visible': False},
                              {'field': 'title', 'title': '标题'},
                              {'field': 'proposer', 'title': '申请人'},
                              {'field': 'auditor', 'title': '审核人'},
                              {'field': 'task_version', 'title': '上线版本号'},
                              ]

        dynamic_columns_definition = [{'field': x, 'title': x, 'formatter': 'render_finish_status'} for x in
                                      dynamic_columns]

        # 获取列名对应的数据
        for row in data:
            columns = {
                'id': row.id,
                'title': row.title,
                'proposer': row.proposer,
                'auditor': row.auditor,
                'task_version': row.task_version,
            }
            for i in dynamic_columns:
                columns[i] = getattr(row, i)
            result.append(columns)

        context = {'columns': columns_definition + dynamic_columns_definition, 'data': result}
        return JsonResponse(context, safe=False)


class RenderMyOrdersView(View):
    """渲染工单列表页面"""

    @permission_required('can_commit_sql', 'can_audit_sql', 'can_execute_sql', 'can_commit_ops', 'can_audit_ops')
    def get(self, request):
        return render(request, 'sqlorders/my_orders.html')


class MyOrdersView(View):
    """获取工单列表页面的工单数据"""

    @permission_required('can_commit_sql', 'can_audit_sql', 'can_execute_sql', 'can_commit_ops', 'can_audit_ops')
    def get(self, request):
        form = MyOrdersForm(request.GET)
        context = {}
        if form.is_valid():
            context = form.query(request)

        return JsonResponse(context, safe=False)


class RenderSqlExportView(View):
    def get(self, request):
        return render(request, 'sqlorders/export_orders.html')


class RenderExportTasksView(View):
    """渲染指定导出数据执行任务详情页面"""

    def get(self, request, taskid):
        return render(request, 'sqlorders/export_tasks.html', {'taskid': taskid})


class ExecuteExportTasksView(View):
    """执行导出任务"""

    @permission_required('can_execute_sql')
    @transaction.atomic
    def post(self, request):
        form = ExecuteExportTasksForm(request.POST)
        if form.is_valid():
            context = form.exec(request)
        else:
            error = form.errors.as_text()
            context = {'status': 2, 'msg': error}
        return HttpResponse(json.dumps(context))


class GetOrderChartView(View):
    def get(self, request):
        my_order_queryset = SqlOrdersContents.objects.filter(proposer=request.user.username)
        my_order_count = my_order_queryset.count()
        my_order_dml_count = my_order_queryset.filter(sql_type='DML').count()
        my_order_ddl_count = my_order_queryset.filter(sql_type='DDL').count()
        my_order_ops_count = my_order_queryset.filter(sql_type='OPS').count()

        myorder = [
            {
                'value': my_order_dml_count,
                'color': '#f56954',
                'highlight': '#f56954',
                'label': 'DML工单'
            },
            {
                'value': my_order_ddl_count,
                'color': '#00a65a',
                'highlight': '#00a65a',
                'label': 'DDL工单'
            },
            {
                'value': my_order_ops_count,
                'color': '#00c0ef',
                'highlight': '#00c0ef',
                'label': '运维工单'
            }]

        platform_order_count = SqlOrdersContents.objects.count()
        platform_order_dml_count = SqlOrdersContents.objects.filter(sql_type='DML').count()
        platform_order_ddl_count = SqlOrdersContents.objects.filter(sql_type='ddl').count()
        platform_order_ops_count = SqlOrdersContents.objects.filter(sql_type='ops').count()
        user_count = UserAccounts.objects.count()
        platformorder = [
            {
                'value': platform_order_dml_count,
                'color': '#f56954',
                'highlight': '#f56954',
                'label': 'DML工单'
            },
            {
                'value': platform_order_ddl_count,
                'color': '#00a65a',
                'highlight': '#00a65a',
                'label': 'DDL工单'
            },
            {
                'value': platform_order_ops_count,
                'color': '#00c0ef',
                'highlight': '#00c0ef',
                'label': '运维工单'
            }]

        context = {'my_order_count': my_order_count, 'platform_order_count': platform_order_count,
                   'user_count': user_count, 'myorder': myorder, 'platformorder': platformorder}

        return HttpResponse(json.dumps(context))
