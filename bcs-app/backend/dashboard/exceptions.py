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


class DashboardBaseError(Exception):
    """ Dashboard 模块基础异常类 """

    message = 'Dashboard module exception'
    code = 40050

    def __init__(self, message=None, code=None):
        """ 初始化异常类，若无参数则使用默认值 """
        if message:
            self.message = message
        if code:
            self.code = code

    def __str__(self):
        return f'{self.code}: {self.message}'


class ResourceNotExist(DashboardBaseError):
    """ 指定资源不存在 """

    message = 'Resource not exist'
