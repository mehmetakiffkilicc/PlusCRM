import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from ...models import ScheduledCampaign
from django.utils import timezone

@api_view(['GET'])
def get_scheduled_campaigns(request):
    """Bekleyen ve son tamamlanan kampanyaları listeler."""
    campaigns = ScheduledCampaign.objects.filter(user=request.user).order_by('scheduled_at')[:50]
    data = [{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'segment': c.segment,
        'channel': c.channel,
        'scheduled_at': c.scheduled_at,
        'status': c.status,
        'created_at': c.created_at
    } for c in campaigns]
    return Response({'campaigns': data})

@api_view(['POST'])
def schedule_campaign_view(request):
    """Yeni bir kampanya planlar."""
    data = request.data
    
    try:
        # Tarih formatı kontrolü veya varsayılan (örn: yarın bu saat)
        scheduled_at = data.get('scheduled_at')
        if not scheduled_at:
            scheduled_at = timezone.now() + timezone.timedelta(days=1)
            
        campaign = ScheduledCampaign.objects.create(
            user=request.user,
            title=data.get('title', 'Yeni Kampanya'),
            description=data.get('description', ''),
            segment=data.get('segment', 'Tüm Müşteriler'),
            channel=data.get('channel', 'email'),
            scheduled_at=scheduled_at,
            status='pending'
        )
        
        return Response({
            'status': 'success',
            'campaign_id': campaign.id,
            'message': 'Kampanya başarıyla planlandı.'
        })
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)

@api_view(['DELETE', 'POST'])
def delete_scheduled_campaign(request, pk):
    """Planlanmış bir kampanyayı iptal eder veya siler."""
    try:
        campaign = ScheduledCampaign.objects.get(pk=pk, user=request.user)
        # Eğer POST ise iptal et, DELETE ise sil
        if request.method == 'POST':
            campaign.status = 'cancelled'
            campaign.save()
            return Response({'status': 'success', 'message': 'Kampanya iptal edildi.'})
        else:
            campaign.delete()
            return Response({'status': 'success', 'message': 'Kampanya silindi.'})
    except ScheduledCampaign.DoesNotExist:
        return Response({'status': 'error', 'message': 'Kampanya bulunamadı.'}, status=404)

@api_view(['POST'])
def run_scheduled_campaign(request, pk):
    """Planlanmış bir kampanyayı şimdi yürütür (Simülasyon)."""
    try:
        campaign = ScheduledCampaign.objects.get(pk=pk, user=request.user)
        if campaign.status == 'completed':
            return Response({'status': 'error', 'message': 'Kampanya zaten tamamlanmış.'}, status=400)
            
        campaign.status = 'completed'
        # Simülasyon: Gerçek sistemde burada Twilio/SendGrid vb. tetiklenir
        campaign.save()
        
        return Response({
            'status': 'success', 
            'message': f'"{campaign.title}" kampanyası başarıyla yürütüldü.',
            'timestamp': timezone.now()
        })
    except ScheduledCampaign.DoesNotExist:
        return Response({'status': 'error', 'message': 'Kampanya bulunamadı.'}, status=404)
