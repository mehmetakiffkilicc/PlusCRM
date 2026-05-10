import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from ...models import AINotification
from .tools import detect_anomalies

@api_view(['GET'])
def list_notifications(request):
    """Kullanıcının bildirimlerini listeler."""
    notifications = AINotification.objects.filter(user=request.user).order_by('-created_at')[:50]
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.type,
        'is_read': n.is_read,
        'metadata': n.metadata,
        'created_at': n.created_at
    } for n in notifications]
    return Response({'notifications': data})

@api_view(['POST'])
def mark_notification_as_read(request, pk):
    """Bildirimi okundu olarak işaretler."""
    try:
        notification = AINotification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'status': 'success'})
    except AINotification.DoesNotExist:
        return Response({'status': 'error', 'message': 'Bildirim bulunamadı.'}, status=404)

@api_view(['POST'])
def sync_ai_notifications(request):
    """
    Anomalileri tarar ve yüksek/orta öncelikli olanlar için bildirim oluşturur.
    """
    data_source_id = request.data.get('data_source_id', 0)
    
    # Mevcut anomali tespit tool'unu çalıştır
    anomalies_json = detect_anomalies(int(data_source_id))
    anomalies_data = json.loads(anomalies_json)
    
    new_notifs_count = 0
    for anomaly in anomalies_data.get('anomalies', []):
        if anomaly.get('severity') in ['high', 'medium']:
            # Başlığı güzelleştir
            metric_label = "Toplam Ciro" if anomaly['metric'] == 'totalRevenue' else anomaly['metric']
            type_label = "Düşüş" if anomaly['type'] == 'drop' else "Artış"
            
            title = f"Kritik {type_label}: {metric_label}"
            message = f"{metric_label} metriğinde %{abs(anomaly['change'])} oranında bir {type_label.lower()} tespit edildi. Değer: {anomaly['value']}"
            
            # Taslak kampanya önerisi (Smart-Action)
            campaign_draft = {
                'title': f"{metric_label} Kurtarma Kampanyası",
                'offer': f"{metric_label} verisindeki düşüşü durdurmak için etkilenen segmente özel %10 indirim veya 2 kat bonus puan.",
                'segment': anomaly.get('segment', 'At-Risk Customers'),
                'link': '/kampanya-onerileri'
            }

            # Aynı başlık ve mesajla son 24 saatte bildirim var mı kontrol et
            from django.utils import timezone
            from datetime import timedelta
            yesterday = timezone.now() - timedelta(days=1)
            
            exists = AINotification.objects.filter(
                user=request.user,
                title=title,
                created_at__gte=yesterday
            ).exists()
            
            if not exists:
                AINotification.objects.create(
                    user=request.user,
                    title=title,
                    message=message,
                    type='critical' if anomaly['severity'] == 'high' else 'warning',
                    metadata={
                        'anomaly': anomaly,
                        'campaign_draft': campaign_draft,
                        'link': 'kampanya-onerileri'
                    }
                )
                new_notifs_count += 1
                
    return Response({'status': 'success', 'created_count': new_notifs_count})
