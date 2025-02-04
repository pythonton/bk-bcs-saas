# -*- coding: utf-8 -*-
#
# Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition) available.
# Copyright (C) 2017-2019 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
"""
模板集的公共方法
"""
import json
import logging
import re
from collections import Counter

from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from backend.accounts import bcs_perm
from backend.apps.constants import ProjectKind
from backend.bcs_web.audit_log import client
from backend.utils import cache
from backend.utils.exceptions import ResNotFoundError

from .constants import NUM_VAR_ERROR_MSG, RESOURCE_NAMES, VARIABLE_PATTERN, TemplateEditMode
from .models import CATE_SHOW_NAME, MODULE_DICT, ShowVersion, Template, VersionedEntity
from .serializers_new import CreateTemplateSLZ, TemplateSLZ

logger = logging.getLogger(__name__)

KEY_PATTERN = re.compile(r'{{([^}]*)}}')
REAL_NUM_VAR_PATTERN = re.compile(r"^%s*$" % VARIABLE_PATTERN)


def to_bcs_res_name(project_kind, origin_name):
    if origin_name not in CATE_SHOW_NAME.values():
        return origin_name
    if project_kind == ProjectKind.K8S.value:
        return f'K8s{origin_name}'
    return origin_name.lower()


@cache.region.cache_on_arguments(expiration_time=60)
def get_all_template_info_by_project(project_id):
    # 获取项目下所有的模板信息
    # 暂时不支持YAML模板查询
    temps = Template.objects.filter(project_id=project_id, edit_mode=TemplateEditMode.PageForm.value).values(
        'id', 'name'
    )
    tem_dict = {tem['id']: tem['name'] for tem in temps}
    tem_ids = tem_dict.keys()

    # 获取所有的可见版本
    show_vers = ShowVersion.objects.filter(template_id__in=tem_ids).values(
        'id', 'real_version_id', 'name', 'template_id'
    )

    resource_list = []

    for _show in show_vers:
        show_version_id = _show['id']
        real_version_id = _show['real_version_id']
        template_id = _show['template_id']
        template_name = tem_dict.get(template_id)

        # 每个版本的具体信息
        versioned_entity = VersionedEntity.objects.get(template_id=template_id, id=real_version_id)
        entity = versioned_entity.get_entity()
        for category in entity:
            ids = entity.get(category)
            id_list = ids.split(',') if ids else []
            res_list = MODULE_DICT.get(category).objects.filter(id__in=id_list).values('id', 'name', 'config')
            for resource in res_list:
                config = resource['config']
                resource_list.append(
                    {
                        'template_id': template_id,
                        'template_name': template_name,
                        'show_version_id': show_version_id,
                        'show_version_name': _show['name'],
                        'category': category,
                        'category_name': CATE_SHOW_NAME.get(category, category),
                        'resource_id': resource['id'],
                        'resource_name': resource['name'],
                        'config': config,
                    }
                )
    return resource_list


# TODO refactor
def get_all_template_config(project_id):
    # 暂时不支持YAML模板查询
    tem_ids = Template.objects.filter(project_id=project_id, edit_mode=TemplateEditMode.PageForm.value).values_list(
        'id', flat=True
    )
    tem_ids = list(tem_ids)
    real_version_ids = ShowVersion.objects.filter(template_id__in=tem_ids).values_list('real_version_id', flat=True)
    real_version_ids = list(real_version_ids)
    versioned_entity = VersionedEntity.objects.filter(id__in=real_version_ids).values('entity', 'id')
    # 多个 show_ver 对应 一个 real_version，real_version 需要按show_ver出现的次数重复计数
    real_version_count_dict = Counter(real_version_ids)

    category_dict = {}
    for ver in versioned_entity:
        try:
            entity = json.loads(ver['entity'])
        except Exception as error:
            logger.exception('load entity error, %s, %s', ver, error)
            continue

        # 重复出现的id，需要重复添加
        count = real_version_count_dict.get(ver['id'])
        i = 0
        while i < count:
            for category in entity:
                ids = entity.get(category)
                id_list = ids.split(',') if ids else []
                id_list = [int(_id) for _id in id_list]
                if category in category_dict:
                    category_dict[category].extend(id_list)
                else:
                    category_dict[category] = id_list
            i = i + 1

    resource_list = []
    for category in category_dict:
        category_id_list = category_dict[category]
        # 统计每个id出现的次数
        category_id_count_dict = Counter(category_id_list)
        res_list = MODULE_DICT.get(category).objects.filter(id__in=category_id_list).values('config', 'id')
        for resource in res_list:
            # 重复出现的id，需要重复添加
            count = category_id_count_dict.get(resource['id'])
            i = 0
            while i < count:
                resource_list.append({'config': resource['config']})
                i = i + 1
    return resource_list


def check_var_by_config(config):
    """获取配置文件中所有的变量"""
    search_list = KEY_PATTERN.findall(config)
    search_keys = set(search_list)
    for _key in search_keys:
        if not REAL_NUM_VAR_PATTERN.match(_key):
            raise ValidationError(_('变量[{}]不合法, {}').format(_key, NUM_VAR_ERROR_MSG))
    return list(search_keys)


def validate_resource_name(resource_name):
    if resource_name not in RESOURCE_NAMES:
        raise ResNotFoundError(_('资源{}不存在').format(resource_name))


def validate_template_locked(template, username):
    locker = template.locker
    if template.is_locked and locker != username:
        raise ValidationError(_('{locker}正在操作，您如需操作请联系{locker}解锁').format(locker=locker))


def create_template(username, project_id, tpl_args):
    if not tpl_args:
        raise ValidationError(_("请先创建模板集"))

    tpl_args['project_id'] = project_id
    serializer = CreateTemplateSLZ(data=tpl_args)
    serializer.is_valid(raise_exception=True)
    template = serializer.save(creator=username)
    # 记录操作日志
    client.ContextActivityLogClient(
        project_id=project_id,
        user=username,
        resource_type='template',
        resource=tpl_args['name'],
        resource_id=template.id,
        extra=json.dumps(tpl_args),
        description=_("创建模板集"),
    ).log_add()
    return template


def update_template(username, template, tpl_args):
    serializer = TemplateSLZ(template, data=tpl_args)
    serializer.is_valid(raise_exception=True)
    template = serializer.save(updator=username)
    # 记录操作日志
    client.ContextActivityLogClient(
        project_id=template.project_id,
        user=username,
        resource_type="template",
        resource=template.name,
        resource_id=template.id,
        extra=json.dumps(serializer.data),
        description=_("更新模板集"),
    ).log_modify()
    return template


def create_template_with_perm_check(request, project_id, tpl_args):
    # 验证用户是否有创建的权限
    perm = bcs_perm.Templates(request, project_id, bcs_perm.NO_RES)
    # 如果没有权限，会抛出异常
    perm.can_create(raise_exception=True)
    template = create_template(request.user.username, project_id, tpl_args)
    # 注册资源到权限中心
    perm.register(template.id, tpl_args['name'])
    return template


def update_template_with_perm_check(request, template, tpl_args):
    validate_template_locked(template, request.user.username)
    # 验证用户是否有编辑权限
    perm = bcs_perm.Templates(request, template.project_id, template.id, template.name)
    perm.can_edit(raise_exception=True)
    template = update_template(request.user.username, template, tpl_args)
    if template.name != tpl_args.get('name'):
        perm.update_name(template.name)
    return template
