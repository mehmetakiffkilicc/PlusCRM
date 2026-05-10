from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
import logging
from datetime import datetime
from .. import db_engine

logger = logging.getLogger(__name__)

# Geçerli DB status değerleri: 'Bekliyor', 'Onaylandi', 'Reddedildi', 'Tamamlandi'
# Frontend doğrudan bu değerleri gönderiyor — eski Türkçe etiketler ('Bekleyenler' vb.) kaldırıldı.
def normalize_status(status: str):
    """
    'Tümü' veya boş → None (WHERE filtresi eklenmez, tüm kayıtlar gelir).
    Diğer değerler doğrudan DB'ye geçirilir.
    """
    if not status or status == 'Tümü':
        return None
    return status

def get_db_connection():
    return db_engine.get_connection()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_campaign_recommendations(request):
    """
    Kampanya önerilerini sayfalanmış ve optimize edilmiş şekilde getirir
    """
    # Parametreleri al
    status = normalize_status(request.GET.get('status', 'Bekliyor'))
    camp_type = request.GET.get('type')
    category = request.GET.get('category')
    buyer = request.GET.get('yonetici') or request.GET.get('buyer')
    brand = request.GET.get('brand')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    offset = (page - 1) * limit

    logger.info(f"FETCH_RECS: status={status} type={camp_type} cat={category} p={page} l={limit}")

    import time
    start_time = time.time()

    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        # Optimize sütun listesi
        # PostgreSQL'de küçük harf, SQLite'da PascalCase olabilir ama db_engine.val hallediyor.
        # Tablo adını PostgreSQL uyumluluğu için küçük harf yapıyoruz.
        table_name = "otomatikkampanyaonerileri"

        cols = [
            "oneri_id", "olusturma_tarihi", "kampanya_tipi", "hedef_segment",
            "hedef_musteri_sayisi", "oncelik_seviye", "urun_ad", "kategori_ad",
            "ikinci_urun_ad", "gerekcesi", "veri_ozeti", "onerilen_indirim",
            "onerilen_min_tutar", "gecerlilik_suresi", "tahmini_katilim",
            "potansiyel_ciro", "birlikte_ciro", "mevcut_birlikte_ciro", "roi_tahmini", "tahmini_kar", "beklenen_sonuc", "oneri_durumu",
            "lift", "guven", "fis_sayisi", "onerilen_urunler", "kaynak_kategori_ad"
        ]

        # Base query parts
        where_parts = ["1=1"]
        params = []

        if status:
            where_parts.append(f"oneri_durumu = {db_engine.ph()}")
            params.append(status)
        
        if camp_type and camp_type != 'Tümü':
            where_parts.append(f"kampanya_tipi = {db_engine.ph()}")
            params.append(camp_type)
            
        if category and category != 'all':
            where_parts.append(f"kaynak_kategori_ad = {db_engine.ph()}")
            params.append(category)
            
        if buyer and buyer != 'all':
            where_parts.append(f"yonetici_id = {db_engine.ph()}")
            params.append(buyer)
            
        if brand and brand != 'all':
            brand_both_sides = request.GET.get('brand_both_sides', 'false').lower() == 'true'
            ph = db_engine.ph()
            if brand_both_sides:
                ph2 = db_engine.ph()
                where_parts.append(f"kaynak_marka_id = {ph} AND hedef_marka_id = {ph2}")
                params.append(brand)
                params.append(brand)
            else:
                where_parts.append(f"kaynak_marka_id = {ph}")
                params.append(brand)

        min_lift = float(request.GET.get('min_lift', 0) or 0)
        min_confidence = float(request.GET.get('min_confidence', 0) or 0)
        min_fis = int(request.GET.get('min_fis', 0) or 0)

        if min_lift > 0:
            where_parts.append(f"lift >= {db_engine.ph()}")
            params.append(min_lift)
        if min_confidence > 0:
            where_parts.append(f"guven >= {db_engine.ph()}")
            params.append(min_confidence)
        if min_fis > 0:
            where_parts.append(f"fis_sayisi >= {db_engine.ph()}")
            params.append(min_fis)

        where_clause = " WHERE " + " AND ".join(where_parts)
        
        # Toplam sayıyı al
        count_query = f"SELECT COUNT(*) as total FROM {table_name}{where_clause}"
        logger.info(f"COUNT_QUERY: {count_query} params={params}")
        cursor.execute(count_query, params)
        total_count = db_engine.val(cursor.fetchone(), 'total', 0)

        sort_by = request.GET.get('sort_by', 'default')
        sort_order = request.GET.get('sort_order', 'DESC').upper()
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'DESC'
            
        # Sorting mapping
        sort_map = {
            'lift': 'lift',
            'confidence': 'guven',
            'guven': 'guven',
            'fis': 'fis_sayisi',
            'fis_sayisi': 'fis_sayisi',
            'ciro': 'potansiyel_ciro',
            'kar': 'tahmini_kar',
            'tarih': 'olusturma_tarihi'
        }
        
        # Veriyi çek
        col_str = ', '.join([f't.{c}' for c in cols])

        if sort_by == 'ciro' or sort_by == 'potansiyel_ciro':
            # CTE ile grup toplamına göre sırala — params tek kez kullanılır
            query = f"""
                WITH filtered AS (
                    SELECT {', '.join(cols)}
                    FROM {table_name}{where_clause}
                ),
                grup_ciro AS (
                    SELECT kaynak_kategori_ad, SUM(potansiyel_ciro) as toplam_ciro
                    FROM filtered
                    GROUP BY kaynak_kategori_ad
                )
                SELECT {', '.join([f'f.{c}' for c in cols])}
                FROM filtered f
                JOIN grup_ciro g ON f.kaynak_kategori_ad = g.kaynak_kategori_ad
                ORDER BY g.toplam_ciro {sort_order} NULLS LAST, f.potansiyel_ciro {sort_order} NULLS LAST
            """
        elif sort_by in sort_map:
            query = f"SELECT {', '.join(cols)} FROM {table_name}{where_clause} ORDER BY {sort_map[sort_by]} {sort_order} NULLS LAST"
        else:
            # Default sorting
            query = f"SELECT {', '.join(cols)} FROM {table_name}{where_clause} ORDER BY lift DESC NULLS LAST, guven DESC NULLS LAST, fis_sayisi DESC NULLS LAST"
        query += f" LIMIT {limit} OFFSET {offset}"
        
        logger.info(f"DATA_QUERY: {query} params={params}")
        sql_start = time.time()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        sql_end = time.time()
        logger.info(f"ROWS_FETCHED: {len(rows)} in {sql_end-sql_start:.3f}s")

        
        if not rows and offset == 0:
            logger.warning(f"No recommendations found: status='{status}', table='{table_name}'")
        else:
            logger.info(f"Fetched {len(rows)}/{total_count} recommendations from {table_name} ({db_engine.DB_BACKEND})")
        
        # db_engine.release_connection(conn) # Moved to finally

        if not rows and offset == 0:
            logger.warning(f"No campaign recommendations found for status={status}, type={camp_type}, category={category}")
        else:
            logger.info(f"Fetched {len(rows)}/{total_count} recommendations in {sql_end-sql_start:.3f}s (Backend: {db_engine.DB_BACKEND})")

        # Mod B aktifse: kategori → marka ürünleri mapping'i önceden hazırla
        import json as _json2
        brand_category_products = None  # {kategori_ad: [{id, ad}, ...]}
        if brand and brand != 'all' and request.GET.get('brand_both_sides', 'false').lower() == 'true':
            # O markanın ürünlerini kategorileriyle birlikte çek (sınır yok)
            cursor.execute(f"""
                SELECT u.id, u.ad, k.alt2 as kategori
                FROM urunler u
                JOIN kategoriler k ON k.id = u.kategori_id
                WHERE u.marka_id = {db_engine.ph()} AND k.alt2 IS NOT NULL
            """, [int(brand)])
            brand_category_products = {}
            for r in cursor.fetchall():
                kat = db_engine.val(r, 'kategori')
                if kat not in brand_category_products:
                    brand_category_products[kat] = []
                brand_category_products[kat].append({
                    'id': db_engine.val(r, 'id'),
                    'ad': db_engine.val(r, 'ad'),
                    'ciro': 0,
                    'ort': 0
                })
            logger.info(f"BRAND_FILTER_MOD_B: brand={brand} categories={list(brand_category_products.keys())[:5]}")

        recommendations = []
        mod_b_updates = []  # (onerilen_urunler_json, oneri_id) — batch UPDATE için
        for row in rows:
            onerilen_urunler_raw = row.get('onerilen_urunler') or '[]'
            if brand_category_products is not None:
                try:
                    kategori_adi = db_engine.val(row, 'kategori_ad', default='')
                    marka_urunleri = brand_category_products.get(kategori_adi, [])
                    if not marka_urunleri:
                        continue  # Hedef kategoride markanın ürünü yoksa bu kampanyayı atla
                    onerilen_urunler_out = _json2.dumps(marka_urunleri, ensure_ascii=False)
                    urun_adi = marka_urunleri[0]['ad']
                    oneri_id = db_engine.val(row, 'oneri_id')
                    if oneri_id:
                        mod_b_updates.append((onerilen_urunler_out, int(oneri_id)))
                except Exception as e:
                    logger.warning(f"BRAND_FILTER_MOD_B_ERR: {e}")
                    onerilen_urunler_out = onerilen_urunler_raw
                    urun_adi = db_engine.val(row, 'urun_ad', default='')
            else:
                onerilen_urunler_out = onerilen_urunler_raw
                urun_adi = db_engine.val(row, 'urun_ad', default='')

            # db_engine.val ensures mapping from any DB column name to frontend PascalCase
            recommendations.append({
                'OneriID': db_engine.val(row, 'oneri_id', default=0),
                'OlusturmaTarihi': db_engine.val(row, 'olusturma_tarihi', default=''),
                'KampanyaTipi': db_engine.val(row, 'kampanya_tipi', default=''),
                'HedefSegment': db_engine.val(row, 'hedef_segment', default=''),
                'HedefMusteriSayisi': db_engine.val(row, 'hedef_musteri_sayisi', default=0),
                'OncelikSeviye': db_engine.val(row, 'oncelik_seviye', default=3),
                'UrunAdi': urun_adi,
                'KategoriAdi': db_engine.val(row, 'kategori_ad', default=''),
                'IkinciUrunAdi': db_engine.val(row, 'ikinci_urun_ad', default=''),
                'Gerekcesi': db_engine.val(row, 'gerekcesi', default=''),
                'VeriOzeti': db_engine.val(row, 'veri_ozeti', default=''),
                'OnerilenIndirim': db_engine.val(row, 'onerilen_indirim', default=0),
                'OnerilenMinTutar': db_engine.val(row, 'onerilen_min_tutar', default=0),
                'GecerlilikSuresi': db_engine.val(row, 'gecerlilik_suresi', default=7),
                'TahminiKatilim': db_engine.val(row, 'tahmini_katilim', default=0),
                'PotansiyelCiro': db_engine.val(row, 'potansiyel_ciro', default=0),
                'BirlikteCiro': db_engine.val(row, 'birlikte_ciro', default=0),
                'MevcutBirlikteCiro': db_engine.val(row, 'mevcut_birlikte_ciro', default=0),
                'RoiTahmini': db_engine.val(row, 'roi_tahmini', default=0),
                'TahminiKar': db_engine.val(row, 'tahmini_kar', default=0),
                'BeklenenSonuc': db_engine.val(row, 'beklenen_sonuc', default=''),
                'OneriDurumu': db_engine.val(row, 'oneri_durumu', default='Bekliyor'),
                'Lift': db_engine.val(row, 'lift', default=0),
                'Guven': db_engine.val(row, 'guven', default=0),
                'FisSayisi': db_engine.val(row, 'fis_sayisi', default=0),
                'OnerilenUrunler': onerilen_urunler_out,
                'KaynakKategoriAd': db_engine.val(row, 'kaynak_kategori_ad', default='')
            })

        # Mod B: filtrelenmiş onerilen_urunler'i DB'ye kaydet (for döngüsü dışında)
        if mod_b_updates:
            try:
                ph = db_engine.ph()
                for onerilen_json, oneri_id in mod_b_updates:
                    cursor.execute(
                        f"UPDATE otomatikkampanyaonerileri SET onerilen_urunler = {ph} WHERE oneri_id = {ph}",
                        [onerilen_json, oneri_id]
                    )
                conn.commit()
                logger.info(f"BRAND_FILTER_MOD_B_SAVED: {len(mod_b_updates)} rows updated")
            except Exception as e:
                logger.warning(f"BRAND_FILTER_MOD_B_SAVE_ERR: {e}")
            
        total_time = time.time() - start_time
        logger.info(f"PERF: get_campaign_recommendations status={status} type={camp_type} TOTAL={total_time:.3f}s SQL={sql_end-sql_start:.3f}s COUNT={len(recommendations)}")
        
        # Son kampanya yenileme tarihini syncmeta'dan al
        last_refreshed = None
        is_stale = False
        try:
            cursor.execute(f"SELECT value FROM syncmeta WHERE key = 'last_campaign_refresh'")
            meta_row = cursor.fetchone()
            if meta_row:
                last_refreshed = db_engine.val(meta_row, 'value', default=None)
            
            # Eğer son yenileme 7 günden eski ise eskime uyarısı ver
            if last_refreshed:
                try:
                    from datetime import datetime as _dt, timedelta
                    last_dt = _dt.strptime(str(last_refreshed)[:19], '%Y-%m-%d %H:%M:%S')
                    days_since = (_dt.now() - last_dt).days
                    is_stale = days_since >= 7
                    
                    # 7+ gün eskiyse arka planda otomatik yenileme tetikle
                    if is_stale:
                        logger.info(f"⚠️ Kampanyalar {days_since} gündür güncellenmemiş — arka plan yenilemesi tetikleniyor.")
                        import threading
                        def auto_refresh():
                            try:
                                import sys as _sys2, os as _os2
                                project_root = _os2.path.dirname(_os2.path.dirname(_os2.path.dirname(_os2.path.dirname(_os2.path.abspath(__file__)))))
                                if project_root not in _sys2.path:
                                    _sys2.path.insert(0, project_root)
                                from database.campaign_manager import kampanya_onerileri_uret
                                kampanya_onerileri_uret()
                                logger.info("✅ Otomatik kampanya yenilemesi tamamlandı.")
                            except Exception as e:
                                logger.error("Kampanya auto-refresh hatası: %s", str(e), exc_info=True)
                        threading.Thread(target=auto_refresh, daemon=True).start()
                except Exception:
                    pass
            else:
                is_stale = True  # Hiç yenilenmemişse uyarı ver
        except Exception as e:
            logger.warning(f"Syncmeta last_campaign_refresh sorgusu hatası: {e}")

        return Response({
            'status': 'success',
            'count': len(recommendations),
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'backend': db_engine.DB_BACKEND,
            'last_refreshed': last_refreshed,
            'is_stale': is_stale,
            'recommendations': recommendations
        }, status=HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_campaign_recommendations: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_campaign_source_categories(request):
    """
    Kaynak kategorileri sayfalanmış döndürür (her kategori için toplam kampanya, ciro, hedef kitle)
    """
    status = normalize_status(request.GET.get('status', 'Bekliyor'))
    camp_type = request.GET.get('type', 'Cross-Sell')
    buyer = request.GET.get('yonetici') or request.GET.get('buyer')
    brand = request.GET.get('brand')
    brand_both_sides = request.GET.get('brand_both_sides', 'false').lower() == 'true'
    min_lift = float(request.GET.get('min_lift', 0) or 0)
    min_confidence = float(request.GET.get('min_confidence', 0) or 0)
    min_fis = int(request.GET.get('min_fis', 0) or 0)
    sort_by = request.GET.get('sort_by', 'ciro')
    sort_order = 'DESC' if request.GET.get('sort_order', 'desc').lower() == 'desc' else 'ASC'
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    offset = (page - 1) * limit

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()

        if status:
            where_parts = [f"oneri_durumu = {ph}", f"kampanya_tipi = {ph}"]
            params = [status, camp_type]
        else:
            where_parts = [f"kampanya_tipi = {ph}"]
            params = [camp_type]

        if buyer and buyer != 'all':
            where_parts.append(f"yonetici_id = {ph}")
            params.append(buyer)
        if brand and brand != 'all':
            if brand_both_sides:
                where_parts.append(f"kaynak_marka_id = {ph} AND hedef_marka_id = {ph}")
                params.extend([brand, brand])
            else:
                where_parts.append(f"kaynak_marka_id = {ph}")
                params.append(brand)
        if min_lift > 0:
            where_parts.append(f"lift >= {ph}")
            params.append(min_lift)
        if min_confidence > 0:
            where_parts.append(f"guven >= {ph}")
            params.append(min_confidence / 100.0)
        if min_fis > 0:
            where_parts.append(f"fis_sayisi >= {ph}")
            params.append(min_fis)

        where_clause = " WHERE " + " AND ".join(where_parts)

        sort_col = {
            'ciro': 'toplam_ciro',
            'musteri': 'toplam_hedef',
            'fis': 'toplam_fis',
            'kampanya': 'kampanya_sayisi',
        }.get(sort_by, 'toplam_ciro')

        cursor.execute(f"""
            WITH ranked AS (
                SELECT kaynak_kategori_ad, potansiyel_ciro, hedef_musteri_sayisi, fis_sayisi,
                       ROW_NUMBER() OVER (
                           PARTITION BY kaynak_kategori_ad
                           ORDER BY lift DESC NULLS LAST, guven DESC NULLS LAST, fis_sayisi DESC NULLS LAST
                       ) AS rn
                FROM otomatikkampanyaonerileri
                {where_clause}
                AND kaynak_kategori_ad IS NOT NULL
            )
            SELECT kaynak_kategori_ad,
                   COUNT(*) as kampanya_sayisi,
                   SUM(potansiyel_ciro) as toplam_ciro,
                   MAX(hedef_musteri_sayisi) as toplam_hedef,
                   SUM(fis_sayisi) as toplam_fis
            FROM ranked
            WHERE rn <= 15
            GROUP BY kaynak_kategori_ad
            ORDER BY {sort_col} {sort_order} NULLS LAST
            LIMIT {ph} OFFSET {ph}
        """, params + [limit, offset])
        rows = cursor.fetchall()

        cursor.execute(f"""
            SELECT COUNT(DISTINCT kaynak_kategori_ad) as total
            FROM otomatikkampanyaonerileri
            {where_clause}
            AND kaynak_kategori_ad IS NOT NULL
        """, params)  # Kategori sayısı değişmez, sadece içerideki kampanya sayısı 15 ile sınırlı
        total = db_engine.val(cursor.fetchone(), 'total', 0)

        categories = []
        for r in rows:
            categories.append({
                'kaynak_kategori_ad': db_engine.val(r, 'kaynak_kategori_ad'),
                'kampanya_sayisi': db_engine.val(r, 'kampanya_sayisi', 0),
                'toplam_ciro': float(db_engine.val(r, 'toplam_ciro') or 0),
                'toplam_hedef': int(db_engine.val(r, 'toplam_hedef') or 0),
                'toplam_fis': int(db_engine.val(r, 'toplam_fis') or 0),
            })

        return Response({
            'categories': categories,
            'total_count': total,
            'page': page,
            'has_more': (offset + limit) < total,
        }, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"get_campaign_source_categories error: {e}")
        return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_campaign_counts(request):
    """
    Tüm kampanya tipleri için toplam sayıları döner
    """
    status = normalize_status(request.GET.get('status', 'Bekliyor'))

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)

        table_name = "otomatikkampanyaonerileri"
        ph = db_engine.ph()

        # Her kampanya tipi + kategori kombinasyonu için max 15 alarak gerçek gösterim sayısını hesapla
        if status:
            where = f"WHERE oneri_durumu = {ph}"
            base_params = [status]
        else:
            where = ""
            base_params = []

        cte_query = f"""
            WITH ranked AS (
                SELECT kampanya_tipi,
                       ROW_NUMBER() OVER (
                           PARTITION BY kampanya_tipi, kaynak_kategori_ad
                           ORDER BY lift DESC NULLS LAST, guven DESC NULLS LAST, fis_sayisi DESC NULLS LAST
                       ) AS rn
                FROM {table_name}
                {where}
            )
            SELECT kampanya_tipi, COUNT(*) as count
            FROM ranked
            WHERE rn <= 15
            GROUP BY kampanya_tipi
        """
        cursor.execute(cte_query, base_params)
        rows = cursor.fetchall()

        counts = {row['kampanya_tipi']: row['count'] for row in rows}

        total_query = f"""
            WITH ranked AS (
                SELECT ROW_NUMBER() OVER (
                           PARTITION BY kampanya_tipi, kaynak_kategori_ad
                           ORDER BY lift DESC NULLS LAST, guven DESC NULLS LAST, fis_sayisi DESC NULLS LAST
                       ) AS rn
                FROM {table_name}
                {where}
            )
            SELECT COUNT(*) as total FROM ranked WHERE rn <= 15
        """
        cursor.execute(total_query, base_params)
        total_count = db_engine.val(cursor.fetchone(), 'total', 0)
        counts['Tümü'] = total_count
        
        return Response(counts, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching campaign counts: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_campaign_filter_counts(request):
    """
    Yönetici, marka (Mod A + Mod B) ve kategori bazında kampanya sayılarını döner
    """
    status = normalize_status(request.GET.get('status', 'Bekliyor'))
    camp_type = request.GET.get('type', 'Cross-Sell')
    ph = db_engine.ph()

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)
        # status=None means 'Tümü' (no filter)
        if status:
            base_params = [status, camp_type]
            w = f"oneri_durumu = {ph} AND kampanya_tipi = {ph}"
        else:
            base_params = [camp_type]
            w = f"kampanya_tipi = {ph}"

        # Yönetici sayıları
        yonetici_counts = {}
        try:
            cursor.execute(f"SELECT yonetici_id, COUNT(*) as cnt FROM otomatikkampanyaonerileri WHERE {w} AND yonetici_id IS NOT NULL GROUP BY yonetici_id", base_params)
            yonetici_counts = {str(r['yonetici_id']): r['cnt'] for r in cursor.fetchall()}
        except Exception as e:
            logger.warning(f"yonetici counts error: {e}")

        # Kategori sayıları — alt2 (kaynak_kategori_ad) + alt1 + ana toplamaları
        kategori_counts = {}
        try:
            cursor.execute(f"SELECT kaynak_kategori_ad, COUNT(*) as cnt FROM otomatikkampanyaonerileri WHERE {w} AND kaynak_kategori_ad IS NOT NULL GROUP BY kaynak_kategori_ad", base_params)
            kategori_counts = {r['kaynak_kategori_ad']: r['cnt'] for r in cursor.fetchall()}
        except Exception as e:
            logger.warning(f"kategori counts error: {e}")
        try:
            # alt1 toplamları: o alt1 altındaki tüm alt2'lerin sayısı
            cursor.execute(f"""
                SELECT k.alt1, COUNT(*) as cnt
                FROM otomatikkampanyaonerileri o
                JOIN kategoriler k ON o.kaynak_kategori_ad = k.alt2
                WHERE {w} AND k.alt1 IS NOT NULL
                GROUP BY k.alt1
            """, base_params)
            for r in cursor.fetchall():
                if r['alt1'] and r['cnt']:
                    kategori_counts[r['alt1']] = r['cnt']
        except Exception as e:
            logger.warning(f"alt1 counts error: {e}")
        try:
            # ana toplamları: o ana altındaki tüm kategorilerin sayısı
            cursor.execute(f"""
                SELECT k.ana, COUNT(*) as cnt
                FROM otomatikkampanyaonerileri o
                JOIN kategoriler k ON o.kaynak_kategori_ad = k.alt2
                WHERE {w} AND k.ana IS NOT NULL
                GROUP BY k.ana
            """, base_params)
            for r in cursor.fetchall():
                if r['ana'] and r['cnt']:
                    kategori_counts[r['ana']] = r['cnt']
        except Exception as e:
            logger.warning(f"ana counts error: {e}")

        # Marka Mod A: kaynak_marka_id kolonundan direkt say (lift >= 2, fis >= 500)
        marka_a_counts = {}
        marka_b_counts = {}
        try:
            cursor.execute(f"""
                SELECT kaynak_marka_id, COUNT(*) as cnt
                FROM otomatikkampanyaonerileri
                WHERE {w} AND kaynak_marka_id = hedef_marka_id
                GROUP BY kaynak_marka_id
            """, base_params)
            for r in cursor.fetchall():
                mid = str(r['kaynak_marka_id'])
                if r['cnt']: marka_a_counts[mid] = r['cnt']
        except Exception as e:
            logger.warning(f"marka_a counts error: {e}")

        # Marka Mod B: kaynak ve hedef aynı marka (lift >= 2, fis >= 500)
        try:
            cursor.execute(f"""
                SELECT kaynak_marka_id, COUNT(*) as cnt
                FROM otomatikkampanyaonerileri
                WHERE {w} AND kaynak_marka_id IS NOT NULL
                  AND kaynak_marka_id = hedef_marka_id
                GROUP BY kaynak_marka_id
            """, base_params)
            for r in cursor.fetchall():
                mid = str(r['kaynak_marka_id'])
                if r['cnt']: marka_b_counts[mid] = r['cnt']
        except Exception as e:
            logger.warning(f"marka_b counts error: {e}")

        return Response({
            'yonetici': yonetici_counts,
            'kategori': kategori_counts,
            'marka_a': marka_a_counts,
            'marka_b': marka_b_counts,
        }, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching filter counts: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_recommendation_status(request, pk):
    """
    Öneri durumunu günceller (Onaylandi, Reddedildi vb.)
    """
    new_status = request.data.get('status')
    if not new_status:
        return Response({"error": "Status is required"}, status=HTTP_400_BAD_REQUEST)

    ph = db_engine.ph()

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)

        table_name = "otomatikkampanyaonerileri"
        id_col = "oneri_id" if db_engine.DB_BACKEND == "postgresql" else "OneriID"
        cursor.execute(f"SELECT * FROM {table_name} WHERE {id_col} = {ph}", [pk])
        if not cursor.fetchone():
            return Response({"error": "Recommendation not found"}, status=HTTP_404_NOT_FOUND)

        status_col = "oneri_durumu" if db_engine.DB_BACKEND == "postgresql" else "OneriDurumu"
        update_col = "son_guncelleme" if db_engine.DB_BACKEND == "postgresql" else "SonGuncelleme"
        
        cursor.execute(f"""
            UPDATE {table_name}
            SET {status_col} = {ph}, {update_col} = {ph}
            WHERE {id_col} = {ph}
        """, [new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pk])

        conn.commit()

        if new_status == 'Onaylandi':
            try:
                import sys
                import os
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                if project_root not in sys.path:
                    sys.path.append(project_root)
                from database.campaign_manager import onaylanan_kampanyalari_uygula
                onaylanan_kampanyalari_uygula()
            except Exception as camp_err:
                logger.warning(f"Campaign activation skipped: {camp_err}")

        return Response({"message": f"Status updated to {new_status}"}, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error updating recommendation status: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_recommendation_status(request):
    """
    Birden fazla öneri durumunu toplu günceller
    """
    ids = request.data.get('ids', [])
    new_status = request.data.get('status')
    
    if not ids or not new_status:
        return Response({"error": "IDs and status are required"}, status=HTTP_400_BAD_REQUEST)

    ph = db_engine.ph()
    table_name = "otomatikkampanyaonerileri"
    id_col = "oneri_id" if db_engine.DB_BACKEND == "postgresql" else "OneriID"
    status_col = "oneri_durumu" if db_engine.DB_BACKEND == "postgresql" else "OneriDurumu"
    update_col = "son_guncelleme" if db_engine.DB_BACKEND == "postgresql" else "SonGuncelleme"

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)
        
        # ID listesini placeholderlara çevir: (1, 2, 3) -> (?, ?, ?) or (%s, %s, %s)
        placeholders = ", ".join([ph for _ in ids])
        
        query = f"""
            UPDATE {table_name}
            SET {status_col} = {ph}, {update_col} = {ph}
            WHERE {id_col} IN ({placeholders})
        """
        
        # Parametreler: [status, time, id1, id2, ...]
        params = [new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')] + ids
        
        cursor.execute(query, params)
        conn.commit()
        
        return Response({"message": f"{len(ids)} recommendations updated to {new_status}"}, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in bulk status update: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_campaign_summary(request, pk):
    """
    Kampanya tipine göre özgün, veri odaklı detaylı özet üretir.
    Potansiyel müşteri = hedef kitlenin %15'u, önerilen fiyat = normal fiyatın %75'i,
    potansiyel ciro = bu ikisinin çarpımı.
    """
    ph = db_engine.ph()

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)

        id_col = "oneri_id" if db_engine.DB_BACKEND == "postgresql" else "OneriID"
        cursor.execute(f"SELECT * FROM OtomatikKampanyaOnerileri WHERE {id_col} = {ph}", [pk])
        r = cursor.fetchone()

        if not r:
            return Response({"error": "Recommendation not found"}, status=HTTP_404_NOT_FOUND)

        camp_type = db_engine.val(r, 'KampanyaTipi', 'N/A')
        segment = db_engine.val(r, 'HedefSegment', 'N/A')
        category = db_engine.val(r, 'KategoriAdi', 'N/A')
        product = db_engine.val(r, 'UrunAdi', '-')
        target_count = int(db_engine.val(r, 'HedefMusteriSayisi', 0) or 0)
        fis_sayisi = int(db_engine.val(r, 'FisSayisi', 0) or 0)
        veri_ozeti = db_engine.val(r, 'VeriOzeti', '')
        gerekce = db_engine.val(r, 'Gerekcesi', '')
        beklenen_sonuc = db_engine.val(r, 'BeklenenSonuc', '')
        onerilen_indirim = db_engine.val(r, 'OnerilenIndirim', 0) or 0
        onerilen_min_tutar = float(db_engine.val(r, 'OnerilenMinTutar', 150) or 150)
        lift = db_engine.val(r, 'Lift', None)
        guven = db_engine.val(r, 'Guven', None)
        source_cat = db_engine.val(r, 'IkinciUrunAdi', '') or db_engine.val(r, 'KaynakKategoriAd', '')

        # VeriOzeti'nden ortak müşteri sayısını parse et ("Ortak müşteri: X" formatı)
        import re as _re
        ortak_musteri = 0
        if veri_ozeti:
            m = _re.search(r'Ortak m[üu][şs]teri:\s*(\d+)', veri_ozeti)
            if m:
                ortak_musteri = int(m.group(1))

        # Cross-Sell için gerçek kaynak kategorisi toplam alıcı sayısını sorgula
        kaynak_toplam_musteri = 0
        if camp_type == 'Cross-Sell' and source_cat:
            try:
                cursor.execute("""
                    SELECT COUNT(DISTINCT s.musteri_id) as toplam
                    FROM satislar s
                    JOIN urunler u ON s.urun_id = u.id
                    JOIN kategoriler k ON k.id = u.kategori_id
                    WHERE (k.alt2 = %s OR k.alt1 = %s OR k.ana = %s)
                      AND s.musteri_id IS NOT NULL AND s.miktar > 0 AND s.tutar > 0
                """, [source_cat, source_cat, source_cat])
                row_src = cursor.fetchone()
                if row_src:
                    kaynak_toplam_musteri = int(db_engine.val(row_src, 'toplam', 0) or 0)
            except Exception:
                kaynak_toplam_musteri = target_count + ortak_musteri  # fallback: hedef + ortak

        # OnerilenUrunler JSON'undan ürün listesi
        import json as _json
        onerilen_urunler_raw = db_engine.val(r, 'OnerilenUrunler', '[]') or '[]'
        try:
            onerilen_urunler = _json.loads(onerilen_urunler_raw) if isinstance(onerilen_urunler_raw, str) else onerilen_urunler_raw
        except Exception:
            onerilen_urunler = []

        # DB'deki hesaplanmış değerleri direkt kullan — kart ile tutarlı olması için
        potansiyel_ciro = float(db_engine.val(r, 'PotansiyelCiro', 0) or 0)
        potansiyel_musteri = int(db_engine.val(r, 'TahminiKatilim', 0) or 0)

        # [DYNAMIC SYNC] Eğer Cross-Sell ise ve ROI düşük görünüyorsa veya DB eski kalmışsa 
        # generator'daki yeni formülü burada da uygula (UI tutarlılığı için)
        if camp_type == 'Cross-Sell' and target_count > 0:
            _lift = float(lift) if lift else 2.0
            # Generator'daki formülün aynısı:
            dinamik_donusum_orani = min(0.25, max(0.05, _lift * 0.05))
            kitle_bazli_katilim = target_count * dinamik_donusum_orani
            organik_bazli_katilim = ortak_musteri * max(1.5, _lift * 0.8)
            
            yeni_potansiyel = max(1, min(round(max(kitle_bazli_katilim, organik_bazli_katilim)), target_count))
            
            # Eğer hesapladığımız yeni değer DB'dekinden büyükse (veya ROI < 1 ise) güncelle
            if yeni_potansiyel > potansiyel_musteri:
                # Birim fiyat koruması: potansiyel_ciro / potansiyel_musteri
                avg_val = potansiyel_ciro / potansiyel_musteri if potansiyel_musteri > 0 else (onerilen_min_tutar or 150)
                potansiyel_musteri = yeni_potansiyel
                potansiyel_ciro = round(potansiyel_musteri * avg_val, 2)
        
        # Fallback (Cross-Sell değilse veya hala 0 ise)
        if potansiyel_musteri <= 0:
            potansiyel_musteri = max(1, round(target_count * 0.15))

        # Kaynak ve hedef kategorinin birlikte alındığı fişlerdeki gerçek kategori ciroları
        kategori_id = db_engine.val(r, 'KategoriID') or db_engine.val(r, 'kategori_id')
        kaynak_ciro = 0.0
        hedef_ciro = 0.0
        kaynak_avg = 0.0
        try:
            # Tek sorguda: her iki kategoriyi aynı fişte içeren satırların kategori bazlı ciro toplamı
            # INNER JOIN ile fis_no üzerinden cross-join — subquery yerine daha hızlı
            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN (k.alt2 = %s OR k.alt1 = %s OR k.ana = %s) THEN s.tutar ELSE 0 END), 0) AS kaynak_toplam,
                    COALESCE(SUM(CASE WHEN s.kategori_id = %s THEN s.tutar ELSE 0 END), 0) AS hedef_toplam
                FROM satislar s
                JOIN kategoriler k ON k.id = s.kategori_id
                WHERE s.fis_no IN (
                    SELECT fis_no FROM satislar
                    JOIN kategoriler kk ON kk.id = kategori_id
                    WHERE (kk.alt2 = %s OR kk.alt1 = %s OR kk.ana = %s) AND tutar > 0
                    INTERSECT
                    SELECT fis_no FROM satislar WHERE kategori_id = %s AND tutar > 0
                )
                AND s.tutar > 0
            """, [source_cat, source_cat, source_cat, kategori_id,
                  source_cat, source_cat, source_cat, kategori_id])
            r2 = cursor.fetchone()
            kaynak_ciro = round(float(db_engine.val(r2, 'kaynak_toplam', 0) or 0), 2)
            hedef_ciro  = round(float(db_engine.val(r2, 'hedef_toplam', 0) or 0), 2)
        except Exception:
            pass
        # potansiyel birlikte alım için kaynak avg
        try:
            cursor.execute("""
                SELECT AVG(s.tutar / NULLIF(s.miktar, 0)) AS avg_val
                FROM satislar s
                JOIN kategoriler k ON k.id = s.kategori_id
                WHERE (k.alt1 = %s OR k.alt2 = %s)
                  AND s.miktar > 0 AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
            """, [source_cat, source_cat])
            r4 = cursor.fetchone()
            kaynak_avg = float(db_engine.val(r4, 'avg_val', 0) or 0)
        except Exception:
            pass

        # Mevcut birlikte alım cirosu: DB değeri varsa kullan, yoksa iki kategorinin gerçek ciro toplamı
        mevcut_birlikte_ciro = float(db_engine.val(r, 'MevcutBirlikteCiro', 0) or 0)
        if mevcut_birlikte_ciro <= 0:
            mevcut_birlikte_ciro = round(kaynak_ciro + hedef_ciro, 2)
        # Son fallback: fis_sayisi × (kaynak_avg + hedef kat avg fiyatı)
        if mevcut_birlikte_ciro <= 0 and fis_sayisi > 0:
            try:
                hedef_avg_fb = 0.0
                cursor.execute(f"""
                    SELECT AVG(s.tutar / NULLIF(s.miktar, 0)) AS avg_val
                    FROM satislar s
                    WHERE s.kategori_id = {ph}
                      AND s.miktar > 0 AND s.tutar > 0
                      AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
                """, [kategori_id])
                r_fb = cursor.fetchone()
                if r_fb:
                    hedef_avg_fb = float(db_engine.val(r_fb, 'avg_val', 0) or 0)
                if kaynak_avg <= 0:
                    cursor.execute(f"""
                        SELECT AVG(s.tutar / NULLIF(s.miktar, 0)) AS avg_val
                        FROM satislar s
                        JOIN kategoriler k ON k.id = s.kategori_id
                        WHERE (k.ana = {ph} OR k.alt1 = {ph} OR k.alt2 = {ph})
                          AND s.miktar > 0 AND s.tutar > 0
                          AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
                    """, [source_cat, source_cat, source_cat])
                    r_ka = cursor.fetchone()
                    if r_ka:
                        kaynak_avg = float(db_engine.val(r_ka, 'avg_val', 0) or 0)
                mevcut_birlikte_ciro = round(fis_sayisi * (kaynak_avg + hedef_avg_fb), 2)
            except Exception:
                pass

        # Potansiyel birlikte alım cirosu
        kaynak_katki = round(potansiyel_musteri * kaynak_avg, 2)
        birlikte_ciro = round(potansiyel_ciro + kaynak_katki, 2)

        indirim_orani = (float(db_engine.val(r, 'OnerilenIndirim', 25)) or 25) / 100.0
        if indirim_orani >= 1 or indirim_orani <= 0:
            indirim_orani = 0.25
        indirim_maliyeti = max(round(potansiyel_ciro / (1 - indirim_orani) * indirim_orani, 2), 1)

        urun_roi = round(potansiyel_ciro / indirim_maliyeti, 2)
        birlikte_roi = round(birlikte_ciro / indirim_maliyeti, 2)

        # Ürün id'leri ile satislar'dan gerçek ortalama birim fiyat çek (son 365 gün)
        urun_ids = [int(u['id']) for u in (onerilen_urunler or []) if u.get('id')]
        gercek_fiyat_map = {}
        if urun_ids:
            try:
                ph_list = ','.join([db_engine.ph()] * len(urun_ids))
                cursor.execute(f"""
                    SELECT s.urun_id, AVG(s.tutar / NULLIF(s.miktar, 0)) as avg_fiyat
                    FROM satislar s
                    WHERE s.urun_id IN ({ph_list}) AND s.miktar > 0 AND s.tutar > 0
                      AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
                    GROUP BY s.urun_id
                """, urun_ids)
                for fr in cursor.fetchall():
                    uid = db_engine.val(fr, 'urun_id')
                    avg = db_engine.val(fr, 'avg_fiyat')
                    if uid and avg:
                        gercek_fiyat_map[int(uid)] = round(float(avg), 2)
            except Exception:
                pass

        # Kategori bazlı ortalama fiyat (tüm ürünler için son fallback)
        kat_avg_fallback = 0.0
        try:
            cursor.execute(f"""
                SELECT AVG(s.tutar / NULLIF(s.miktar, 0)) AS avg_val
                FROM satislar s
                WHERE s.kategori_id = {ph}
                  AND s.miktar > 0 AND s.tutar > 0
                  AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
            """, [kategori_id])
            r_kat = cursor.fetchone()
            if r_kat:
                kat_avg_fallback = float(db_engine.val(r_kat, 'avg_val', 0) or 0)
        except Exception:
            pass

        # Her ürün için (ad, normal_fiyat, kampanya_fiyati) tuple'ı
        urun_detaylari = []
        for u in (onerilen_urunler or []):
            ad = u.get('ad', '')
            if not ad:
                continue
            uid = u.get('id')
            gercek_avg = gercek_fiyat_map.get(int(uid), 0) if uid else 0
            json_ort = float(u.get('ort', 0) or 0)
            # Öncelik: satislar gerçek ortalaması > JSON ort (100 değilse) > kategori ort > onerilen_min_tutar
            if gercek_avg > 0:
                normal_fiyat = gercek_avg
            elif json_ort > 0 and json_ort != 100.0:
                normal_fiyat = round(json_ort, 2)
            elif kat_avg_fallback > 0:
                normal_fiyat = round(kat_avg_fallback, 2)
            else:
                normal_fiyat = round(onerilen_min_tutar / 0.75, 2) if onerilen_min_tutar > 0 else 0
            kampanya_fiyati = round(normal_fiyat * (1 - indirim_orani), 2) if normal_fiyat > 0 else round(onerilen_min_tutar, 2)
            urun_detaylari.append((ad, normal_fiyat, kampanya_fiyati))
        if not urun_detaylari:
            normal_fiyat = round(onerilen_min_tutar / 0.75, 2) if onerilen_min_tutar > 0 else (kat_avg_fallback or 0)
            kampanya_fiyati_fb = round(normal_fiyat * (1 - indirim_orani), 2) if normal_fiyat > 0 else round(onerilen_min_tutar, 2)
            urun_detaylari = [(product, normal_fiyat, kampanya_fiyati_fb)]
        # Potansiyel ciroya (kampanya_fiyati) göre azalan sırala
        urun_detaylari.sort(key=lambda x: x[2], reverse=True)
        urun_listesi = [u[0] for u in urun_detaylari]

        # Ürün satırı cirosu: potansiyel_ciro'yu ürünler arasında kampanya fiyatına göre orantılı böl
        toplam_kampanya_fiyat = sum(kf for _, _, kf in urun_detaylari if kf > 0) or 1
        def urun_satiri(ad, normal_fiyat, kampanya_fiyati):
            if kampanya_fiyati and kampanya_fiyati > 0:
                ciro = round(potansiyel_ciro * kampanya_fiyati / toplam_kampanya_fiyat, 2)
                if normal_fiyat > 0:
                    indirim_yuzdesi = round((1 - kampanya_fiyati / normal_fiyat) * 100)
                    return f'- **{ad}** — ~~₺{normal_fiyat:,.2f}~~ → **₺{kampanya_fiyati:,.2f}** (%{indirim_yuzdesi} indirim) × {potansiyel_musteri:,} müşteri = **₺{ciro:,.2f} pot. ciro**'
                return f'- **{ad}** — **₺{kampanya_fiyati:,.2f}** × {potansiyel_musteri:,} müşteri = **₺{ciro:,.2f} pot. ciro**'
            return f'- **{ad}**'

        if camp_type == 'Cross-Sell':
            lift_val = float(lift) if lift else 0
            guven_val = float(guven) * 100 if guven else 0
            lift_yorum = "çok güçlü" if lift_val >= 2.0 else "güçlü" if lift_val >= 1.5 else "pozitif"
            summary = f"""### ÇAPRAZ SATIŞ KAMPANYASI — {source_cat} → {category}

**Neden Bu Kampanya Önerildi?**
Sepet analizi verilerimiz, **'{source_cat}'** kategorisinden alışveriş yapan müşterilerin **'{category}'** kategorisini de satın alma olasılığının sıradan bir müşteriye kıyasla **{lift_val:.1f}x daha yüksek** olduğunu ortaya koyuyor. Bu **{lift_yorum}** bir birliktelik sinyalidir — müşteri zaten alışveriş modundadır ve ek bir ikna çabası gerekmez. Güven skoru **%{guven_val:.0f}** olan bu öneri, gerçek satın alma verilerinden türetilmiştir.

**Ne Gibi Avantajlar Sağlar?**
- Mevcut müşteri trafiğini değerlendirerek sıfır yeni müşteri edinim maliyetiyle ek ciro üretir
- Sepet büyüklüğünü artırır; müşteri başı ortalama işlem değeri yükselir
- '{source_cat}' alışverişi sırasında veya hemen sonrasında tetiklenebileceği için doğru zamanlama avantajı sunar
- Müşteri '{category}' kategorisine organik ilgi duyduğu için dönüşüm oranı yüksektir

**Hedef Kitle ve Finansal Projeksiyon**

| Metrik | Değer |
|--------|-------|
| '{source_cat}' kategorisi toplam alıcısı | {kaynak_toplam_musteri:,} müşteri |
| Henüz '{category}' almamış hedef kitle | {target_count:,} müşteri |
| Kampanyaya ulaşılacak kitle (lift bazlı) | {potansiyel_musteri:,} müşteri |
| Bu birlikteliği gösteren işlem (fiş) sayısı | {fis_sayisi:,} fiş |
| Her iki kategoriyi birlikte alan müşteri | {ortak_musteri:,} müşteri |
| Mevcut birlikte alım cirosu ({fis_sayisi:,} fiş) | ₺{mevcut_birlikte_ciro:,.2f} |
| ↳ '{source_cat}' kategorisi mevcut cirosu | ₺{kaynak_ciro:,.2f} |
| ↳ '{category}' önerilen ürün kategorisi mevcut cirosu | ₺{hedef_ciro:,.2f} |
| Önerilen indirim oranı | %{round(indirim_orani * 100):.0f} |
| Önerilen kampanya fiyatı (ort.) | ₺{urun_detaylari[0][2]:,.2f} |
| Geçerlilik süresi | {db_engine.val(r, 'GecerlilikSuresi', 15) or 15} gün |
| **'{category}' kampanyası yatırım maliyeti (İndirim)** | **₺{indirim_maliyeti:,.2f}** |
| **'{category}' önerilen ürün potansiyel cirosu** | **₺{potansiyel_ciro:,.2f}** |
| **'{category}' önerilen ürün tahmini ROI** | **{urun_roi:.1f}x** |
| **Potansiyel birlikte alım cirosu** | **₺{birlikte_ciro:,.2f}** |
| **Birlikte tahmini ROI (Çapraz Satış Etkisiyle)** | **{birlikte_roi:.1f}x** |

**Uygulama Önerisi**
'{source_cat}' alışverişini tamamlayan müşterilere; sepet sayfasında, ödeme sonrası e-postada veya uygulama bildirimiyle aşağıdaki ürünler için **%{round(indirim_orani * 100):.0f} indirimli** teklif sunulması önerilir:

{chr(10).join(urun_satiri(ad, ort, fiyat) for ad, ort, fiyat in urun_detaylari[:5])}

**Veri Kaynağı**
{veri_ozeti}
"""

        elif camp_type == 'Loyalty':
            summary = f"""### SADAKAT KAMPANYASI — {segment} Segmenti

**Neden Bu Kampanya Önerildi?**
**{segment}** segmentindeki müşteriler, RFM analizimizde yüksek alışveriş sıklığı ve sepet büyüklüğü ile öne çıkan en değerli grubumuzdan birini oluşturuyor. Veriler, bu müşterilerin **'{category}'** kategorisinde henüz tam potansiyellerini kullanmadığını gösteriyor; yani bu kategoriye ilgi var ama tetikleyici bir neden bekleniyorlar. Sadakat programlarına yatırımın getirisi, yeni müşteri ediniminden ortalama **5x daha yüksektir**.

**Ne Gibi Avantajlar Sağlar?**
- Zaten marka bağlılığı olan müşterileri daha sık alışverişe yönlendirir; düşük ikna maliyeti
- Müşteri Yaşam Boyu Değerini (LTV) doğrudan artırır
- Segment bazlı kişiselleştirme müşteriye özel hissettirerek çıkma (churn) riskini azaltır
- '{category}' kategorisinde derinleşme sağlayarak raf payını genişletir

**Hedef Kitle ve Finansal Projeksiyon**

| Metrik | Değer |
|--------|-------|
| Toplam {segment} müşterisi | {target_count:,} müşteri |
| Kampanyaya ulaşılacak kitle (Dinamik) | {potansiyel_musteri:,} müşteri |
| **Potansiyel ciro** | **₺{potansiyel_ciro:,.2f}** |

**Uygulama Önerisi**
{segment} segmentindeki müşterilere "Sana Özel" etiketiyle kişiselleştirilmiş bildirim gönderilmesi önerilir. Aşağıdaki ürünlerde **%25 indirim** veya sadakat puanı ile ödüllendirme en etkili teşvik yöntemi olacaktır:

{chr(10).join(urun_satiri(ad, ort, fiyat) for ad, ort, fiyat in urun_detaylari[:5])}

**Veri Kaynağı**
{veri_ozeti}
"""

        elif camp_type == 'Win-Back':
            summary = f"""### MÜŞTERİ GERİ KAZANIM KAMPANYASI — {segment}

**Neden Bu Kampanya Önerildi?**
**{segment}** segmentindeki {target_count:,} müşteri, sistematik churn analizi sonucunda yüksek kayıp riski taşıdığı tespit edilen gruptur. Bu müşteriler geçmişte **'{category}'** kategorisinde ve özellikle **'{product}'** ürününde alışveriş yapmış; dolayısıyla markamızı tanıyorlar. Araştırmalar, kaybedilen bir müşteriyi geri kazanmanın yeni müşteri ediniminden **5x daha ucuz** olduğunu gösteriyor. Doğru ürün ve zamanlama ile bu müşterilerin önemli bir kısmı geri döndürülebilir.

**Ne Gibi Avantajlar Sağlar?**
- Müşteri daha önce ürünü/markayı deneyimlemiş; sıfırdan güven inşa etmek gerekmez
- Hedeflenen ürün müşterinin geçmiş tercihleriyle birebir örtüştüğü için dönüşüm oranı yüksek
- Segmentlenmiş ulaşım sayesinde doğru kişiye doğru mesaj iletilir; israf yoktur
- Geri kazanılan her müşteri, ilerleyen dönemde tekrar kayıp olmadan elde tutulabilir

**Hedef Kitle ve Finansal Projeksiyon**

| Metrik | Değer |
|--------|-------|
| Toplam kayıp riskli müşteri | {target_count:,} müşteri |
| Kampanyaya ulaşılacak kitle (Dinamik) | {potansiyel_musteri:,} müşteri |
| **Potansiyel ciro** | **₺{potansiyel_ciro:,.2f}** |

**Uygulama Önerisi**
Müşterinin son alışverişinden bu yana geçen süreye göre kademeli bir "Seni Özledik" serisi önerilir. İlk temas e-posta, ikinci temas SMS, üçüncüsü ise uygulama bildirimi olabilir. Aşağıdaki ürünlerde **%25 indirim** veya ücretsiz kargo gibi somut bir teşvik eklenmelidir:

{chr(10).join(urun_satiri(ad, ort, fiyat) for ad, ort, fiyat in urun_detaylari[:5])}

**Veri Kaynağı**
{veri_ozeti}
"""

        elif camp_type == 'Clearance':
            summary = f"""### STOK ERİTME KAMPANYASI — {product}

**Neden Bu Kampanya Önerildi?**
**'{product}'** ürünü, stok analizi sonucunda **fazla stok** ve **düşük/durgun satış performansı** kombinasyonuyla öne çıkmaktadır. {gerekce} Stokta tutulan her fazla ürün; depolama maliyeti, sermaye blokajı ve bozulma/eskime riski doğurur. Hızlı bir kampanyayla hem bu maliyet ortadan kalkar hem de nakit akışı güçlenir.

**Ne Gibi Avantajlar Sağlar?**
- Depoda bağlı kalan sermaye serbest kalır; likidite artar
- Stoğun bozulma veya modası geçme riskinden önce değer yaratılır
- Fiyat avantajıyla aktif müşteri tabanında anlık talep yaratır
- Raf alanı ve lojistik kapasitesi yeni, daha kârlı ürünlere açılır

**Hedef Kitle ve Finansal Projeksiyon**

| Metrik | Değer |
|--------|-------|
| Toplam aktif müşteri tabanı | {target_count:,} müşteri |
| Kampanyaya ulaşılacak kitle (Dinamik) | {potansiyel_musteri:,} müşteri |
| **Potansiyel ciro** | **₺{potansiyel_ciro:,.2f}** |

**Uygulama Önerisi**
Kampanya süresi kısa tutulmalı (7 gün önerilir); "Sınırlı Stok" vurgusu aciliyet hissi yaratır. Tüm aktif müşterilere e-posta ve uygulama bildirimiyle aşağıdaki ürünlerde **%25 indirim** duyurusu yapılabilir:

{chr(10).join(urun_satiri(ad, ort, fiyat) for ad, ort, fiyat in urun_detaylari[:5])}

**Veri Kaynağı**
{veri_ozeti}
"""

        else:
            summary = f"""### STRATEJİK SATIŞ ÖNERİSİ — {category}

**Gerekçe**
{gerekce}

**Hedef Kitle ve Finansal Projeksiyon**

| Metrik | Değer |
|--------|-------|
| Toplam hedef kitle | {target_count:,} müşteri |
| Kampanyaya ulaşılacak kitle (Dinamik) | {potansiyel_musteri:,} müşteri |
| Önerilen kampanya fiyatı (%25 indirim) | ₺{onerilen_min_tutar:,.2f} |
| **Potansiyel ciro** | **₺{potansiyel_ciro:,.2f}** |

**Veri Kaynağı**
{veri_ozeti}
"""

        return Response({"summary": summary}, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_category_hierarchy(request):
    """
    Kategori hiyerarşisini döndürür (ana > alt1 > alt2)
    """
    import time
    start_time = time.time()
    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)

        sql_start = time.time()
        cursor.execute("""
            SELECT DISTINCT ana, alt1, alt2
            FROM kategoriler
            WHERE ana IS NOT NULL
            ORDER BY ana, alt1, alt2
        """)

        rows = cursor.fetchall()
        sql_end = time.time()

        hierarchy = {}
        mapping_start = time.time()
        for row in rows:
            ana = row['ana'] or 'Diğer'
            alt1 = row['alt1']
            alt2 = row['alt2']

            if ana not in hierarchy:
                hierarchy[ana] = {}

            if alt1:
                if alt1 not in hierarchy[ana]:
                    hierarchy[ana][alt1] = []
                if alt2:
                    hierarchy[ana][alt1].append(alt2)
        mapping_end = time.time()
        
        total_time = time.time() - start_time
        logger.info(f"PERF: get_category_hierarchy TOTAL={total_time:.3f}s SQL={sql_end-sql_start:.3f}s MAP={mapping_end-mapping_start:.3f}s ROWS={len(rows)}")

        return Response(hierarchy, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching category hierarchy: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_category_top_products(request):
    """
    Belirli bir kategori için en çok satan 10 ürünü getirir.
    3-tier fallback: encoksatanlar → urunperformansdetay → satislar+urunler+kategoriler
    """
    category_name = request.GET.get('name')

    if not category_name:
        return Response({"error": "Category name is required"}, status=HTTP_400_BAD_REQUEST)

    category_name = category_name.strip()
    ph = db_engine.ph()

    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)

        products = []

        # Find category IDs matching the name (Ana, Alt1 or Alt2)
        cursor.execute(f"""
            SELECT id FROM kategoriler
            WHERE ana = {ph} OR alt1 = {ph} OR alt2 = {ph}
        """, [category_name, category_name, category_name])
        cat_ids = [row['id'] for row in cursor.fetchall()]

        if cat_ids:
            # Live query from satislar + urunler for actual customer/receipt counts
            placeholders = ','.join([ph] * len(cat_ids))
            cursor.execute(f"""
                SELECT u.ad,
                       SUM(s.tutar) as revenue,
                       SUM(s.miktar) as quantity,
                       COUNT(DISTINCT s.musteri_id) as customer_count,
                       COUNT(DISTINCT s.fis_no) as receipt_count,
                       SUM(s.tutar) / NULLIF(SUM(s.miktar), 0) as avg_price
                FROM satislar s
                JOIN urunler u ON s.urun_id = u.id
                WHERE s.kategori_id IN ({placeholders})
                GROUP BY u.ad
                ORDER BY quantity DESC
                LIMIT 10
            """, cat_ids)
            products = [dict(row) for row in cursor.fetchall()]

        return Response(products, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching category top products: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_kategori_yoneticileri(request):
    """
    Tüm kategori yöneticilerini listeler
    """
    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)
        cursor.execute("""
            SELECT s.id, s.ad as name
            FROM kategori_yoneticileri s
            ORDER BY s.ad
        """)
        rows = cursor.fetchall()
        return Response([dict(row) for row in rows], status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching kategori yoneticileri: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_brands(request):
    """
    Tüm markaları listeler
    """
    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)
        # Adım 1: Kaynak kategorileri çek
        cursor.execute("""
            SELECT DISTINCT kaynak_kategori_ad
            FROM otomatikkampanyaonerileri
            WHERE oneri_durumu != 'Reddedildi' AND kaynak_kategori_ad IS NOT NULL
        """)
        kaynak_kategoriler = [r['kaynak_kategori_ad'] for r in cursor.fetchall()]
        if not kaynak_kategoriler:
            return Response([], status=HTTP_200_OK)
        # Adım 2: Bu kategorilerdeki markaları getir
        placeholders = ','.join(['%s'] * len(kaynak_kategoriler))
        cursor.execute(f"""
            SELECT DISTINCT m.id, m.ad as name
            FROM markalar m
            JOIN urunler u ON u.marka_id = m.id
            JOIN kategoriler k ON k.id = u.kategori_id
            WHERE k.alt2 IN ({placeholders})
            ORDER BY m.ad
        """, kaynak_kategoriler)
        rows = cursor.fetchall()
        return Response([dict(row) for row in rows], status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching brands: {e}")
        return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
    finally:
        if 'conn' in locals() and conn:
            db_engine.release_connection(conn)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_campaigns(request):
    """
    Kampanya önerilerini yeniden üretir.
    ?sync=1 ile senkron çalışır ve sonucu döndürür (debug için).
    """
    sync = request.GET.get('sync') == '1'
    import sys, os, traceback as tb_module
    # campaign_manager.py backend/ kökünde
    current = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.abspath(os.path.join(current, '..', '..'))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    if sync:
        try:
            from campaign_manager import kampanya_onerileri_uret
            kampanya_onerileri_uret()
            return Response({"status": "ok", "message": "Kampanya önerileri başarıyla üretildi."}, status=HTTP_200_OK)
        except Exception as e:
            return Response({"status": "error", "message": str(e), "traceback": tb_module.format_exc()}, status=HTTP_200_OK)

    import threading
    def run():
        try:
            from campaign_manager import kampanya_onerileri_uret
            kampanya_onerileri_uret()
            logger.info("Kampanya önerileri başarıyla yeniden üretildi.")
        except Exception as e:
            logger.error("Kampanya auto-refresh hatası: %s", str(e), exc_info=True)
    threading.Thread(target=run, daemon=True).start()
    return Response({"status": "started", "message": "Kampanya önerileri arka planda yeniden üretiliyor."}, status=HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enrich_urun_fiyatlari(request):
    """
    onerilen_urunler JSON'undaki her ürün için son 30 günlük gerçek ortalama fiyatı
    (gercek_avg) hesaplar ve JSON'a kaydeder. Bir kez çalıştırılır.
    """
    import json as _json
    try:
        conn = get_db_connection()
        cursor = db_engine.get_dict_cursor(conn)
        read_cursor = db_engine.get_dict_cursor(conn)

        cursor.execute("""
            SELECT oneri_id, onerilen_urunler
            FROM otomatikkampanyaonerileri
            WHERE kampanya_tipi = 'Cross-Sell'
              AND onerilen_urunler IS NOT NULL
              AND onerilen_urunler != '[]'
        """)
        rows = cursor.fetchall()

        updated = 0
        for row in rows:
            oneri_id = db_engine.val(row, 'oneri_id')
            urunler_raw = db_engine.val(row, 'onerilen_urunler') or '[]'
            try:
                urunler = _json.loads(urunler_raw) if isinstance(urunler_raw, str) else urunler_raw
            except Exception:
                continue

            urun_ids = [int(u['id']) for u in urunler if u.get('id')]
            if not urun_ids:
                continue

            ph_list = ','.join(['%s'] * len(urun_ids))
            read_cursor.execute(f"""
                SELECT urun_id, AVG(tutar / NULLIF(miktar, 0)) as avg_fiyat
                FROM satislar
                WHERE urun_id IN ({ph_list})
                  AND miktar > 0 AND tutar > 0
                  AND tarih >= CURRENT_DATE - INTERVAL '365 days'
                GROUP BY urun_id
            """, urun_ids)
            fiyat_map = {}
            for fr in read_cursor.fetchall():
                uid = db_engine.val(fr, 'urun_id')
                avg = db_engine.val(fr, 'avg_fiyat')
                if uid and avg:
                    fiyat_map[int(uid)] = round(float(avg), 2)

            changed = False
            for u in urunler:
                uid = u.get('id')
                if uid and int(uid) in fiyat_map:
                    gercek_avg = fiyat_map[int(uid)]
                    if u.get('gercek_avg') != gercek_avg:
                        u['gercek_avg'] = gercek_avg
                        changed = True

            if changed:
                cursor.execute(
                    "UPDATE otomatikkampanyaonerileri SET onerilen_urunler = %s WHERE oneri_id = %s",
                    [_json.dumps(urunler, ensure_ascii=False), oneri_id]
                )
                updated += 1

        conn.commit()

        # birlikte_ciro güncelle: (tahmini_katilim * kaynak_avg) + potansiyel_ciro
        cursor.execute("""
            UPDATE otomatikkampanyaonerileri o
            SET birlikte_ciro = ROUND((
                o.tahmini_katilim * (
                    SELECT AVG(s.tutar / NULLIF(s.miktar, 0))
                    FROM satislar s
                    JOIN kategoriler k ON k.id = s.kategori_id
                    WHERE (k.alt1 = o.kaynak_kategori_ad OR k.alt2 = o.kaynak_kategori_ad)
                      AND s.miktar > 0
                      AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
                ) + o.potansiyel_ciro
            )::numeric, 2)
            WHERE o.kampanya_tipi = 'Cross-Sell'
        """)
        birlikte_updated = cursor.rowcount

        # mevcut_birlikte_ciro güncelle: fis_sayisi * (kaynak_avg + hedef_avg) son 30 gun
        cursor.execute("""
            UPDATE otomatikkampanyaonerileri o
            SET mevcut_birlikte_ciro = ROUND((
                o.fis_sayisi * (
                    COALESCE((
                        SELECT AVG(s.tutar / NULLIF(s.miktar, 0))
                        FROM satislar s
                        JOIN kategoriler k ON k.id = s.kategori_id
                        WHERE (k.alt1 = o.kaynak_kategori_ad OR k.alt2 = o.kaynak_kategori_ad)
                          AND s.miktar > 0 AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
                    ), 0)
                    +
                    COALESCE((
                        SELECT AVG(s.tutar / NULLIF(s.miktar, 0))
                        FROM satislar s
                        WHERE s.kategori_id = o.kategori_id
                          AND s.miktar > 0 AND s.tarih >= CURRENT_DATE - INTERVAL '365 days'
                    ), 0)
                )
            )::numeric, 2)
            WHERE o.kampanya_tipi = 'Cross-Sell'
        """)
        mevcut_updated = cursor.rowcount
        conn.commit()

        db_engine.release_connection(conn)
        return Response({"status": "ok", "urun_fiyat_updated": updated, "birlikte_ciro_updated": birlikte_updated, "mevcut_birlikte_updated": mevcut_updated, "total": len(rows)}, status=HTTP_200_OK)
    except Exception as e:
        import traceback
        return Response({"status": "error", "message": str(e), "traceback": traceback.format_exc()}, status=HTTP_200_OK)
