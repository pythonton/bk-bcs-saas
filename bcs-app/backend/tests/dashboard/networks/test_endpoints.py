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
import pytest

pytestmark = pytest.mark.django_db


class TestEndpoints:
    """ 测试 Endpoints 相关接口 """

    def test_list(self, api_client, project_id, cluster_id, dashboard_api_common_patch):
        """ 测试获取资源列表接口 """
        response = api_client.get(f'/api/dashboard/projects/{project_id}/clusters/{cluster_id}/networks/endpoints/')
        assert response.json()['code'] == 0

    def test_retrieve(self, api_client, project_id, cluster_id, dashboard_api_common_patch):
        """ 测试获取单个资源接口 """
        namespace, endpoints_name = 'default', 'test_endpoints_name'
        response = api_client.get(
            f'/api/dashboard/projects/{project_id}/clusters/{cluster_id}/'
            + f'namespaces/{namespace}/networks/endpoints/{endpoints_name}/'
        )
        assert response.json()['code'] == 0
