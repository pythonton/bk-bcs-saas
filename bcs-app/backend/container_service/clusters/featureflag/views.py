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
from rest_framework.response import Response

from backend.bcs_web import viewsets

from .featflag import get_cluster_feature_flags
from .serializers import ClusterFeatureTypeSLZ


class ClusterFeatureFlagViewSet(viewsets.SystemViewSet):
    def get_cluster_feature_flags(self, request, project_id, cluster_id):
        validated_data = self.params_validate(ClusterFeatureTypeSLZ, cluster_id=cluster_id)
        feat_flags = get_cluster_feature_flags(cluster_id, validated_data.get('cluster_feature_type'))
        return Response(feat_flags)
