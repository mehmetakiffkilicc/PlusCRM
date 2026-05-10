from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/crm/', include('api.crm_urls')),  # CRM API endpoints
]

# Health check
from django.http import JsonResponse
def health(request):
    return JsonResponse({'status': 'ok', 'message': 'Backend is running'})

urlpatterns += [
    path('health/', health),
]
