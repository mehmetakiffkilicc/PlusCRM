from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from ..models import SystemSetting, DataSource
from ..serializers import SystemSettingSerializer
import logging

logger = logging.getLogger(__name__)

class SettingsView(APIView):
    """
    Uygulama genel ayarlarını yöneten view.
    GET: Tüm ayarları getirir.
    POST: Ayarları günceller veya yeni ayar ekler.
    """
    permission_classes = [AllowAny] # Demo mod için

    def get(self, request):
        try:
            # Varsayılan ayarları kontrol et ve yoksa oluştur
            self._ensure_default_settings()
            
            settings = SystemSetting.objects.all()
            serializer = SystemSettingSerializer(settings, many=True)
            
            # Key-value şeklinde objeye dönüştür
            settings_dict = {s['key']: s['value'] for s in serializer.data}
            
            return Response(settings_dict)
        except Exception as e:
            logger.error(f"SettingsView GET error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """
        Settings objesi içinde key-value çiftleri bekler.
        Örn: {"crm_name": "My CRM", "currency": "USD"}
        """
        try:
            data = request.data
            updated_settings = []
            
            for key, value in data.items():
                setting, created = SystemSetting.objects.update_or_create(
                    key=key,
                    defaults={'value': value}
                )
                updated_settings.append(setting)
            
            return Response({
                'message': 'Ayarlar başarıyla güncellendi',
                'count': len(updated_settings)
            })
        except Exception as e:
            logger.error(f"SettingsView POST error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _ensure_default_settings(self):
        defaults = {
            'crm_name': {'name': 'XPlusCRM', 'logo': ''},
            'localization': {'currency': 'TRY', 'language': 'tr', 'date_format': 'DD.MM.YYYY'},
            'appearance': {'primary_color': '#4c6ef5', 'theme': 'light'},
            'system': {'sync_frequency': '15', 'auto_sync': True, 'log_retention_days': 30},
        }
        
        for key, value in defaults.items():
            if not SystemSetting.objects.filter(key=key).exists():
                SystemSetting.objects.create(key=key, value=value)
