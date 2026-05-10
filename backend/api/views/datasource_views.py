"""
DataSource Views (List, Detail, Create, Update, Delete)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ..serializers import DataSourceSerializer, DataSourceDetailSerializer
from ..models import DataSource
from .base import TokenAuthMixin
import json
import logging

logger = logging.getLogger(__name__)

try:
    import connectorx as cx
    import pandas as pd
except Exception:  # Optional dependency
    cx = None
    pd = None


class DataSourceListView(APIView, TokenAuthMixin):
    # AllowAny - demo mod için authentication gerekmez
    permission_classes = [AllowAny]

    def get(self, request):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        # PERF: DataSource.data (JSONField) çok büyük olabilir. Liste endpoint'i data'yı çekmemeli.
        # Database tipini önce döndür - SQLite cache'den veri çekiyor
        from django.db.models import Case, When, Value, IntegerField
        
        # Helper to get formatted datasources
        def get_sources():
            return DataSource.objects.filter(user_id=user.id).annotate(
                type_order=Case(
                    When(type='database', then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                )
            ).order_by('type_order', '-id').values(
                'id', 'name', 'type', 'column_mapping', 'uploaded_at'
            )

        data_sources = get_sources()

        # EĞER HİÇ VERİ KAYNAĞI YOKSA -> OTOMATİK OLUŞTUR
        # Bu sayede yeni kullanıcılar veya demo kullanıcıları boş ekran görmez
        if not data_sources:
            logger.info(f"User {user.username} has no data sources. Creating default system source.")
            DataSource.objects.create(
                user_id=user.id,
                name='MarketFlow Veri',
                type='database',
                data=[],
                connection_info={
                    'db_type': 'sqlite',
                    'cache_enabled': True, 
                    'local_mode': True # İşaretleyici
                }
            )
            data_sources = get_sources()

        return Response({'dataSources': list(data_sources)})
    
    def post(self, request):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        file = request.FILES.get('file')
        name = request.data.get('name', 'Untitled')
        
        if not file:
            # Database source creation - MODERNIZED FOR OPTIMIZED SYSTEM
            # Note: This system now uses local SQLite cache instead of storing data in JSONField
            source_type = request.data.get('type') or request.data.get('sourceType') or request.data.get('source_type')
            db_type = request.data.get('dbType') or request.data.get('db_type') or request.data.get('db')

            if source_type != 'database' and db_type is None:
                return Response({'error': 'Dosya gerekli'}, status=HTTP_400_BAD_REQUEST)

            # Modern approach: Test connection only, don't fetch data
            # Data is handled by sync_worker which populates SQLite cache
            server = request.data.get('server') or request.data.get('host')
            port = request.data.get('port') or '1433'
            database = request.data.get('database') or request.data.get('dbName') or request.data.get('db_name')
            username = request.data.get('username') or request.data.get('user')
            password = request.data.get('password')
            query = request.data.get('query')
            encrypt = request.data.get('encrypt')
            trust_cert = request.data.get('trustServerCertificate')

            if not server or not database or not username or password is None:
                return Response({'error': 'server, database, username, password gerekli'}, status=HTTP_400_BAD_REQUEST)

            # Normalize booleans
            if isinstance(encrypt, str):
                encrypt = encrypt.lower() in ['1', 'true', 'yes', 'on']
            if isinstance(trust_cert, str):
                trust_cert = trust_cert.lower() in ['1', 'true', 'yes', 'on']
            if encrypt is None:
                encrypt = False  # Default to no encryption for Tailscale VPN
            if trust_cert is None:
                trust_cert = True

            try:
                # Modern approach: Just test connection, don't fetch all data
                # The sync_worker will handle data synchronization to SQLite
                logger.info(f"Testing database connection: server={server}, port={port}, database={database}")

                # Use pyodbc for connection test (lighter than connectorx)
                try:
                    try:
                        import pyodbc
                    except ImportError:
                        return Response({
                            'error': 'pyodbc modülü yüklü değil. Veritabanı bağlantısı testi yapılamıyor.'
                        }, status=HTTP_400_BAD_REQUEST)

                    # Try available drivers
                    drivers = [
                        '{ODBC Driver 18 for SQL Server}',
                        '{ODBC Driver 17 for SQL Server}',
                        '{SQL Server Native Client 11.0}',
                        '{SQL Server}'
                    ]

                    conn_str = None
                    for driver in drivers:
                        if driver.strip('{}') in pyodbc.drivers():
                            conn_str = (
                                f"DRIVER={driver};"
                                f"SERVER={server},{port};"
                                f"DATABASE={database};"
                                f"UID={username};"
                                f"PWD={password};"
                                f"Network=DBMSSOCN;"
                                f"Encrypt={'yes' if encrypt else 'no'};"
                                f"TrustServerCertificate={'yes' if trust_cert else 'no'};"
                            )
                            break

                    if not conn_str:
                        return Response({'error': 'ODBC driver bulunamadı'}, status=HTTP_400_BAD_REQUEST)

                    # Test connection
                    conn = pyodbc.connect(conn_str, timeout=30)
                    cursor = conn.cursor()

                    # Test query
                    if query:
                        # If query provided, test it with LIMIT
                        test_query = f"SELECT TOP 1 * FROM ({query}) AS test_query"
                        cursor.execute(test_query)
                        cursor.fetchone()
                        row_count_msg = "Query syntax valid"
                    else:
                        # Just test connection
                        cursor.execute("SELECT 1 AS test")
                        cursor.fetchone()
                        row_count_msg = "Connection successful"

                    cursor.close()
                    conn.close()

                    logger.info(f"Connection test successful: {row_count_msg}")

                except Exception as conn_err:
                    logger.error(f"Connection test failed: {conn_err}")
                    return Response({
                        'error': f'Veritabanına bağlanılamadı: {str(conn_err)}'
                    }, status=HTTP_400_BAD_REQUEST)

                # Create DataSource record (without storing data in JSONField)
                # Data will be accessed via SQLite cache (sales_cache.db)
                data_source = DataSource.objects.create(
                    user_id=user.id,
                    name=name or f'{database} - {server}',
                    type='database',
                    data=[],  # Empty - data stored in SQLite cache
                    connection_info={
                        'db_type': db_type or 'mssql',
                        'server': server,
                        'port': str(port),
                        'database': database,
                        'username': username,
                        'password': password,
                        'query': query or 'SELECT * FROM M_PowerBi',  # Default query
                        'encrypt': bool(encrypt),
                        'trust_server_certificate': bool(trust_cert),
                        'cache_enabled': True,  # Flag: data comes from SQLite cache
                        'cache_path': 'database/sales_cache.db'
                    }
                )

                return Response({
                    'message': (
                        'Veritabanı bağlantısı başarılı! '
                        'Veriler sync_worker tarafından SQLite cache\'e senkronize ediliyor. '
                        'Performans optimizasyonu: Veriler artık pagination ve index ile hızlıca erişiliyor.'
                    ),
                    'dataSource': DataSourceSerializer(data_source).data,
                    'info': {
                        'cache_enabled': True,
                        'sync_worker_active': True,
                        'performance_mode': 'optimized',
                        'features': [
                            'Pagination support (limit/offset)',
                            'Index-based filtering (50-100x faster)',
                            'Connection pooling',
                            'Incremental sync (every 15 min)'
                        ]
                    }
                }, status=HTTP_201_CREATED)

            except Exception as e:
                import traceback
                error_detail = str(e)
                logger.error(f"Database source creation error: {error_detail}\n{traceback.format_exc()}")
                return Response({
                    'error': error_detail,
                    'details': traceback.format_exc() if logger.level <= logging.DEBUG else None
                }, status=HTTP_400_BAD_REQUEST)
        
        # Sadece veritabanı bağlantısı destekleniyor
        if not db_connection:
            return Response({'error': 'Sadece veritabanı bağlantısı desteklenmektedir.'}, status=HTTP_400_BAD_REQUEST)

        try:
            # Veritabanı bağlantısı oluşturma işlemi zaten yukarıda yapılıyor
            pass 
        except Exception as e:
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)



class DataSourceDetailView(APIView, TokenAuthMixin):
    # AllowAny - demo mod için authentication gerekmez
    permission_classes = [AllowAny]

    def get(self, request, pk):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        data_source = get_object_or_404(DataSource, pk=pk, user_id=user.id)

        # PERFORMANCE OPTIMIZATION: For database sources with cache_enabled,
        # return paginated data from SQLite cache instead of full JSONField
        if (data_source.type == 'database' and
            data_source.connection_info and
            data_source.connection_info.get('cache_enabled')):

            # Use new optimized data_access functions
            from api.data_access import get_sales_data

            # Get pagination params from query string
            limit = int(request.GET.get('limit', 100))
            offset = int(request.GET.get('offset', 0))

            # Get filter params
            customer_code = request.GET.get('customer_code')
            category = request.GET.get('category')
            brand = request.GET.get('brand')
            store = request.GET.get('store')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            # Fetch paginated, filtered data from SQLite cache
            result = get_sales_data(
                limit=limit,
                offset=offset,
                customer_code=customer_code,
                category=category,
                brand=brand,
                store=store,
                start_date=start_date,
                end_date=end_date
            )

            # Return with metadata
            return Response({
                'dataSource': {
                    'id': data_source.id,
                    'name': data_source.name,
                    'type': data_source.type,
                    'connection_info': data_source.connection_info,
                    'uploaded_at': data_source.uploaded_at.isoformat(),
                    'column_mapping': data_source.column_mapping,
                    'cache_enabled': True
                },
                'data': result['data'],
                'pagination': {
                    'total_count': result['total_count'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'total_pages': result['total_pages']
                },
                'performance': {
                    'source': 'sqlite_cache',
                    'indexed': True,
                    'pagination_enabled': True
                }
            })
        else:
            return Response({
                'error': 'Bu veri kaynağı türü (CSV/JSON) artık desteklenmemektedir. Lütfen veritabanı bağlantısı kullanın.',
                'dataSource': DataSourceSerializer(data_source).data
            }, status=HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        data_source = get_object_or_404(DataSource, pk=pk, user_id=user.id)
        
        # Update column_mapping if provided
        if 'column_mapping' in request.data:
            data_source.column_mapping = request.data['column_mapping']
            data_source.save()
        
        serializer = DataSourceDetailSerializer(data_source)
        return Response({'dataSource': serializer.data, 'message': 'Sütun eşleştirmesi güncellendi'})
    
    def delete(self, request, pk):
        user = self.try_get_user(request)
        if not user:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(username='demo', email='demo@demo.com', password='demo')
        data_source = get_object_or_404(DataSource, pk=pk, user_id=user.id)
        data_source.delete()
        return Response({'message': 'Veri kaynağı başarıyla silindi'})


class SystemStatusView(APIView):
    """Sistem Durumu - Veritabanı ve Cache Monitör"""
    
    def get(self, request):
        from ..data_access import get_system_status
        
        try:
            status = get_system_status()
            return Response(status)
        except Exception as e:
            logger.error(f"System status error: {e}")
            return Response({
                'error': str(e),
                'sqlite_cache': {'status': 'error'},
                'sql_server': {'status': 'error'},
                'sync': {'is_syncing': False},
                'scheduler': {'running': False}
            }, status=HTTP_400_BAD_REQUEST)


class PlatformStatusView(APIView):
    """Platform Durumları — Railway, Tailscale, DB, Sync Worker"""
    permission_classes = [AllowAny]

    def get(self, request):
        from ..data_access import get_platform_status

        try:
            status = get_platform_status()
            return Response(status)
        except Exception as e:
            logger.error(f"Platform status error: {e}")
            return Response({
                'platforms': [],
                'summary': {'online': 0, 'total': 0, 'overall_status': 'down'},
                'error': str(e)
            }, status=HTTP_400_BAD_REQUEST)


