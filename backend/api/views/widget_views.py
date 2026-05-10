"""
Widget and Misc Views (Create, Delete, Query, SyncStatus)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ..serializers import WidgetSerializer
from ..models import DataSource, Dashboard, Widget
from .base import TokenAuthMixin
import logging

logger = logging.getLogger(__name__)


class WidgetCreateView(APIView, TokenAuthMixin):
    # Uses default IsAuthenticated from settings

    def post(self, request, dashboard_id):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        dashboard = get_object_or_404(Dashboard, pk=dashboard_id, user_id=user.id)
        
        data_source_id = request.data.get('dataSourceId')
        widget_type = request.data.get('type')
        title = request.data.get('title')
        x_axis = request.data.get('xAxis')
        y_axis = request.data.get('yAxis')
        aggregation = request.data.get('aggregation')
        filters = request.data.get('filters', {})
        
        if not all([data_source_id, widget_type, title]):
            return Response({'error': 'dataSourceId, type ve title gerekli'}, status=HTTP_400_BAD_REQUEST)
        
        data_source = get_object_or_404(DataSource, pk=data_source_id, user_id=user.id)
        
        widget = Widget.objects.create(
            dashboard=dashboard,
            data_source=data_source,
            type=widget_type,
            title=title,
            x_axis=x_axis,
            y_axis=y_axis,
            aggregation=aggregation,
            filters=filters
        )
        
        return Response({
            'message': 'Widget başarıyla eklendi',
            'widget': WidgetSerializer(widget).data
        }, status=HTTP_201_CREATED)


class WidgetDeleteView(APIView, TokenAuthMixin):
    # Uses default IsAuthenticated from settings

    def delete(self, request, dashboard_id, widget_id):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        dashboard = get_object_or_404(Dashboard, pk=dashboard_id, user_id=user.id)
        widget = get_object_or_404(Widget, pk=widget_id, dashboard=dashboard)
        widget.delete()
        return Response({'message': 'Widget başarıyla silindi'})




class SyncStatusView(APIView, TokenAuthMixin):
    # Uses default IsAuthenticated from settings

    def get(self, request):
        from api.data_access import get_sync_status
        status = get_sync_status()
        return Response(status)


# Query View
class QueryView(APIView, TokenAuthMixin):
    # Uses default IsAuthenticated from settings

    def post(self, request):
        return Response({
            'error': 'Bu endpoint (QueryView) eski CSV veri yapısı için tasarlanmıştır ve artık kullanılmamaktadır. Lütfen analitik endpointlerini kullanın.'
        }, status=HTTP_400_BAD_REQUEST)
