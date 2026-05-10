import os
import sys
import django
from django.test import RequestFactory
from rest_framework.response import Response

# Add the project directory to sys.path
sys.path.append('c:\\Users\\Akif\\Desktop\\BackendFronend\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from api.analytics.dashboard_view import dashboard_sqlite_direct

def test_dashboard_direct():
    factory = APIRequestFactory()
    # Test for year 2026
    request = factory.get('/api/panel-sqlite/', {'year': '2026'})
    
    from django.contrib.auth.models import User
    user = User.objects.first()
    force_authenticate(request, user=user)
    
    response = dashboard_sqlite_direct(request)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.data
        print(f"Total Revenue: {data.get('totalRevenue')}")
        print(f"Total Receipts: {data.get('totalReceipts')}")
        print(f"Total Customers: {data.get('totalCustomers')}")
        print(f"Sales By Month (count): {len(data.get('salesByMonth', []))}")
        print(f"Customer Segments (count): {len(data.get('customerSegments', []))}")
        
        if len(data.get('salesByMonth', [])) > 0:
            print(f"First month sales: {data['salesByMonth'][0]}")
    else:
        print(f"Error: {response.data}")

if __name__ == "__main__":
    test_dashboard_direct()
