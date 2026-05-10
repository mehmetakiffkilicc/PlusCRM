from rest_framework.decorators import api_view
from rest_framework.response import Response
from ...models import AIDashboard
from django.shortcuts import get_object_or_404

@api_view(['GET'])
def list_ai_dashboards(request):
    dashboards = AIDashboard.objects.filter(user=request.user)
    return Response({
        "status": "success",
        "dashboards": [{
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "is_favorite": d.is_favorite,
            "config": d.config,
            "created_at": d.created_at
        } for d in dashboards]
    })

@api_view(['GET'])
def get_ai_dashboard(request, dashboard_id):
    dashboard = get_object_or_404(AIDashboard, id=dashboard_id, user=request.user)
    return Response({
        "status": "success",
        "dashboard": {
            "id": dashboard.id,
            "name": dashboard.name,
            "description": dashboard.description,
            "config": dashboard.config,
            "is_favorite": dashboard.is_favorite
        }
    })

@api_view(['DELETE'])
def delete_ai_dashboard(request, dashboard_id):
    dashboard = get_object_or_404(AIDashboard, id=dashboard_id, user=request.user)
    dashboard.delete()
    return Response({"status": "success", "message": "Dashboard silindi."})

@api_view(['POST'])
def toggle_ai_dashboard_favorite(request, dashboard_id):
    dashboard = get_object_or_404(AIDashboard, id=dashboard_id, user=request.user)
    dashboard.is_favorite = not dashboard.is_favorite
    dashboard.save()
    return Response({"status": "success", "is_favorite": dashboard.is_favorite})
