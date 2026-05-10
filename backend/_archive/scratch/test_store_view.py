import os
import django
from django.test import RequestFactory
from django.contrib.auth.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from api.analytics.store_view import get_store_analysis

def test_view():
    factory = RequestFactory()
    user = User.objects.first()
    
    # Test 1: All
    request = factory.get('/api/magaza-analizi/')
    request.user = user
    response = get_store_analysis(request)
    print(f"Total summary: {response.data['summary']}")
    
    # Test 2: 1. Bölge
    request = factory.get('/api/magaza-analizi/', {'region': '1. Bölge'})
    request.user = user
    response = get_store_analysis(request)
    print(f"Region 1 summary: {response.data['summary']}")

if __name__ == "__main__":
    test_view()
