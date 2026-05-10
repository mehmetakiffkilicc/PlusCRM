"""
Dashboard Views (List, Detail, Create, Update, Delete)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Count
from ..serializers import DashboardSerializer, DashboardListSerializer
from ..models import Dashboard
from .base import TokenAuthMixin
import logging

logger = logging.getLogger(__name__)


class DashboardListView(APIView, TokenAuthMixin):
    # Uses default IsAuthenticated from settings

    def get(self, request):
        user = self.try_get_user(request)
        if not user:
            # Token yoksa ilk kullanıcıyı al veya default user oluştur
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        dashboards = Dashboard.objects.filter(user_id=user.id).annotate(widget_count=Count('widgets'))
        serializer = DashboardListSerializer(dashboards, many=True)
        return Response({'dashboards': serializer.data})
    
    def post(self, request):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        name = request.data.get('name')
        description = request.data.get('description')
        
        if not name:
            return Response({'error': 'Dashboard adı gerekli'}, status=HTTP_400_BAD_REQUEST)
        
        dashboard = Dashboard.objects.create(
            user_id=user.id,
            name=name,
            description=description
        )
        
        return Response({
            'message': 'Dashboard başarıyla oluşturuldu',
            'dashboard': DashboardListSerializer(dashboard).data
        }, status=HTTP_201_CREATED)


class DashboardDetailView(APIView, TokenAuthMixin):
    # Uses default IsAuthenticated from settings

    def get(self, request, pk):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        dashboard = get_object_or_404(Dashboard, pk=pk, user_id=user.id)
        serializer = DashboardSerializer(dashboard)
        return Response({'dashboard': serializer.data})
    
    def put(self, request, pk):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        dashboard = get_object_or_404(Dashboard, pk=pk, user_id=user.id)
        
        name = request.data.get('name')
        description = request.data.get('description')
        
        if name:
            dashboard.name = name
        if description is not None:
            dashboard.description = description
        
        dashboard.save()
        return Response({
            'message': 'Dashboard başarıyla güncellendi',
            'dashboard': DashboardSerializer(dashboard).data
        })
    
    def delete(self, request, pk):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        dashboard = get_object_or_404(Dashboard, pk=pk, user_id=user.id)
        dashboard.delete()
        return Response({'message': 'Dashboard başarıyla silindi'})

