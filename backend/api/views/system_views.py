from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .. import db_engine
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rebuild_kpi_cache(request):
    """KPI cache'ini yeniden hesaplar. Giriş yapmış kullanıcılar tetikleyebilir."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from rebuild_cache_kpi import rebuild_cache
        rebuild_cache()
        return Response({'status': 'ok', 'message': 'KPI cache yeniden oluşturuldu'})
    except Exception as e:
        logger.error(f"Cache rebuild hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_system_logs(request):
    """Sistem loglarını veritabanından getirir. JWT ile korunur."""
    limit = int(request.GET.get('limit', 500))
    service = request.GET.get('service') # Opsiyonel: backend veya worker

    query = "SELECT * FROM system_logs"
    params = []
    
    if service:
        query += " WHERE service_name = %s" if db_engine.DB_BACKEND == 'postgresql' else " WHERE service_name = ?"
        params.append(service)
        
    query += " ORDER BY timestamp DESC LIMIT "
    query += "%s" if db_engine.DB_BACKEND == 'postgresql' else "?"
    params.append(limit)

    try:
        logs = db_engine.execute_query(query, params)
        return Response({
            'count': len(logs),
            'logs': logs
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_system_logs(request):
    """Log tablosunu temizle. JWT ile korunur."""
        
    try:
        db_engine.execute_query("DELETE FROM system_logs", fetch=False)
        return Response({'status': 'Logs cleared'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
