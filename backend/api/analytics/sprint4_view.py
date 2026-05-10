"""
Sprint 4 Views
- Enflasyon Dayanıklılık Profili (3.4)
- Rakip Riski Skoru (4.3)
- Temsilci Notları ve CRM Görevleri (4.4)
- Kampanya Gönderim Motoru (4.1)
- Hane Tespit Analizi (4.2)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
import logging
from .base import get_user_from_request, _read_cache
from .. import db_engine

logger = logging.getLogger(__name__)


# Imported from base.py: _read_cache(cursor, tablo) -> dict | None


# ─── 3.4 Enflasyon Dayanıklılık Profili ─────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enflasyon_dayaniklilik(request, data_source_id):
    """
    Enflasyon dayanıklılık profili — cache_enflasyon_dayaniklilik tablosundan okunur.
    Cache yoksa anlık hesaplar (fallback).
    """
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        cached = _read_cache(cursor, 'cache_enflasyon_dayaniklilik')
        if cached:
            return Response(cached)

        # ── Fallback: anlık hesapla ──────────────────────────────────────────
        logger.warning("cache_enflasyon_dayaniklilik boş — anlık hesaplama yapılıyor.")
        cursor.execute("""
            SELECT
                m.rfm_segment,
                COUNT(DISTINCT musteri_id) as musteri_sayisi,
                AVG(pf.indirim_oran_yuzde) as ort_indirim_oran,
                AVG(pf.ort_indirim_yuzde) as ort_indirim_yuzde,
                AVG(dk.harcama_degisim_3ay_yuzde) as ort_harcama_degisim_3ay,
                AVG(dk.ziyaret_degisim_3ay_yuzde) as ort_ziyaret_degisim_3ay,
                AVG(dk.harcama_degisim_6ay_yuzde) as ort_harcama_degisim_6ay,
                COUNT(CASE WHEN me.enflasyon_stokcusu = TRUE THEN 1 END) as stokcu_sayisi,
                COUNT(CASE WHEN me.fiyat_hassas = TRUE THEN 1 END) as fiyat_hassas_sayisi
            FROM musteriler m
            JOIN musterifiyatfeatures pf ON m.id = pf.musteri_id
            JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
            JOIN musterietiketler me ON m.id = me.musteri_id
            WHERE m.rfm_segment IS NOT NULL
            GROUP BY m.rfm_segment ORDER BY musteri_sayisi DESC
        """)
        segment_analiz = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT m.id, m.ad, m.rfm_segment, md.toplam_harcama as toplam_harcama,
                   pf.indirim_oran_yuzde, pf.ort_indirim_yuzde,
                   dk.harcama_degisim_3ay_yuzde as harcama_degisim_3ay,
                   dk.ziyaret_degisim_3ay_yuzde as ziyaret_degisim_3ay
            FROM musteriler m
            JOIN musterietiketler me ON m.id = me.musteri_id
            JOIN musterifiyatfeatures pf ON m.id = pf.musteri_id
            JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
            LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
            WHERE me.enflasyon_stokcusu = TRUE
            ORDER BY dk.harcama_degisim_3ay_yuzde DESC LIMIT 50
        """)
        stokcu_liste = [dict(r) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT COUNT(DISTINCT musteri_id) as toplam_musteri,
                   COUNT(CASE WHEN me.enflasyon_stokcusu = TRUE THEN 1 END) as stokcu_sayisi,
                   COUNT(CASE WHEN me.fiyat_hassas = TRUE THEN 1 END) as fiyat_hassas_sayisi,
                   AVG(pf.indirim_oran_yuzde) as genel_indirim_oran,
                   AVG(dk.harcama_degisim_3ay_yuzde) as genel_harcama_degisim
            FROM musteriler m
            JOIN musterifiyatfeatures pf ON m.id = pf.musteri_id
            JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
            JOIN musterietiketler me ON m.id = me.musteri_id
            WHERE 1=1
        """)
        ozet_row = cursor.fetchone()
        ozet = dict(ozet_row) if ozet_row else {}

        return Response({'segment_analiz': segment_analiz, 'stokcu_liste': stokcu_liste, 'ozet': ozet, '_cache_tarihi': None})

    except Exception as e:
        logger.error(f"Enflasyon dayanıklılık hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


# ─── 4.3 Rakip Riski Skoru ───────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_rakip_riski(request, data_source_id):
    """
    Rakip riski skoru — cache_rakip_riski tablosundan okunur.
    Cache yoksa anlık hesaplar (fallback).
    """
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
    approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')
    region = request.GET.get('region')
    has_filter = bool(customer_type or approval_status or region)

    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()

        if not has_filter:
            cached = _read_cache(cursor, 'cache_rakip_riski')
            if cached:
                return Response(cached)

        # ── Müşteri filtresi oluştur ────────────────────────────────────────
        if not has_filter:
            logger.warning("cache_rakip_riski boş — anlık hesaplama yapılıyor.")
        extra_filter = ""
        extra_params = []
        if customer_type:
            extra_filter += f" AND m.tip = {ph}"
            extra_params.append(customer_type)
        if approval_status:
            extra_filter += f" AND m.onay_durumu = {ph}"
            extra_params.append(approval_status)
        if region:
            extra_filter += f" AND m.kayit_magazasi IN (SELECT id::text FROM magazalar WHERE bolge = {ph})"
            extra_params.append(region)

        cursor.execute(f"""
            SELECT
                m.id, m.ad, m.rfm_segment,
                md.toplam_harcama as toplam_harcama,
                COALESCE(dk.terk_edilen_kategori, 0) as terk_edilen_kategori,
                COALESCE(dk.harcama_degisim_3ay_yuzde, 0) as harcama_degisim_3ay,
                COALESCE(dk.ziyaret_degisim_3ay_yuzde, 0) as ziyaret_degisim_3ay,
                LEAST(100, GREATEST(0,
                    CASE WHEN me.kategori_terk_eden = TRUE THEN 30 ELSE 0 END +
                    CASE WHEN me.sepeti_daralan = TRUE THEN 20 ELSE 0 END +
                    CASE WHEN me.kaybedilme_riski_yuksek = TRUE THEN 25 ELSE 0 END +
                    CASE WHEN me.soguyan_musteri = TRUE THEN 15 ELSE 0 END +
                    CASE WHEN COALESCE(dk.terk_edilen_kategori, 0) > 2 THEN 10 ELSE 0 END
                )) as rakip_riski_skoru
            FROM musteriler m
            JOIN musterietiketler me ON m.id = me.musteri_id
            LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
            LEFT JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
            WHERE (me.kategori_terk_eden = TRUE OR me.sepeti_daralan = TRUE OR me.kaybedilme_riski_yuksek = TRUE)
              {extra_filter}
            ORDER BY rakip_riski_skoru DESC, toplam_harcama DESC
            LIMIT 200
        """, extra_params)
        risk_liste = [dict(r) for r in cursor.fetchall()]

        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT musteri_id) FILTER (WHERE skor >= 60) as yuksek,
                COUNT(*) FILTER (WHERE skor >= 30 AND skor < 60) as orta,
                COUNT(*) FILTER (WHERE skor < 30) as dusuk,
                COUNT(*) as toplam
            FROM (
                SELECT LEAST(100, GREATEST(0,
                    CASE WHEN me.kategori_terk_eden = TRUE THEN 30 ELSE 0 END +
                    CASE WHEN me.sepeti_daralan = TRUE THEN 20 ELSE 0 END +
                    CASE WHEN me.kaybedilme_riski_yuksek = TRUE THEN 25 ELSE 0 END +
                    CASE WHEN me.soguyan_musteri = TRUE THEN 15 ELSE 0 END +
                    CASE WHEN COALESCE(dk.terk_edilen_kategori, 0) > 2 THEN 10 ELSE 0 END
                )) as skor
                FROM musteriler m
                JOIN musterietiketler me ON m.id = me.musteri_id
                LEFT JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
                WHERE (me.kategori_terk_eden = TRUE OR me.sepeti_daralan = TRUE OR me.kaybedilme_riski_yuksek = TRUE)
                  {extra_filter}
            ) sub
        """, extra_params)
        dagilim_row = cursor.fetchone()
        yuksek = int(db_engine.val(dagilim_row, 'yuksek', 0)) if dagilim_row else 0
        orta   = int(db_engine.val(dagilim_row, 'orta', 0)) if dagilim_row else 0
        dusuk  = int(db_engine.val(dagilim_row, 'dusuk', 0)) if dagilim_row else 0
        toplam = int(db_engine.val(dagilim_row, 'toplam', 0)) if dagilim_row else 0

        return Response({
            'risk_listesi': risk_liste,
            'dagilim': {'yuksek': yuksek, 'orta': orta, 'dusuk': dusuk, 'toplam': toplam},
            '_cache_tarihi': None,
        })

    except Exception as e:
        logger.error(f"Rakip riski hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


# ─── 4.4 Temsilci Notları ────────────────────────────────────────────────────

def ensure_notes_table(cursor):
    """musteri_notlar tablosunu oluştur (yoksa)"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musteri_notlar (
            id SERIAL PRIMARY KEY,
            musteri_id INTEGER NOT NULL,
            kullanici_id INTEGER NOT NULL,
            baslik TEXT,
            icerik TEXT NOT NULL,
            onem TEXT DEFAULT 'normal',
            olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def musteri_notlari(request, data_source_id, customer_id):
    """
    GET: Müşteriyle ilişkili notları listele
    POST: Yeni not ekle
    """
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    ph = db_engine.ph()
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ensure_notes_table(cursor)
        conn.commit()

        if request.method == 'GET':
            cursor.execute(f"""
                SELECT id, musteri_id, kullanici_id, baslik, icerik, onem,
                       olusturma_tarihi, guncelleme_tarihi
                FROM musteri_notlar
                WHERE musteri_id = {ph}
                ORDER BY olusturma_tarihi DESC
                LIMIT 50
            """, (customer_id,))
            notlar = [dict(r) for r in cursor.fetchall()]
            # Tarih alanlarını stringe çevir
            for n in notlar:
                for k in ['olusturma_tarihi', 'guncelleme_tarihi']:
                    if n.get(k) and hasattr(n[k], 'isoformat'):
                        n[k] = n[k].isoformat()
            return Response({'notlar': notlar})

        elif request.method == 'POST':
            icerik = request.data.get('icerik', '').strip()
            baslik = request.data.get('baslik', '').strip()
            onem = request.data.get('onem', 'normal')
            if not icerik:
                return Response({'error': 'İçerik boş olamaz'}, status=400)
            if onem not in ('dusuk', 'normal', 'yuksek', 'kritik'):
                onem = 'normal'

            cursor.execute(f"""
                INSERT INTO musteri_notlar (musteri_id, kullanici_id, baslik, icerik, onem)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                RETURNING id, olusturma_tarihi
            """, (customer_id, user.id, baslik or None, icerik, onem))
            row = cursor.fetchone()
            conn.commit()
            not_id = db_engine.val(row, 'id')
            tarih = db_engine.val(row, 'olusturma_tarihi')
            return Response({
                'id': not_id,
                'tarih': tarih.isoformat() if hasattr(tarih, 'isoformat') else str(tarih),
                'mesaj': 'Not eklendi'
            }, status=201)

    except Exception as e:
        logger.error(f"Müşteri notları hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def musteri_not_sil(request, data_source_id, customer_id, not_id):
    """Notu sil"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    ph = db_engine.ph()
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        cursor.execute(f"""
            DELETE FROM musteri_notlar
            WHERE id = {ph} AND musteri_id = {ph} AND kullanici_id = {ph}
        """, (not_id, customer_id, user.id))
        conn.commit()
        return Response({'mesaj': 'Not silindi'})
    except Exception as e:
        logger.error(f"Not silme hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


# ─── 4.1 Kampanya Gönderim Motoru ────────────────────────────────────────────

def ensure_gonderim_table(cursor):
    """kampanya_gonderimler tablosunu oluştur (yoksa)"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kampanya_gonderimler (
            id SERIAL PRIMARY KEY,
            oneri_id INTEGER NOT NULL,
            musteri_id INTEGER NOT NULL,
            kanal TEXT DEFAULT 'manuel',
            durum TEXT DEFAULT 'gonderildi',
            gonderim_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acilis_tarihi TIMESTAMP,
            conversion_tarihi TIMESTAMP,
            conversion_tutar NUMERIC(12,2),
            notlar TEXT
        )
    """)
    # İndeks
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kamp_gond_oneri ON kampanya_gonderimler(oneri_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kamp_gond_musteri ON kampanya_gonderimler(musteri_id)
        """)
    except Exception:
        pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kampanya_gonder(request, data_source_id, oneri_id):
    """
    Kampanya önerisini seçili müşterilere gönder.
    Body: { musteri_idler: [id,...], kanal: 'sms'|'email'|'push'|'manuel' }
    """
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    ph = db_engine.ph()
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ensure_gonderim_table(cursor)

        musteri_idler = request.data.get('musteri_idler', [])
        kanal = request.data.get('kanal', 'manuel')

        if not musteri_idler:
            return Response({'error': 'En az 1 müşteri seçilmeli'}, status=400)

        gecerli_kanallar = ('sms', 'email', 'push', 'manuel')
        if kanal not in gecerli_kanallar:
            kanal = 'manuel'

        # Tekrar gönderimi önle: aynı oneri_id + musteri_id var mı?
        zaten_gonderilen = set()
        placeholders = ', '.join([ph for _ in musteri_idler])
        cursor.execute(f"""
            SELECT musteri_id FROM kampanya_gonderimler
            WHERE oneri_id = {ph} AND musteri_id IN ({placeholders})
        """, [oneri_id] + list(musteri_idler))
        for r in cursor.fetchall():
            zaten_gonderilen.add(db_engine.val(r, 'musteri_id'))

        yeni_musteri_idler = [mid for mid in musteri_idler if mid not in zaten_gonderilen]

        if not yeni_musteri_idler:
            return Response({'mesaj': 'Bu müşterilere zaten gönderildi', 'gonderilen': 0, 'atlanan': len(zaten_gonderilen)})

        # Toplu insert
        now = datetime.now()
        for mid in yeni_musteri_idler:
            cursor.execute(f"""
                INSERT INTO kampanya_gonderimler (oneri_id, musteri_id, kanal, durum, gonderim_tarihi)
                VALUES ({ph}, {ph}, {ph}, 'gonderildi', {ph})
            """, (oneri_id, mid, kanal, now))

        # Öneri durumunu 'Gonderildi' olarak güncelle
        cursor.execute(f"""
            UPDATE MusteriOnerileri SET oneri_durumu = 'Gonderildi'
            WHERE oneri_id = {ph}
        """, (oneri_id,))

        conn.commit()

        return Response({
            'mesaj': f'{len(yeni_musteri_idler)} müşteriye gönderildi',
            'gonderilen': len(yeni_musteri_idler),
            'atlanan': len(zaten_gonderilen),
            'kanal': kanal,
        }, status=201)

    except Exception as e:
        logger.error(f"Kampanya gönderim hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kampanya_gonderim_ozeti(request, data_source_id, oneri_id):
    """
    Belirli bir öneri için gönderim özeti + conversion tracking
    """
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    ph = db_engine.ph()
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ensure_gonderim_table(cursor)

        # Gönderim özeti
        cursor.execute(f"""
            SELECT
                COUNT(*) as toplam_gonderilen,
                COUNT(acilis_tarihi) as acilan,
                COUNT(conversion_tarihi) as conversion,
                COALESCE(SUM(conversion_tutar), 0) as toplam_conversion_tutar,
                kanal,
                MIN(gonderim_tarihi) as ilk_gonderim,
                MAX(gonderim_tarihi) as son_gonderim
            FROM kampanya_gonderimler
            WHERE oneri_id = {ph}
            GROUP BY kanal
        """, (oneri_id,))
        kanal_ozet = [dict(r) for r in cursor.fetchall()]

        # Tarih alanlarını stringe çevir
        for row in kanal_ozet:
            for k in ['ilk_gonderim', 'son_gonderim']:
                if row.get(k) and hasattr(row[k], 'isoformat'):
                    row[k] = row[k].isoformat()

        # 30 gün conversion: gönderim sonrası 30 gün içinde ilgili üründen satın alım
        cursor.execute(f"""
            SELECT COUNT(DISTINCT kg.musteri_id) as conversion_sayisi
            FROM kampanya_gonderimler kg
            JOIN MusteriOnerileri mo ON kg.oneri_id = mo.oneri_id
            JOIN satislar s ON s.musteri_id = kg.musteri_id
            WHERE kg.oneri_id = {ph}
              AND s.tarih >= kg.gonderim_tarihi::date
              AND s.tarih <= kg.gonderim_tarihi::date + 30
        """, (oneri_id,))
        conv_row = cursor.fetchone()
        otomatik_conversion = db_engine.val(conv_row, 'conversion_sayisi', 0) if conv_row else 0

        toplam = sum(r['toplam_gonderilen'] for r in kanal_ozet)
        acilan = sum(r['acilan'] or 0 for r in kanal_ozet)
        conversion = sum(r['conversion'] or 0 for r in kanal_ozet)

        return Response({
            'kanal_ozet': kanal_ozet,
            'toplam': toplam,
            'acilan': acilan,
            'conversion': conversion,
            'otomatik_conversion': otomatik_conversion,
            'conversion_oran': round(conversion / toplam * 100, 1) if toplam > 0 else 0,
        })

    except Exception as e:
        logger.error(f"Gönderim özeti hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


# ─── 4.2 Hane Tespit Analizi ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hane_analizi(request, data_source_id):
    """
    Hane profili analizi — cache_hane_analizi tablosundan okunur.
    Cache yoksa anlık hesaplar (fallback).
    """
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'Yetkisiz'}, status=401)

    customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
    approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')
    region = request.GET.get('region')
    has_filter = bool(customer_type or approval_status or region)

    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()

        if not has_filter:
            cached = _read_cache(cursor, 'cache_hane_analizi')
            if cached:
                return Response(cached)

        # ── Müşteri filtresi ────────────────────────────────────────────────
        if not has_filter:
            logger.warning("cache_hane_analizi boş — anlık hesaplama yapılıyor.")
        extra_filter = ""
        extra_params = []
        if customer_type:
            extra_filter += f" AND m.tip = {ph}"
            extra_params.append(customer_type)
        if approval_status:
            extra_filter += f" AND m.onay_durumu = {ph}"
            extra_params.append(approval_status)
        if region:
            extra_filter += f" AND m.kayit_magazasi IN (SELECT id::text FROM magazalar WHERE bolge = {ph})"
            extra_params.append(region)

        hane_kolonlar = [
            ('hane_bekar_skoru', 'Bekar'), ('hane_cift_skoru', 'Çift'),
            ('hane_aile_skoru', 'Aile'), ('hane_cocuklu_skoru', 'Çocuklu'),
            ('hane_bebek_skoru', 'Bebek'), ('hane_yasli_skoru', 'Yaşlı'),
            ('hane_evcil_hayvan_skoru', 'Evcil Hayvan'), ('hane_araba_skoru', 'Araba'),
        ]
        hane_dagilim = []
        for kolon, etiket in hane_kolonlar:
            try:
                cursor.execute(f"""
                    SELECT                 COUNT(DISTINCT musteri_id) as musteri_sayisi,
                           AVG(me.{kolon}) as ort_skor,
                           COUNT(CASE WHEN me.{kolon} >= 0.6 THEN 1 END) as yuksek_skor_sayisi
                    FROM musterietiketler me
                    JOIN musteriler m ON m.id = me.musteri_id
                    WHERE 1=1 {extra_filter}
                """, extra_params)
                row = cursor.fetchone()
                if row:
                    hane_dagilim.append({
                        'tip': etiket, 'kolon': kolon,
                        'musteri_sayisi': db_engine.val(row, 'musteri_sayisi', 0),
                        'ort_skor': round(float(db_engine.val(row, 'ort_skor') or 0), 3),
                        'yuksek_skor_sayisi': db_engine.val(row, 'yuksek_skor_sayisi', 0),
                    })
            except Exception:
                continue

        cursor.execute(f"""
            SELECT m.rfm_segment, COUNT(*) as toplam,
                   AVG(me.hane_bekar_skoru) as bekar, AVG(me.hane_cift_skoru) as cift,
                   AVG(me.hane_aile_skoru) as aile, AVG(me.hane_cocuklu_skoru) as cocuklu,
                   AVG(me.hane_bebek_skoru) as bebek, AVG(me.hane_yasli_skoru) as yasli,
                   AVG(me.hane_evcil_hayvan_skoru) as evcil, AVG(me.hane_araba_skoru) as araba
            FROM musterietiketler me
            JOIN musteriler m ON m.id = me.musteri_id
            WHERE m.rfm_segment IS NOT NULL {extra_filter}
            GROUP BY m.rfm_segment ORDER BY toplam DESC
        """, extra_params)
        segment_hane = []
        for r in cursor.fetchall():
            row = dict(r)
            skorlar = {
                'Bekar': float(row.get('bekar') or 0), 'Çift': float(row.get('cift') or 0),
                'Aile': float(row.get('aile') or 0), 'Çocuklu': float(row.get('cocuklu') or 0),
                'Bebek': float(row.get('bebek') or 0), 'Yaşlı': float(row.get('yasli') or 0),
                'Evcil Hayvan': float(row.get('evcil') or 0), 'Araba': float(row.get('araba') or 0),
            }
            baskin = max(skorlar, key=skorlar.get)
            segment_hane.append({
                'rfm_segment': row.get('rfm_segment'), 'toplam': row.get('toplam'),
                'baskin_hane': baskin, 'baskin_skor': round(skorlar[baskin], 3),
                'skorlar': {k: round(v, 3) for k, v in skorlar.items()},
            })

        cursor.execute(f"""
            SELECT m.id, m.ad, m.rfm_segment, md.toplam_harcama as toplam_harcama,
                   me.hane_cocuklu_skoru, me.hane_bebek_skoru, me.hane_aile_skoru, me.hane_araba_skoru
            FROM musterietiketler me
            JOIN musteriler m ON m.id = me.musteri_id
            LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
            WHERE (me.hane_cocuklu_skoru >= 0.5 OR me.hane_bebek_skoru >= 0.5) {extra_filter}
            ORDER BY md.toplam_harcama DESC LIMIT 30
        """, extra_params)
        cocuklu_aile_liste = [dict(r) for r in cursor.fetchall()]

        return Response({
            'hane_dagilim': hane_dagilim, 'segment_hane': segment_hane,
            'cocuklu_aile_liste': cocuklu_aile_liste, '_cache_tarihi': None,
        })

    except Exception as e:
        logger.error(f"Hane analizi hatası: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)
