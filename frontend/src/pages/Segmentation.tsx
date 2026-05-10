import { useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'
import useDashboardStore from '../stores/dashboardStore'
import ExcelExportButton from '../components/ExcelExportButton'
import { Group } from '@mantine/core'
import {
  IconTag, IconX, IconChevronDown, IconChevronRight,
  IconUsers, IconHeart, IconAlertTriangle, IconTarget, IconChartBar,
  IconTrendingUp, IconBulb, IconDiamond, IconStar, IconHome, IconSearch
} from '@tabler/icons-react'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { notifications } from '@mantine/notifications'
import { useChatStore } from '../stores/chatStore'
import '../styles/DashboardHome.css'

// ─── Types ───────────────────────────────────────────────────────────────────

interface EtiketTrend {
  degisim_yuzde: number
  degisim_yonu: 'yukselis' | 'dusus' | 'sabit'
  onceki_sayi: number
}

interface EtiketOzet {
  kolon: string
  sayi: number
  oran: number
  trend?: EtiketTrend | null
}

interface EtiketOzetiResponse {
  toplam_musteri: number
  etiketler: EtiketOzet[]
  kategoriler: Record<string, EtiketOzet[]>
  trend_tarihi?: string | null
}

interface SegmentDetail {
  metrics: {
    total_count: number
    avg_spend: number
    avg_visits: number
    avg_churn_risk: number
    avg_basket: number
  }
  top_categories: { category: string; count: number }[]
  activity_dist: { status: string; count: number }[]
  label: string
}

// ─── Constants ───────────────────────────────────────────────────────────────

const KATEGORI_CONFIG: { key: string; ad: string; renk: string; icon: ReactNode }[] = [
  { key: 'ziyaret',   ad: 'Ziyaret Davranışı',         renk: '#6366f1', icon: <IconTarget size={18} stroke={1.8} /> },
  { key: 'sepet',     ad: 'Sepet & Harcama',            renk: '#10b981', icon: <IconChartBar size={18} stroke={1.8} /> },
  { key: 'fiyat',     ad: 'Fiyat & Kampanya',           renk: '#f59e0b', icon: <IconTag size={18} stroke={1.8} /> },
  { key: 'taze_gida', ad: 'Taze Gıda',                  renk: '#22c55e', icon: <IconStar size={18} stroke={1.8} /> },
  { key: 'kategori',  ad: 'Kategori İlgileri',          renk: '#8b5cf6', icon: <IconBulb size={18} stroke={1.8} /> },
  { key: 'kanal',     ad: 'Kanal & Kampanya Tepkisi',   renk: '#3b82f6', icon: <IconTrendingUp size={18} stroke={1.8} /> },
  { key: 'odeme',     ad: 'Ödeme & Finansal',           renk: '#06b6d4', icon: <IconDiamond size={18} stroke={1.8} /> },
  { key: 'sadakat',   ad: 'Sadakat & Risk',             renk: '#ef4444', icon: <IconAlertTriangle size={18} stroke={1.8} /> },
  { key: 'hane',      ad: 'Hane Yapısı & Tüketim',     renk: '#f97316', icon: <IconHome size={18} stroke={1.8} /> },
]

const ETIKET_ADLARI: Record<string, string> = {
  sabah_alisveriscisi:            'Sabah Alışverişçisi',
  aksam_alisveriscisi:            'Akşam Alışverişçisi',
  gece_alisveriscisi:             'Gece Alışverişçisi',
  hafta_sonu_alisveriscisi:       'Hafta Sonu Alışverişçisi',
  hafta_ici_alisveriscisi:        'Hafta İçi Alışverişçisi',
  aylik_duzenli_alici:            'Aylık Düzenli Alıcı',
  maas_gunu_alisveriscisi:        'Maaş Günü Alışverişçisi',
  gunluk_ugrayan:                 'Günlük Uğrayan',
  seyrek_alisverisci:             'Seyrek Alışverişçi',
  buyuk_sepet_alisveriscisi:      'Büyük Sepet Alışverişçisi',
  kucuk_sepet_alisveriscisi:      'Küçük Sepet Alışverişçisi',
  premium_harcayici:              'Premium Harcayıcı',
  ekonomik_harcayici:             'Ekonomik Harcayıcı',
  b2b_mahalle_esnafi:             'B2B Mahalle Esnafı',
  stokcu_alici:                   'Stokçu Alıcı',
  tekli_urun_alisveriscisi:       'Tekli Ürün Alışverişçisi',
  indirim_avcisi:                 'İndirim Avcısı',
  promosyon_bagimli:              'Promosyon Bağımlı',
  fiyat_hassas:                   'Fiyat Hassas',
  fiyata_duyarsiz:                'Fiyata Duyarsız',
  coklu_alim_firsatcisi:          'Çoklu Alım Fırsatçısı',
  enflasyon_stokcusu:             'Enflasyon Stokçusu',
  kampanya_tepkisi_dusuk:         'Kampanya Tepkisi Düşük',
  kasap_odakli:                   'Kasap Odaklı',
  manav_odakli:                   'Manav Odaklı',
  firinci_odakli:                 'Fırıncı Odaklı',
  sarkuteri_odakli:               'Şarküteri Odaklı',
  sadece_taze_gidaci:             'Sadece Taze Gıdacı',
  yoresel_urun_meraklisi:         'Yöresel Ürün Meraklısı',
  taze_gida_kacinani:             'Taze Gıda Kaçınanı',
  saglikli_yasam_egilimli:        'Sağlıklı Yaşam Eğilimli',
  hazir_tuketim_egilimli:         'Hazır Tüketim Eğilimli',
  protein_odakli:                 'Protein Odaklı',
  kafein_yogun_tuketici:          'Kafein Yoğun Tüketici',
  atistirmalik_tuketicisi:        'Atıştırmalık Tüketicisi',
  temizlik_hijyen_odakli:         'Temizlik & Hijyen Odaklı',
  kisisel_bakim_tutkunu:          'Kişisel Bakım Tutkunu',
  misafir_sofrasi_kurucusu:       'Misafir Sofrası Kurucusu',
  winback_adayi:                  'Winback Adayı',
  reaktivasyon_potansiyeli:       'Reaktivasyon Potansiyeli',
  yeniden_kazanilmis:             'Yeniden Kazanılmış',
  kampanya_duyarli:               'Kampanya Duyarlı',
  kampanyasiz_sadik:              'Kampanyasız Sadık',
  yemek_karti_kullanicisi:        'Yemek Kartı Kullanıcısı',
  ay_sonu_yemek_karti_harcayicisi:'Ay Sonu YK Harcayıcısı',
  fatura_musterisi:               'Fatura Müşterisi',
  sadik_musteri:                  'Sadık Müşteri',
  soguyan_musteri:                'Soğuyan Müşteri',
  kaybedilme_riski_yuksek:        'Kaybedilme Riski Yüksek',
  tamamen_kaybedilmis:            'Tamamen Kaybedilmiş',
  yeniden_kazanilmis_saglik:      'Yeniden Kazanılmış (Sağlık)',
  gidip_gelen_musteri:            'Gidip Gelen Müşteri',
  sepeti_daralan:                 'Sepeti Daralan',
  kategori_terk_eden:             'Kategori Terk Eden',
  marji_dusuran:                  'Marjı Düşüren',
  gizli_risk:                     'Gizli Risk',
  kaybedilmemesi_gereken:         'Kaybedilmemesi Gereken',
  hane_bekar_skoru:               'Bekar / Tek Kişilik Hane',
  hane_cift_skoru:                'Çift Hane',
  hane_aile_skoru:                'Geniş Aile',
  hane_cocuklu_skoru:             'Çocuklu Hane',
  hane_bebek_skoru:               'Bebekli Hane',
  hane_yasli_skoru:               'Yaşlı Birey İçeren Hane',
  hane_evcil_hayvan_skoru:        'Evcil Hayvan Sahibi',
  hane_araba_skoru:               'Araçlı Müşteri',
  hane_toplu_alim_skoru:          'Toplu Alım Eğilimli',
}

const ETIKET_ACIKLAMALARI: Record<string, string> = {
  sabah_alisveriscisi:            'Alışverişlerinin %50\'sinden fazlasını sabah 07-11 saatleri arasında yapar.',
  aksam_alisveriscisi:            'Alışverişlerinin %50\'sinden fazlasını akşam 18-21 saatleri arasında yapar.',
  gece_alisveriscisi:             'Alışverişlerinin %25\'inden fazlasını gece 21 sonrasında yapar.',
  hafta_sonu_alisveriscisi:       'Ziyaretlerinin %60\'ından fazlası Cumartesi-Pazar günlerine denk gelir.',
  hafta_ici_alisveriscisi:        'Ziyaretlerinin büyük çoğunluğu hafta içi günlerine aittir.',
  aylik_duzenli_alici:            'Ortalama 15-40 gün aralıklarla düzenli alışveriş yapar.',
  maas_gunu_alisveriscisi:        'Alışverişlerinin %35\'inden fazlası ayın 1-4 veya 15-18. günlerine denk gelir.',
  gunluk_ugrayan:                 'Ortalama ziyaret aralığı 2 gün veya daha az; markete çok sık uğrar.',
  seyrek_alisverisci:             'Ortalama ziyaret aralığı 40 günden fazla; nadiren gelir.',
  buyuk_sepet_alisveriscisi:      'Ortalama sepet tutarı 800 TL\'nin üzerindedir.',
  kucuk_sepet_alisveriscisi:      'Ortalama sepet tutarı 200 TL\'nin altındadır.',
  premium_harcayici:              'Toplam harcaması tüm müşterilerin %75\'inin üzerinde.',
  ekonomik_harcayici:             'Toplam harcaması tüm müşterilerin %25\'inin altında.',
  b2b_mahalle_esnafi:             'Sık ziyaret, büyük sepet ve toplu alım kombinasyonu ile esnaf profili taşır.',
  stokcu_alici:                   'Aynı üründen çok yüksek miktarda alım yapma eğilimi gösterir.',
  tekli_urun_alisveriscisi:       'Fiş başına ortalama kategori sayısı çok düşük; tek iş için gelir.',
  indirim_avcisi:                 'Satırlarının %40\'ından fazlası indirimli; ortalama indirim derinliği %15+ .',
  promosyon_bagimli:              'Satırlarının %80\'inden fazlası indirimli; neredeyse sadece kampanyada alır.',
  fiyat_hassas:                   'Tek markada yoğunlaşmak yerine birçok markayı fiyata göre tercih eder.',
  fiyata_duyarsiz:                'En sevdiği markada ısrar eder; indirim olmasa da aynı ürünü tekrar alır.',
  coklu_alim_firsatcisi:          'Kampanyalı dönemlerde normalden çok daha yüksek adet satın alır.',
  enflasyon_stokcusu:             'Temel gıda kategorilerinde belirli dönemlerde normalin 2,5 katı alım yapar.',
  kampanya_tepkisi_dusuk:         'Satırlarının %5\'inden azı indirimli; kampanyadan bağımsız alır.',
  kasap_odakli:                   'Harcamasının %35\'inden fazlası Et & Balık & Kümes Hayvanları kategorisindedir.',
  manav_odakli:                   'Harcamasının %30\'undan fazlası Meyve & Sebze kategorisindedir.',
  firinci_odakli:                 'Harcamasının %10\'undan fazlası Unlu Mamuller & Ekmek kategorisindedir.',
  sarkuteri_odakli:               'Harcamasının %30\'undan fazlası Şarküteri & Sütlük kategorisindedir.',
  sadece_taze_gidaci:             'Harcamasının %70\'inden fazlası Et, Meyve/Sebze, Şarküteri ve Ekmek kategorilerindedir.',
  yoresel_urun_meraklisi:         'Bakliyat, Baharat ve Konserve/Salça kategorilerinin toplamı %20\'yi aşar.',
  taze_gida_kacinani:             'Taze gıda kategorilerinden düşük oranda alım yapar.',
  saglikli_yasam_egilimli:        'Meyve/Sebze payı %25\'in üstünde; atıştırmalık ve hazır gıda tüketimi düşük.',
  hazir_tuketim_egilimli:         'Konserve, hazır yemek ve dondurulmuş ürünlerin toplam payı %15\'in üstünde.',
  protein_odakli:                 'Et ve işlenmiş et ürünlerinin toplam payı %30\'un üstünde.',
  kafein_yogun_tuketici:          'Çay, Kahve & Şeker kategorisinin payı %15\'in üstünde.',
  atistirmalik_tuketicisi:        'Atıştırmalık & Bisküvi kategorisinin payı %15\'in üstünde.',
  temizlik_hijyen_odakli:         'Temizlik & Kâğıt Ürünler kategorisinin payı %15\'in üstünde.',
  kisisel_bakim_tutkunu:          'Kozmetik & Kişisel Bakım kategorisinin payı %10\'un üstünde.',
  misafir_sofrasi_kurucusu:       'Ortalama fiş tutarı 1000 TL+ ve fiş başına kategori çeşitliliği 5+.',
  winback_adayi:                  'Son gelişi 90-270 gün önce; en az 5 ziyareti olan müşteri.',
  reaktivasyon_potansiyeli:       'Son 90-180 günde geldi ama ziyaret sıklığı %50+ düştü.',
  yeniden_kazanilmis:             'Hayatında en az 90 gün ara vermiş ama son 30 günde geri döndü.',
  kampanya_duyarli:               'Fişlerinin %80\'inden fazlası kampanyalı dönemlere denk gelir.',
  kampanyasiz_sadik:              'Fişlerinin %90\'ından fazlası kampanyanın olmadığı dönemlerde.',
  yemek_karti_kullanicisi:        'En az bir kez yemek kartıyla ödeme yapmıştır.',
  ay_sonu_yemek_karti_harcayicisi:'Yemek kartı fişlerinin %30\'undan fazlası ayın son haftasında.',
  fatura_musterisi:               'En az bir kez fatura belgesi kesilerek alışveriş yapılmış.',
  sadik_musteri:                  '10+ ziyaret, son 60 günde gelmiş, 6+ aydır müşteri.',
  soguyan_musteri:                'Önceki 3 aya kıyasla ziyaret sıklığı %50+ azalmış.',
  kaybedilme_riski_yuksek:        'Hem harcama hem ziyaret sayısı önceki döneme göre %50+ düşmüş.',
  tamamen_kaybedilmis:            '180 günden fazla süredir hiç gelmeyen (en az 3 geçmiş ziyareti olan).',
  yeniden_kazanilmis_saglik:      'Uzun aradan sonra geri dönen ve tekrar aktif alışveriş yapan müşteri.',
  gidip_gelen_musteri:            'Hayatında 60 günden uzun en az iki ayrı bekleme süresi yaşamış.',
  sepeti_daralan:                 'Son 3 ayda fiş tutarı önceki 3 aya göre %30\'dan fazla küçülmüş.',
  kategori_terk_eden:             'Önceki 6 ayda aldığı 3 veya daha fazla kategoriyi son 6 ayda almıyor.',
  marji_dusuran:                  'Gelmeye devam ediyor ama daha az harcıyor; harcama %30+ geriledi.',
  gizli_risk:                     'Henüz kaybedilmedi (son 60 günde geldi) ama ziyaret trendi %30+ düşüyor.',
  kaybedilmemesi_gereken:         'Yüksek CLV (toplam harcama P75+) VE risk sinyali taşıyan kritik müşteri.',
  hane_bekar_skoru:               'Düşük sepet tutarı ve az ürün çeşitliliği; tek kişilik tüketim profili.',
  hane_cift_skoru:                'Orta büyüklükte sepet ve düzenli alışveriş; iki kişilik hane profili.',
  hane_aile_skoru:                'Yüksek sepet tutarı, yüksek ürün adedi ve geniş kategori çeşitliliği.',
  hane_cocuklu_skoru:             'Atıştırmalık, kahvaltılık ve dondurma kategorileri yüksek oranla alınıyor.',
  hane_bebek_skoru:               'Bebek Bakım Ürünleri kategorisinden düzenli ve tekrarlayan alımlar.',
  hane_yasli_skoru:               'Sağlık, bakım ve temel gıda ağırlıklı; saat uyumlu düzenli alışveriş.',
  hane_evcil_hayvan_skoru:        'Hayvan Yemleri & Malzemeleri kategorisinden tekrarlayan alımlar.',
  hane_araba_skoru:               'Büyük sepet + içecek (su/kola) yoğunluğu + hafta sonu alışverişi kombinasyonu.',
  hane_toplu_alim_skoru:          'Bir fişte aynı üründen ortalama 5+ adet alan; stoklama eğilimi yüksek.',
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Segmentation() {
  const { selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion, selectedStartDate, selectedEndDate } = useDashboardStore()
  const navigate = useNavigate()

  const [etiketData, setEtiketData]           = useState<EtiketOzetiResponse | null>(null)
  const [etiketLoading, setEtiketLoading]     = useState(false)
  const [expandedKategori, setExpandedKategori] = useState<string>('')
  const [etiketSearch, setEtiketSearch]       = useState('')
  const [selectedEtiket, setSelectedEtiket]   = useState<string | null>(null)
  const [etiketMusteriler, setEtiketMusteriler] = useState<any[]>([])
  const [segmentDetail, setSegmentDetail]     = useState<SegmentDetail | null>(null)
  const [listLoading, setListLoading]         = useState(false)
  const [detailLoading, setDetailLoading]     = useState(false)
  const [listPage, setListPage]               = useState(1)
  const [listHasMore, setListHasMore]         = useState(true)
  const PAGE_SIZE = 20

  // Segment Geçiş Matrisi state
  const [gecisMatrisi, setGecisMatrisi]       = useState<any>(null)
  const [gecisLoading, setGecisLoading]       = useState(false)
  const [gecisExpanded, setGecisExpanded]     = useState(false)

  useEffect(() => {
    if (selectedDataSourceId) {
      loadEtiketData()
    }
  }, [selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  const loadGecisMatrisi = async () => {
    if (!selectedDataSourceId || gecisLoading) return
    setGecisLoading(true)
    try {
      const res = await apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/segment-gecis-matrisi/`)
      setGecisMatrisi(res.data)
    } catch (e) {
      console.error('Segment geçiş matrisi yüklenemedi', e)
      notifications.show({
        title: 'Hata',
        message: 'Segment geçiş matrisi yüklenemedi.',
        color: 'red'
      })
    } finally {
      setGecisLoading(false)
    }
  }

  const loadEtiketData = async () => {
    if (!selectedDataSourceId) return
    setEtiketLoading(true)
    try {
      const res = await apiClient.get(
        `/veri-kaynaklari/${selectedDataSourceId}/musteri-etiket-ozeti/`,
        {
          params: {
            customer_type: selectedCustomerType || undefined,
            approval_status: selectedApprovalStatus || undefined,
            region: selectedRegion || undefined,
            start_date: selectedStartDate || undefined,
            end_date: selectedEndDate || undefined,
          }
        }
      )
      setEtiketData(res.data)
    } catch (e) {
      console.error('Etiket özeti yüklenemedi', e)
      notifications.show({
        title: 'Hata',
        message: 'Etiket özeti yüklenemedi.',
        color: 'red'
      })
    } finally {
      setEtiketLoading(false)
    }
  }

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (etiketData) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Müşteri Segmentasyonu', {
        page: 'segmentation',
        data_source_id: selectedDataSourceId,
        total_customers: etiketData.toplam_musteri,
        active_segment: selectedEtiket,
        segment_detail: segmentDetail,
        kategoriler: Object.keys(etiketData.kategoriler)
      });
    }
  }, [etiketData, selectedEtiket, segmentDetail]);

  const handleEtiketClick = (kolon: string) => {
    if (selectedEtiket === kolon) {
      setSelectedEtiket(null)
      setEtiketMusteriler([])
      setSegmentDetail(null)
      return
    }
    setSelectedEtiket(kolon)
    setEtiketMusteriler([])
    setSegmentDetail(null)
    setListPage(1)
    setListHasMore(true)
    fetchMusteriler(kolon, 1)
    fetchSegmentDetail(kolon)
  }

  const fetchSegmentDetail = async (kolon: string) => {
    if (!selectedDataSourceId) return
    setDetailLoading(true)
    try {
      const res = await apiClient.get(
        `/veri-kaynaklari/${selectedDataSourceId}/segmentasyon/detay/`,
        { params: { 
            etiketler: kolon,
            start_date: selectedStartDate || undefined,
            end_date: selectedEndDate || undefined,
          } }
      )
      setSegmentDetail(res.data)
    } catch (e) {
      console.error('Segment detayları yüklenemedi', e)
      notifications.show({
        title: 'Hata',
        message: 'Segment detayları yüklenemedi.',
        color: 'red'
      })
    } finally {
      setDetailLoading(false)
    }
  }

  const fetchMusteriler = async (kolon: string, page: number) => {
    if (!selectedDataSourceId) return
    setListLoading(true)
    try {
      const res = await apiClient.get(
        `/veri-kaynaklari/${selectedDataSourceId}/musteriler/`,
        { params: { 
            etiketler: kolon, 
            page, 
            limit: PAGE_SIZE, 
            skip_count: true,
            start_date: selectedStartDate || undefined,
            end_date: selectedEndDate || undefined,
          } }
      )
      const newRows = res.data.customers || []
      setEtiketMusteriler(prev => page === 1 ? newRows : [...prev, ...newRows])
      setListHasMore(newRows.length === PAGE_SIZE)
    } catch (e) {
      console.error('Müşteri listesi yüklenemedi', e)
      notifications.show({
        title: 'Hata',
        message: 'Müşteri listesi yüklenemedi.',
        color: 'red'
      })
    } finally {
      setListLoading(false)
    }
  }

  const loadMore = () => {
    if (!selectedEtiket || listLoading || !listHasMore) return
    const next = listPage + 1
    setListPage(next)
    fetchMusteriler(selectedEtiket, next)
  }

  // Arama filtresi
  const filteredEtiketler = etiketSearch.trim()
    ? etiketData?.etiketler.filter(e =>
        (ETIKET_ADLARI[e.kolon] || e.kolon).toLowerCase().includes(etiketSearch.toLowerCase())
      ) ?? []
    : null

  if (!selectedDataSourceId) return (
    <div style={{ padding: '40px', textAlign: 'center' }}>
      <IconTarget size={48} stroke={1.5} color="#6366f1" />
      <div style={{ color: '#6b7280', fontSize: '1.1rem', marginTop: '12px' }}>Veri kaynağı seçin</div>
    </div>
  )

  return (
    <div style={{ padding: '24px' }}>
      <LoadingOverlay loading={etiketLoading}>
        {!etiketData && !etiketLoading && (
          <div style={{ padding: '40px', textAlign: 'center', background: 'white', borderRadius: '16px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
            <IconTag size={48} stroke={1.5} color="#9ca3af" />
            <h2 style={{ color: '#374151', marginTop: '12px' }}>Etiket verisi yüklenemedi</h2>
            <button onClick={loadEtiketData} style={{ marginTop: '16px', padding: '10px 24px', background: '#6366f1', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}>
              Tekrar Dene
            </button>
          </div>
        )}

        {etiketData && (
          <div style={{ display: 'grid', gridTemplateColumns: selectedEtiket ? '1fr 480px' : '1fr', gap: '24px', alignItems: 'start' }}>

            {/* ── Sol: Etiket listesi ── */}
            <div>
              <div style={{ marginBottom: '24px' }}>
                <AIInsightCard 
                  contextType="segmentation" 
                  contextId={selectedDataSourceId?.toString()} 
                  dataSourceId={selectedDataSourceId || ''}
                  title="Segmentasyon ve Davranış Özeti"
                  data={etiketData}
                />
              </div>

              {/* KPI kutuları */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                <KpiCard
                  gradient="linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)"
                  shadow="rgba(79,70,229,0.3)"
                  label="Toplam Müşteri"
                  value={etiketData.toplam_musteri.toLocaleString('tr-TR')}
                  icon={<IconUsers size={80} stroke={1.2} />}
                />
                {(() => {
                  const t = etiketData.kategoriler.sadakat?.find(e => e.kolon === 'sadik_musteri')
                  const tSub = t?.trend && t.trend.degisim_yonu !== 'sabit' && t.trend.degisim_yuzde > 0
                    ? `${t.trend.degisim_yonu === 'yukselis' ? '▲' : '▼'} %${t.trend.degisim_yuzde} son güncelleme`
                    : 'Aktif, düzenli, uzun süreli'
                  return <KpiCard gradient="linear-gradient(135deg, #10b981 0%, #059669 100%)" shadow="rgba(16,185,129,0.3)" label="Sadık Müşteri" value={(t?.sayi || 0).toLocaleString('tr-TR')} sub={tSub} icon={<IconHeart size={80} stroke={1.2} />} />
                })()}
                {(() => {
                  const t = etiketData.kategoriler.sadakat?.find(e => e.kolon === 'gizli_risk')
                  const tSub = t?.trend && t.trend.degisim_yonu !== 'sabit' && t.trend.degisim_yuzde > 0
                    ? `${t.trend.degisim_yonu === 'yukselis' ? '▲' : '▼'} %${t.trend.degisim_yuzde} son güncelleme`
                    : 'Henüz yitmeyen ama tehlikede'
                  return <KpiCard gradient="linear-gradient(135deg, #ef4444 0%, #dc2626 100%)" shadow="rgba(239,68,68,0.3)" label="Gizli Risk" value={(t?.sayi || 0).toLocaleString('tr-TR')} sub={tSub} icon={<IconAlertTriangle size={80} stroke={1.2} />} />
                })()}
                {(() => {
                  const t = etiketData.kategoriler.fiyat?.find(e => e.kolon === 'indirim_avcisi')
                  const tSub = t?.trend && t.trend.degisim_yonu !== 'sabit' && t.trend.degisim_yuzde > 0
                    ? `${t.trend.degisim_yonu === 'yukselis' ? '▲' : '▼'} %${t.trend.degisim_yuzde} son güncelleme`
                    : 'Yüksek indirim kullanımı'
                  return <KpiCard gradient="linear-gradient(135deg, #f59e0b 0%, #d97706 100%)" shadow="rgba(245,158,11,0.3)" label="İndirim Avcısı" value={(t?.sayi || 0).toLocaleString('tr-TR')} sub={tSub} icon={<IconTag size={80} stroke={1.2} />} />
                })()}
              </div>

              {/* Segment Geçiş Matrisi (collapsible) */}
              <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)', overflow: 'hidden', marginBottom: '16px' }}>
                <button
                  onClick={() => {
                    setGecisExpanded(p => !p)
                    if (!gecisMatrisi && !gecisLoading) loadGecisMatrisi()
                  }}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '12px', padding: '14px 20px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: gecisExpanded ? '2px solid #6366f120' : 'none' }}
                >
                  <span style={{ color: '#6366f1' }}><IconTrendingUp size={18} stroke={1.8} /></span>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', flex: 1, textAlign: 'left', color: '#111827' }}>Segment Geçiş Matrisi</span>
                  <span style={{ fontSize: '0.8rem', color: '#9ca3af', marginRight: '8px' }}>Aylık segment değişimleri</span>
                  {gecisExpanded ? <IconChevronDown size={18} stroke={2} color="#9ca3af" /> : <IconChevronRight size={18} stroke={2} color="#9ca3af" />}
                </button>
                {gecisExpanded && (
                  <div style={{ padding: '16px 20px' }}>
                    {gecisLoading ? (
                      <div style={{ textAlign: 'center', padding: '30px', color: '#6b7280' }}>Yükleniyor...</div>
                    ) : !gecisMatrisi ? (
                      <div style={{ textAlign: 'center', padding: '30px', color: '#9ca3af' }}>Veri yüklenemedi</div>
                    ) : gecisMatrisi.mesaj ? (
                      <div style={{ textAlign: 'center', padding: '30px', color: '#6b7280', fontSize: '0.9rem' }}>{gecisMatrisi.mesaj}</div>
                    ) : (() => {
                      const gecisler: any[] = gecisMatrisi.matris ?? []
                      const segmentler: string[] = gecisMatrisi.segments ?? []
                      const oncekiAy: string = gecisMatrisi.onceki_ay ?? ''
                      const buAy: string = gecisMatrisi.bu_ay ?? ''

                      // Build lookup map: kaynak → hedef → count
                      const lookup: Record<string, Record<string, number>> = {}
                      gecisler.forEach((g: any) => {
                        if (!lookup[g.kaynak_segment]) lookup[g.kaynak_segment] = {}
                        lookup[g.kaynak_segment][g.hedef_segment] = g.musteri_sayisi
                      })

                      // Big movers: transitions where kaynak !== hedef
                      const buyukGecisler = gecisler
                        .filter((g: any) => g.kaynak_segment !== g.hedef_segment)
                        .sort((a: any, b: any) => b.musteri_sayisi - a.musteri_sayisi)
                        .slice(0, 5)

                      const segRenk: Record<string, string> = {
                        'Şampiyonlar': '#16a34a', 'Sadık Müşteriler': '#2563eb', 'Potansiyel Sadıklar': '#7c3aed',
                        'Yeni Müşteriler': '#0891b2', 'Umut Vadenler': '#d97706', 'İhtiyaç Sahipleri': '#ea580c',
                        'Uyku Modunda': '#6b7280', 'Risk Altındakiler': '#dc2626', 'Kaybedilmek Üzereler': '#9f1239',
                        'Soğuyanlar': '#b45309', 'Kayıp Müşteriler': '#374151'
                      }

                      return (
                        <div>
                          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '12px' }}>
                            {oncekiAy} → {buAy} · {gecisler.filter((g: any) => g.kaynak_segment !== g.hedef_segment).reduce((s: number, g: any) => s + g.musteri_sayisi, 0).toLocaleString('tr-TR')} müşteri segment değiştirdi
                          </div>

                          {/* Top Moves */}
                          {buyukGecisler.length > 0 && (
                            <div style={{ marginBottom: '16px' }}>
                              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6b7280', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>En Büyük Geçişler</div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                {buyukGecisler.map((g: any, i: number) => {
                                  const isPositive = ['Şampiyonlar', 'Sadık Müşteriler', 'Potansiyel Sadıklar', 'Yeni Müşteriler'].includes(g.hedef_segment)
                                  return (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#f8fafc', borderRadius: '8px', fontSize: '0.82rem' }}>
                                      <span style={{ fontWeight: 600, color: segRenk[g.kaynak_segment] ?? '#374151', flex: '0 0 auto', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.kaynak_segment}</span>
                                      <span style={{ color: isPositive ? '#16a34a' : '#dc2626', fontWeight: 700 }}>{isPositive ? '→' : '→'}</span>
                                      <span style={{ fontWeight: 600, color: segRenk[g.hedef_segment] ?? '#374151', flex: 1 }}>{g.hedef_segment}</span>
                                      <span style={{ fontWeight: 700, color: isPositive ? '#16a34a' : '#dc2626', flexShrink: 0 }}>{g.musteri_sayisi.toLocaleString('tr-TR')} kişi</span>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}

                          {/* Matrix Table */}
                          {segmentler.length > 0 && (
                            <div style={{ overflowX: 'auto' }}>
                              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6b7280', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Geçiş Matrisi (Satır: Önceki Ay, Sütun: Bu Ay)</div>
                              <table style={{ borderCollapse: 'collapse', fontSize: '0.72rem', minWidth: '100%' }}>
                                <thead>
                                  <tr>
                                    <th style={{ padding: '4px 6px', textAlign: 'left', color: '#9ca3af', fontWeight: 600, borderBottom: '1px solid #e5e7eb', whiteSpace: 'nowrap' }}>↓ Önceki / Bu Ay →</th>
                                    {segmentler.map(s => (
                                      <th key={s} style={{ padding: '4px 6px', textAlign: 'center', color: segRenk[s] ?? '#374151', fontWeight: 600, borderBottom: '1px solid #e5e7eb', whiteSpace: 'nowrap', maxWidth: '80px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {s.length > 10 ? s.slice(0, 10) + '…' : s}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {segmentler.map(kaynak => (
                                    <tr key={kaynak}>
                                      <td style={{ padding: '4px 6px', fontWeight: 600, color: segRenk[kaynak] ?? '#374151', whiteSpace: 'nowrap', borderBottom: '1px solid #f3f4f6' }}>{kaynak.length > 12 ? kaynak.slice(0, 12) + '…' : kaynak}</td>
                                      {segmentler.map(hedef => {
                                        const val = lookup[kaynak]?.[hedef] ?? 0
                                        const isDiag = kaynak === hedef
                                        const isMove = !isDiag && val > 0
                                        return (
                                          <td key={hedef} style={{ padding: '4px 6px', textAlign: 'center', borderBottom: '1px solid #f3f4f6', background: isDiag ? '#f0fdf4' : isMove ? '#fef3c7' : 'transparent', fontWeight: isMove ? 700 : 400, color: isDiag ? '#16a34a' : isMove ? '#92400e' : '#d1d5db' }}>
                                            {val > 0 ? val.toLocaleString('tr-TR') : '–'}
                                          </td>
                                        )
                                      })}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                )}
              </div>

              {/* Arama */}
              <div style={{ position: 'relative', marginBottom: '16px' }}>
                <IconSearch size={16} stroke={2} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
                <input
                  value={etiketSearch}
                  onChange={e => setEtiketSearch(e.target.value)}
                  placeholder="Etiket ara..."
                  style={{ width: '100%', padding: '10px 36px', borderRadius: '10px', border: '1.5px solid #e5e7eb', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box' }}
                />
                {etiketSearch && (
                  <button onClick={() => setEtiketSearch('')} style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex' }}>
                    <IconX size={16} stroke={2} />
                  </button>
                )}
              </div>

              {/* Arama sonuçları */}
              {filteredEtiketler ? (
                <div style={{ background: 'white', borderRadius: '16px', padding: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
                  <div style={{ fontWeight: 600, color: '#6b7280', fontSize: '0.85rem', marginBottom: '12px' }}>
                    {filteredEtiketler.length} sonuç
                  </div>
                  {filteredEtiketler.map(e => (
                    <EtiketSatir
                      key={e.kolon}
                      etiket={e}
                      toplam={etiketData.toplam_musteri}
                      renk="#6366f1"
                      selected={selectedEtiket === e.kolon}
                      onClick={() => handleEtiketClick(e.kolon)}
                    />
                  ))}
                </div>
              ) : (
                /* Kategori accordion */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {KATEGORI_CONFIG.map(kat => {
                    const etiketler = etiketData.kategoriler[kat.key] || []
                    const enFazla = etiketler.reduce((max, e) => Math.max(max, e.sayi), 0)
                    const isOpen = expandedKategori === kat.key
                    return (
                      <div key={kat.key} style={{ background: 'white', borderRadius: '16px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)', overflow: 'hidden' }}>
                        <button
                          onClick={() => setExpandedKategori(isOpen ? '' : kat.key)}
                          style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 20px', background: 'none', border: 'none', cursor: 'pointer', borderBottom: isOpen ? `2px solid ${kat.renk}20` : 'none' }}
                        >
                          <span style={{ color: kat.renk }}>{kat.icon}</span>
                          <span style={{ fontWeight: 700, fontSize: '0.95rem', flex: 1, textAlign: 'left', color: '#111827' }}>{kat.ad}</span>
                          <span style={{ fontSize: '0.8rem', color: '#9ca3af', marginRight: '8px' }}>
                            {etiketler.length} etiket · en fazla {enFazla.toLocaleString('tr-TR')} müşteri
                          </span>
                          {isOpen
                            ? <IconChevronDown size={18} stroke={2} color="#9ca3af" />
                            : <IconChevronRight size={18} stroke={2} color="#9ca3af" />
                          }
                        </button>
                        {isOpen && (
                          <div style={{ padding: '8px 20px 16px' }}>
                            {etiketler.map(e => (
                              <EtiketSatir
                                key={e.kolon}
                                etiket={e}
                                toplam={etiketData.toplam_musteri}
                                renk={kat.renk}
                                selected={selectedEtiket === e.kolon}
                                onClick={() => handleEtiketClick(e.kolon)}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* ── Sağ: Seçili etiket müşteri listesi ── */}
            {selectedEtiket && (
              <div style={{ background: 'white', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.10)', overflow: 'hidden', position: 'sticky', top: '20px' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid #f3f4f6', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: '#111827' }}>
                      {ETIKET_ADLARI[selectedEtiket] || selectedEtiket}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '2px' }}>
                      {etiketData.etiketler.find(e => e.kolon === selectedEtiket)?.sayi.toLocaleString('tr-TR')} müşteri
                      · %{etiketData.etiketler.find(e => e.kolon === selectedEtiket)?.oran}
                    </div>
                    {ETIKET_ACIKLAMALARI[selectedEtiket] && (
                      <div style={{ fontSize: '0.78rem', color: '#4b5563', marginTop: '6px', lineHeight: 1.5, background: '#f9fafb', borderRadius: '6px', padding: '6px 8px', borderLeft: '3px solid #6366f1' }}>
                        {ETIKET_ACIKLAMALARI[selectedEtiket]}
                      </div>
                    )}
                  </div>
                  <Group gap="xs">
                    <ExcelExportButton
                      url={`/veri-kaynaklari/${selectedDataSourceId}/musteriler-excel/?etiketler=${selectedEtiket}`}
                      filename={`Segment_${selectedEtiket}.xlsx`}
                      label="Excel İndir"
                      size="xs"
                    />
                    <button
                      onClick={() => { setSelectedEtiket(null); setEtiketMusteriler([]); setSegmentDetail(null) }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex' }}
                    >
                      <IconX size={20} stroke={2} />
                    </button>
                  </Group>
                </div>

                {/* ── Grup Analizi / Insights ── */}
                <div style={{ padding: '16px 20px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '3px', height: '16px', background: '#6366f1', borderRadius: '4px' }}></div>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#374151', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Grup İçgörüleri</div>
                    </div>
                    {segmentDetail && <AISummaryButton contextType="segment_profile" contextId={selectedEtiket || ''} contextData={{ data_source_id: selectedDataSourceId }} />}
                  </div>

                  <div style={{ marginBottom: '16px' }}>
                    <AIInsightCard 
                      contextType="segment_profile" 
                      contextId={selectedEtiket || ''} 
                      dataSourceId={selectedDataSourceId || ''}
                      title={`${ETIKET_ADLARI[selectedEtiket || ''] || selectedEtiket} Profili`}
                      data={segmentDetail}
                    />
                  </div>

                  {detailLoading ? (
                    <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '4px' }}>
                      {[1, 2, 3].map(i => (
                        <div key={i} style={{ minWidth: '120px', height: '60px', background: '#f1f5f9', borderRadius: '10px', animation: 'pulse 1.5s infinite' }}></div>
                      ))}
                    </div>
                  ) : segmentDetail ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {/* Metrik Kartları */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                        <div style={{ background: 'white', padding: '10px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.03)', border: '1px solid #f1f5f9' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#6b7280', fontSize: '0.7rem', fontWeight: 600, marginBottom: '4px' }}>
                            <IconChartBar size={14} /> Ort. Harcama
                          </div>
                          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#111827' }}>₺{segmentDetail.metrics.avg_spend.toLocaleString('tr-TR')}</div>
                        </div>
                        <div style={{ background: 'white', padding: '10px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.03)', border: '1px solid #f1f5f9' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#6b7280', fontSize: '0.7rem', fontWeight: 600, marginBottom: '4px' }}>
                            <IconTarget size={14} /> Ort. Sepet
                          </div>
                          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#111827' }}>₺{segmentDetail.metrics.avg_basket.toLocaleString('tr-TR')}</div>
                        </div>
                        <div style={{ background: 'white', padding: '10px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.03)', border: '1px solid #f1f5f9' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#ef4444', fontSize: '0.7rem', fontWeight: 600, marginBottom: '4px' }}>
                            <IconAlertTriangle size={14} /> Churn Riski
                          </div>
                          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#ef4444' }}>%{segmentDetail.metrics.avg_churn_risk}</div>
                        </div>
                      </div>

                      {/* Alt Analizler */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6b7280', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <IconBulb size={14} color="#8b5cf6" /> Favori Kategoriler
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {segmentDetail.top_categories.map((cat, idx) => (
                              <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: 'white', borderRadius: '8px', fontSize: '0.75rem', border: '1px solid #f1f5f9' }}>
                                <span style={{ fontWeight: 600, color: '#4b5563' }}>{cat.category}</span>
                                <span style={{ color: '#9ca3af', fontWeight: 500 }}>{cat.count} kişi</span>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#6b7280', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <IconTrendingUp size={14} color="#3b82f6" /> Aktivite Durumu
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {segmentDetail.activity_dist.map((dist, idx) => (
                              <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: 'white', borderRadius: '8px', fontSize: '0.75rem', border: '1px solid #f1f5f9' }}>
                                <span style={{ fontWeight: 600, color: dist.status === 'Aktif' ? '#10b981' : '#f59e0b' }}>{dist.status}</span>
                                <span style={{ color: '#9ca3af', fontWeight: 500 }}>%{Math.round(dist.count / segmentDetail.metrics.total_count * 100)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>

                <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                  {/* Filtre Aktif Göstergesi */}
                  <div style={{ padding: '8px 12px', background: '#eef2ff', borderRadius: '8px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#6366f1', animation: 'pulse 2s infinite' }}></div>
                    <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#4338ca' }}>
                      "{ETIKET_ADLARI[selectedEtiket || ''] || selectedEtiket}" etiketine ait müşteriler listeleniyor
                    </span>
                    <span style={{ fontSize: '0.72rem', color: '#6366f1', marginLeft: 'auto', fontWeight: 500 }}>
                      {etiketMusteriler.length} / {etiketData?.etiketler.find(e => e.kolon === selectedEtiket)?.sayi || 0} müşteri
                    </span>
                  </div>

                  <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 4px', fontSize: '0.82rem' }}>
                    <thead style={{ position: 'sticky', top: 0, background: 'white', zIndex: 1 }}>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '8px 12px', color: '#6b7280', fontWeight: 600, borderBottom: '1.5px solid #f3f4f6' }}>Müşteri</th>
                        <th style={{ textAlign: 'center', padding: '8px 12px', color: '#6b7280', fontWeight: 600, borderBottom: '1.5px solid #f3f4f6' }}>Etiket</th>
                        <th style={{ textAlign: 'right', padding: '8px 12px', color: '#6b7280', fontWeight: 600, borderBottom: '1.5px solid #f3f4f6' }}>Harcama</th>
                      </tr>
                    </thead>
                    <tbody>
                      {etiketMusteriler.map((c, i) => (
                        <tr
                          key={i}
                          style={{ background: '#f8fafc', cursor: 'pointer' }}
                          onClick={() => navigate('/musteri-portali', { state: { customerId: c.id } })}
                          onMouseOver={e => e.currentTarget.style.background = '#eef2ff'}
                          onMouseOut={e => e.currentTarget.style.background = '#f8fafc'}
                        >
                          <td style={{ padding: '8px 12px', borderRadius: '6px 0 0 6px' }}>
                            <div style={{ fontWeight: 600, color: '#4f46e5' }}>{c.ad}</div>
                            <div style={{ fontSize: '0.72rem', color: '#6b7280' }}>#{c.id}</div>
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontSize: '0.7rem',
                              fontWeight: 600,
                              background: '#eef2ff',
                              color: '#4338ca',
                              border: '1px solid #c7d2fe'
                            }}>
                              {ETIKET_ADLARI[selectedEtiket || ''] || selectedEtiket}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: '#4f46e5', borderRadius: '0 6px 6px 0' }}>
                            ₺{Number(c.total_spend || 0).toLocaleString('tr-TR')}
                          </td>
                        </tr>
                      ))}
                      {etiketMusteriler.length === 0 && !listLoading && (
                        <tr>
                          <td colSpan={3} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>Kayıt bulunamadı.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>

                  {listLoading && (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                      <div className="spinner" style={{ margin: '0 auto 8px' }}></div>
                      <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>Yükleniyor...</div>
                    </div>
                  )}

                  {listHasMore && !listLoading && (
                    <button
                      onClick={loadMore}
                      style={{ width: 'calc(100% - 32px)', margin: '8px 16px 16px', padding: '10px', backgroundColor: '#f3f4f6', border: 'none', borderRadius: '8px', color: '#4b5563', fontWeight: 700, cursor: 'pointer', fontSize: '0.9rem', transition: 'background 0.2s' }}
                      onMouseOver={e => e.currentTarget.style.backgroundColor = '#e5e7eb'}
                      onMouseOut={e => e.currentTarget.style.backgroundColor = '#f3f4f6'}
                    >
                      Daha Fazla Yükle
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </LoadingOverlay>
    </div>
  )
}

// ─── Alt bileşenler ───────────────────────────────────────────────────────────

function KpiCard({ gradient, shadow, label, value, sub, icon }: {
  gradient: string; shadow: string; label: string; value: string; sub?: string; icon: ReactNode
}) {
  return (
    <div style={{ background: gradient, borderRadius: '16px', padding: '24px', color: 'white', boxShadow: `0 10px 25px -5px ${shadow}`, position: 'relative', overflow: 'hidden' }}>
      <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '8px', fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: '2rem', fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '4px' }}>{sub}</div>}
      <div style={{ position: 'absolute', right: '-10px', bottom: '-10px', opacity: 0.12 }}>{icon}</div>
    </div>
  )
}

function EtiketSatir({ etiket, toplam, renk, selected, onClick }: {
  etiket: EtiketOzet; toplam: number; renk: string; selected: boolean; onClick: () => void
}) {
  const ad = ETIKET_ADLARI[etiket.kolon] || etiket.kolon
  const barWidth = toplam > 0 ? Math.min((etiket.sayi / toplam) * 100 * 3, 100) : 0

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 12px',
        borderRadius: '10px', cursor: 'pointer', marginBottom: '4px',
        background: selected ? renk + '15' : 'transparent',
        border: `1.5px solid ${selected ? renk : 'transparent'}`,
        transition: 'all 0.15s ease',
      }}
      onMouseOver={e => { if (!selected) e.currentTarget.style.background = '#f9fafb' }}
      onMouseOut={e => { if (!selected) e.currentTarget.style.background = 'transparent' }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.875rem', fontWeight: selected ? 700 : 500, color: selected ? renk : '#374151', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {ad}
        </div>
        <div style={{ height: '4px', background: '#f3f4f6', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${barWidth}%`, background: renk, borderRadius: '2px', opacity: 0.7 }} />
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{ fontSize: '0.875rem', fontWeight: 700, color: selected ? renk : '#111827' }}>
          {etiket.sayi.toLocaleString('tr-TR')}
        </div>
        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>%{etiket.oran}</div>
        {etiket.trend && etiket.trend.degisim_yonu !== 'sabit' && etiket.trend.degisim_yuzde > 0 && (
          <div style={{
            fontSize: '0.68rem', fontWeight: 600,
            color: etiket.trend.degisim_yonu === 'yukselis' ? '#10b981' : '#ef4444',
            display: 'flex', alignItems: 'center', gap: '2px', justifyContent: 'flex-end', marginTop: '1px'
          }}>
            {etiket.trend.degisim_yonu === 'yukselis' ? '▲' : '▼'}
            %{etiket.trend.degisim_yuzde}
          </div>
        )}
      </div>
    </div>
  )
}

