import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import apiClient from '../api/client'
import { aiClient } from '../api/aiClient'
import { CampaignRecommendation } from '../types/api'
import {
  IconArrowsCross, IconFlame, IconHeart, IconHeartBroken,
  IconRefresh, IconChevronDown, IconChevronUp, IconSortDescending,
  IconSortAscending,
  IconFolder, IconAlertTriangle, IconSparkles
} from '@tabler/icons-react'
import { AISummaryButton } from './ai/AISummaryButton'
import { CampaignVariantProducer } from './ai/CampaignVariantProducer'
import { CampaignScheduler } from './ai/CampaignScheduler'
import { IconCalendar } from '@tabler/icons-react'

// Kategori hiyerarşisi tipi: ana > alt1 > alt2[]
type CategoryHierarchy = Record<string, Record<string, string[]>>

export default function CampaignSuggestions() {
  const navigate = useNavigate()
  const [recommendations, setRecommendations] = useState<CampaignRecommendation[]>([])
  const [categoryHierarchy, setCategoryHierarchy] = useState<CategoryHierarchy>({})
  const [loading, setLoading] = useState(true)
  const [selectedGroupKey, setSelectedGroupKey] = useState<string | null>(null)
  const [selectedOneriId, setSelectedOneriId] = useState<number | null>(null)
  const [aiSummary, setAiSummary] = useState<string>('')
  const [variantProducerOpened, setVariantProducerOpened] = useState(false);
  const [activeCampaignForVariants, setActiveCampaignForVariants] = useState<any>(null);
  const [schedulerOpened, setSchedulerOpened] = useState(false);
  const [activeCampaignForSchedule, setActiveCampaignForSchedule] = useState<any>(null);
  const [loadingAi, setLoadingAi] = useState(false)
  const [activeTab, setActiveTab] = useState<string>('Cross-Sell')
  const [sortBy, setSortBy] = useState<string>('potansiyel_ciro')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [minLift, setMinLift] = useState<number>(0.0)
  const [minConfidence, setMinConfidence] = useState<number>(0)
  const [minFis, setMinFis] = useState<number>(0)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false)
  const [yoneticiler, setYoneticiler] = useState<{id: number, name: string}[]>([])
  const [brands, setBrands] = useState<{id: number, name: string}[]>([])
  const [yoneticiFilter, setYoneticiFilter] = useState<string>('all')
  const [brandFilter, setBrandFilter] = useState<string>('all')
  const [brandBothSides, setBrandBothSides] = useState(false)
  const campaignStatus = 'Tümü'
  const [page, setPage] = useState(1)
  const [totalCount, setTotalCount] = useState<number>(0)
  const [hasMore, setHasMore] = useState(true)
  const [categorySearch, setCategorySearch] = useState('')
  const [yoneticiDropdownOpen, setYoneticiDropdownOpen] = useState(false)
  const [yoneticiSearch, setYoneticiSearch] = useState('')
  const [brandDropdownOpen, setBrandDropdownOpen] = useState(false)
  const [brandSearch, setBrandSearch] = useState('')
  const [loadingMore, setLoadingMore] = useState(false)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [approvedTotalCount, setApprovedTotalCount] = useState(0)
  const [exportModalOpen, setExportModalOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState(0)
  const [exportStep, setExportStep] = useState('')
  const [approvedCampaigns, setApprovedCampaigns] = useState<CampaignRecommendation[]>([])
  const [loadingApproved, setLoadingApproved] = useState(false)
  const [locallyApprovedIds, setLocallyApprovedIds] = useState<Set<number>>(new Set())
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null)
  const [isStale, setIsStale] = useState(false)

  // Kategori listesi (Cross-Sell için lazy load)
  const [sourceCategories, setSourceCategories] = useState<any[]>([])
  const [categoriesLoading, setCategoriesLoading] = useState(false)
  const [categoriesHasMore, setCategoriesHasMore] = useState(false)
  const [categoriesPage, setCategoriesPage] = useState(1)
  const [categoriesTotalCount, setCategoriesTotalCount] = useState(0)
  const [openCategoryItems, setOpenCategoryItems] = useState<Record<string, { items: any[], page: number, hasMore: boolean, total: number }>>({})
  const [loadingCategoryItems, setLoadingCategoryItems] = useState<Record<string, boolean>>({})

  const [tabCounts, setTabCounts] = useState<Record<string, number>>({})
  const [filterCounts, setFilterCounts] = useState<{
    yonetici: Record<string, number>,
    kategori: Record<string, number>,
    marka_a: Record<string, number>,
    marka_b: Record<string, number>,
  }>({ yonetici: {}, kategori: {}, marka_a: {}, marka_b: {} })
  
  // Alt products modal states
  const [altModalOpen, setAltModalOpen] = useState(false)
  const [altProducts, setAltProducts] = useState<any[]>([])
  const [altLoading, setAltLoading] = useState(false)
  const [altCategory, setAltCategory] = useState<string>('')

  // Helper to extract metrics from VeriOzeti
  const extractMetric = (veriOzeti: string | undefined, pattern: RegExp): number => {
    if (!veriOzeti) return 0
    const match = veriOzeti.match(pattern)
    if (!match) return 0
    // Replace comma with dot if exists (as decimal), but don't remove dots
    const valStr = match[1].replace(',', '.')
    return parseFloat(valStr) || 0
  }

  // Robust search normalization helper for Turkish support
  const normalizeForSearch = (str: string): string => {
    if (!str) return ''
    return str
      .replace(/İ/g, 'i')
      .replace(/I/g, 'ı')
      .toLowerCase()
      .normalize('NFD') // Separate accents
      .replace(/[\u0300-\u036f]/g, '') // Remove accents
      .trim()
  }

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [hierarchyData, countsData, yoneticilerData, brandsData, filterCountsData] = await Promise.all([
        (apiClient as any).getCategoryHierarchy(),
        (apiClient as any).getCampaignCounts(campaignStatus),
        (apiClient as any).getKategoriYoneticileri(),
        (apiClient as any).getBrands(),
        (apiClient as any).getCampaignFilterCounts(campaignStatus, 'Cross-Sell')
      ])
      setCategoryHierarchy(hierarchyData || {})
      setTabCounts(countsData || {})
      setYoneticiler(yoneticilerData || [])
      setBrands(brandsData || [])
      if (filterCountsData) {
        setFilterCounts({
          yonetici: filterCountsData.yonetici || {},
          kategori: filterCountsData.kategori || {},
          marka_a: filterCountsData.marka_a || {},
          marka_b: filterCountsData.marka_b || {},
        })
      }
    } catch (error) {
      console.error('Error loading data:', error)
    }
  }

  const loadSourceCategories = async (reset = false) => {
    const targetPage = reset ? 1 : categoriesPage + 1
    if (reset) { setCategoriesLoading(true); setSourceCategories([]) }
    try {
      const data = await (apiClient as any).getCampaignSourceCategories({
        status: campaignStatus,
        type: 'Cross-Sell',
        yonetici: yoneticiFilter,
        brand: brandFilter,
        brand_both_sides: brandBothSides,
        min_lift: minLift,
        min_confidence: minConfidence,
        min_fis: minFis,
        sort_by: sortBy === 'potansiyel_ciro' ? 'ciro' : sortBy === 'hedef_kitle' ? 'musteri' : sortBy === 'fis_sayisi' ? 'fis' : 'ciro',
        sort_order: sortOrder,
        page: targetPage,
        limit: 50,
      })
      setSourceCategories(prev => reset ? (data.categories || []) : [...prev, ...(data.categories || [])])
      setCategoriesTotalCount(data.total_count || 0)
      setCategoriesHasMore(data.has_more || false)
      setCategoriesPage(targetPage)
    } catch (e) {
      console.error('loadSourceCategories error', e)
    } finally {
      setCategoriesLoading(false)
    }
  }

  const CATEGORY_PAGE_SIZE = 20

  const loadCategoryItems = async (kaynak_kategori_ad: string) => {
    if (openCategoryItems[kaynak_kategori_ad]) {
      // toggle — kapat
      setOpenCategoryItems(prev => { const n = {...prev}; delete n[kaynak_kategori_ad]; return n })
      return
    }
    setLoadingCategoryItems(prev => ({ ...prev, [kaynak_kategori_ad]: true }))
    try {
      const data = await (apiClient as any).getCampaignRecommendations(
        campaignStatus, 'Cross-Sell', kaynak_kategori_ad,
        yoneticiFilter, brandFilter, 1, CATEGORY_PAGE_SIZE,
        sortBy, sortOrder.toUpperCase() as 'ASC' | 'DESC',
        minLift, minConfidence, minFis, brandBothSides
      )
      const recs = data.recommendations || []
      const total = data.total_count || recs.length
      setOpenCategoryItems(prev => ({
        ...prev,
        [kaynak_kategori_ad]: { items: recs, page: 1, hasMore: total > recs.length, total }
      }))
      const approvedFromServer = new Set<number>(recs.filter((r: any) => r.OneriDurumu === 'Onaylandi').map((r: any) => Number(r.OneriID)))
      if (approvedFromServer.size > 0) setLocallyApprovedIds(prev => new Set<number>([...prev, ...approvedFromServer]))
      // Son güncelleme bilgisini al
      if (data?.last_refreshed !== undefined) setLastRefreshed(data.last_refreshed)
      if (data?.is_stale !== undefined) setIsStale(data.is_stale)
    } catch (e) {
      console.error('loadCategoryItems error', e)
    } finally {
      setLoadingCategoryItems(prev => ({ ...prev, [kaynak_kategori_ad]: false }))
    }
  }

  const loadMoreCategoryItems = async (kaynak_kategori_ad: string) => {
    const current = openCategoryItems[kaynak_kategori_ad]
    if (!current || !current.hasMore) return
    const nextPage = current.page + 1
    setLoadingCategoryItems(prev => ({ ...prev, [kaynak_kategori_ad]: true }))
    try {
      const data = await (apiClient as any).getCampaignRecommendations(
        campaignStatus, 'Cross-Sell', kaynak_kategori_ad,
        yoneticiFilter, brandFilter, nextPage, CATEGORY_PAGE_SIZE,
        sortBy, sortOrder.toUpperCase() as 'ASC' | 'DESC',
        minLift, minConfidence, minFis, brandBothSides
      )
      const newRecs = data.recommendations || []
      const total = data.total_count || current.total
      setOpenCategoryItems(prev => ({
        ...prev,
        [kaynak_kategori_ad]: {
          items: [...current.items, ...newRecs],
          page: nextPage,
          hasMore: (current.items.length + newRecs.length) < total,
          total
        }
      }))
      const approvedFromServer = new Set<number>(newRecs.filter((r: any) => r.OneriDurumu === 'Onaylandi').map((r: any) => Number(r.OneriID)))
      if (approvedFromServer.size > 0) setLocallyApprovedIds(prev => new Set<number>([...prev, ...approvedFromServer]))
    } catch (e) {
      console.error('loadMoreCategoryItems error', e)
    } finally {
      setLoadingCategoryItems(prev => ({ ...prev, [kaynak_kategori_ad]: false }))
    }
  }

  const loadRecommendations = async (reset = false) => {
    const targetPage = reset ? 1 : page + 1
    if (reset) {
      setLoading(true)
      setPage(1)
    } else {
      setLoadingMore(true)
    }
    
    try {
      const data = await (apiClient as any).getCampaignRecommendations(
        campaignStatus,
        activeTab,
        categoryFilter,
        yoneticiFilter,
        brandFilter,
        targetPage,
        50,
        sortBy,
        sortOrder,
        minLift,
        minConfidence,
        minFis,
        brandBothSides
      )
      
      // LOG: Detailed response info for Railway debugging
      if (typeof data === 'string' && data.includes('<!DOCTYPE html>')) {
        console.error('CRITICAL: API returned HTML instead of JSON. Proxy/Routing issue detected.')
      }

      const recs = data?.recommendations || (Array.isArray(data) ? data : [])
      
      if (!Array.isArray(recs)) {
        console.error('Error parsing campaign recommendations: Data is not an array', data)
        if (reset) {
          setRecommendations([])
          setTotalCount(0)
        }
        setHasMore(false) // No more data if parsing failed
      } else {
        if (reset) {
          setRecommendations(recs)
        } else {
          setRecommendations(prev => [...prev, ...recs])
          setPage(targetPage)
        }
        // Onaylandi olanları locallyApprovedIds'e ekle
        const approvedFromServer = new Set(recs.filter((r: any) => r.OneriDurumu === 'Onaylandi').map((r: any) => r.OneriID))
        if (approvedFromServer.size > 0) {
          setLocallyApprovedIds(prev => new Set([...prev, ...approvedFromServer]))
        }
        setTotalCount(prev => data?.total_count ?? (reset ? recs.length : prev + recs.length))
        setHasMore(recs.length === 50)
        // Son güncelleme bilgisini al
        if (data?.last_refreshed !== undefined) setLastRefreshed(data.last_refreshed)
        if (data?.is_stale !== undefined) setIsStale(data.is_stale)
      }
    } catch (err) {
      console.error('Error loading recommendations:', err)
      // On error, ensure we don't keep old data
      if (reset) {
        setRecommendations([])
      }
      setHasMore(false) // No more data on error
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  const loadCounts = async () => {
    try {
      const counts = await (apiClient as any).getCampaignCounts(campaignStatus)
      setTabCounts(counts || {})
    } catch (error) {
      console.error('Error loading tab counts:', error)
    }
    try {
      const fCounts = await (apiClient as any).getCampaignFilterCounts(campaignStatus, activeTab)
      if (fCounts && !fCounts.error) setFilterCounts(fCounts)
    } catch (error) {
      console.error('Error loading filter counts:', error)
    }
    try {
      await loadApprovedCampaigns()
    } catch (error) {
      console.error('Error loading approved campaigns:', error)
    }
  }

  useEffect(() => {
    if (activeTab === 'Cross-Sell') {
      loadSourceCategories(true)
      setOpenCategoryItems({})
    } else {
      loadRecommendations(true)
    }
    loadCounts()
  }, [activeTab, categoryFilter, yoneticiFilter, brandFilter, brandBothSides, sortBy, sortOrder, minLift, minConfidence, minFis])

  // "Onayla" → AI Takvim'e ekle ve /ai-takvim'e yönlendir (sepete ekleme yok)
  const handleApproveToCalendar = async (campaign: any) => {
    if (!campaign) return
    try {
      const urunAdi = campaign.UrunAdi || campaign.IkinciUrunAdi || campaign.KategoriAdi || ''
      await aiClient.scheduleCampaign({
        title: `${campaign.KampanyaTipi}${urunAdi ? ' — ' + urunAdi : ''}`,
        description: campaign.Gerekcesi || campaign.BeklenenSonuc || '',
        segment: campaign.HedefSegment || 'Tüm Müşteriler',
        channel: 'email',
        scheduled_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
      })
      navigate('/ai-takvim')
    } catch (err) {
      console.error('Takvime eklenemedi:', err)
    }
  }

  // "Dışa Aktar" → sadece kampanya sepetine ekle (Onaylandi durumuna al)
  const handleAddToBasket = async (id: number) => {
    try {
      await (apiClient as any).updateRecommendationStatus(id, 'Onaylandi')
      setLocallyApprovedIds(prev => new Set(prev).add(id))
      setApprovedTotalCount(prev => prev + 1)
      const approved = recommendations.find(r => r.OneriID === id)
      if (approved) setApprovedCampaigns(prev => [approved, ...prev])
    } catch (error) {
      console.error('Sepete eklenemedi:', error)
    }
  }

  const handleUpdateStatus = async (id: number, status: string) => {
    try {
      await (apiClient as any).updateRecommendationStatus(id, status)
      if (status !== 'Onaylandi') {
        setLocallyApprovedIds(prev => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
        loadRecommendations(true)
        loadCounts()
        setSelectedGroupKey(null)
      }
    } catch (error) {
      console.error('Error updating status:', error)
    }
  }

  const loadApprovedCampaigns = async () => {
    setLoadingApproved(true)
    try {
      // Hem toplam sayıyı hem de listeyi çekiyoruz
      const [countsData, recsData] = await Promise.all([
        (apiClient as any).getCampaignCounts('Onaylandi'),
        (apiClient as any).getCampaignRecommendations('Onaylandi', 'Tümü', 'all', 'all', 'all', 1, 100)
      ])
      
      setApprovedTotalCount(countsData?.Tümü || 0)
      setApprovedCampaigns(recsData?.recommendations || [])
    } catch (error) {
      console.error('Error loading approved campaigns:', error)
    } finally {
      setLoadingApproved(false)
    }
  }

  const handleRemoveFromBasket = async (id: number) => {
    try {
      await (apiClient as any).updateRecommendationStatus(id, 'Bekliyor')
      setLocallyApprovedIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      loadCounts() // Bu aynı zamanda loadApprovedCampaigns'i de tetikleyecek (modal açıksa)
      loadRecommendations(true)
    } catch (error) {
      console.error('Error removing from basket:', error)
    }
  }

  const handleClearBasket = async () => {
    if (!confirm('Sepetteki tüm kampanyaları temizlemek istediğinize emin misiniz?')) return
    
    const ids = approvedCampaigns.map(r => r.OneriID)
    if (ids.length === 0) return

    try {
      await (apiClient as any).bulkUpdateRecommendationStatus(ids, 'Bekliyor')
      setLocallyApprovedIds(prev => {
        const next = new Set(prev)
        ids.forEach(id => next.delete(id))
        return next
      })
      setExportModalOpen(false)
      loadCounts()
      loadRecommendations(true)
    } catch (error) {
      console.error('Error clearing basket:', error)
    }
  }

  // Modal açıldığında zaten pre-fetch yapılmış olacağı için buraya gerek kalmadı
  // Ama yine de en güncel veriyi görmek adına loadCounts çağırılabilir (ihtiyaca göre)

  const loadAiSummary = async (id: number) => {
    setLoadingAi(true)
    try {
      const data = await (apiClient as any).getCampaignAiSummary(id)
      setAiSummary(data.summary)
    } catch (error) {
      console.error('Error loading AI summary:', error)
    } finally {
      setLoadingAi(false)
    }
  }

  const handleCategoryClick = (e: React.MouseEvent, name: string, onerilenUrunler?: any, hedefMusteri?: number, onerilenMinTutar?: number, toplamPotansiyelCiro?: number) => {
    e.stopPropagation()
    setAltCategory(name)
    setAltModalOpen(true)
    let products: any[] = []
    try {
      if (typeof onerilenUrunler === 'string') products = JSON.parse(onerilenUrunler)
      else if (Array.isArray(onerilenUrunler)) products = onerilenUrunler
    } catch (e) { /* ignore */ }

    const mapped = products.map(p => {
      const normalFiyat = p.gercek_avg > 0 ? p.gercek_avg
        : (p.ort && p.ort !== 100) ? p.ort
        : (onerilenMinTutar ? onerilenMinTutar / 0.75 : 0)
      const kampanyaFiyat = normalFiyat > 0 ? Math.round(normalFiyat * 0.75 * 100) / 100 : (onerilenMinTutar || 0)
      return {
        ad: p.ad,
        normal_fiyat: normalFiyat > 0 ? Math.round(normalFiyat * 100) / 100 : null,
        kampanya_fiyat: kampanyaFiyat || null,
        _kf: kampanyaFiyat,
      }
    })

    // AI özeti ile aynı mantık: potansiyel_ciro'yu kampanya fiyatına orantılı böl
    const toplamKF = mapped.reduce((s, p) => s + (p._kf || 0), 0) || 1
    const finalMapped = mapped.map(p => ({
      ad: p.ad,
      normal_fiyat: p.normal_fiyat,
      kampanya_fiyat: p.kampanya_fiyat,
      potansiyel_ciro: toplamPotansiyelCiro && p._kf
        ? Math.round(toplamPotansiyelCiro * p._kf / toplamKF * 100) / 100
        : (p._kf && hedefMusteri ? Math.round(p._kf * hedefMusteri * 100) / 100 : null),
    }))
    finalMapped.sort((a, b) => (b.potansiyel_ciro || 0) - (a.potansiyel_ciro || 0))
    setAltProducts(finalMapped)
  }

  const handleExportExcel = async (specificIds?: number[]) => {
    setIsExporting(true)
    setExportProgress(0)
    setExportStep('Kampanyalar hazırlanıyor...')

    // Aşamalı progress simülasyonu — backend işlem süresiyle senkronize
    let progressInterval: ReturnType<typeof setInterval> | null = null
    const startProgress = (target: number, durationMs: number) => {
      if (progressInterval) clearInterval(progressInterval)
      const steps = 30
      const stepMs = durationMs / steps
      let current = exportProgress
      progressInterval = setInterval(() => {
        current = Math.min(current + (target - current) * 0.15, target - 1)
        setExportProgress(Math.round(current))
      }, stepMs)
    }

    try {
      let ids = specificIds || []

      if (ids.length === 0) {
        setExportStep('Kampanyalar yükleniyor...')
        startProgress(20, 1500)
        // Önce onaylıları dene, yoksa bekleyenleri al
        let recs = await (apiClient as any).getCampaignRecommendations('Onaylandi', 'Tümü', 'all', 'all', 'all', 1, 1000)
        ids = recs?.recommendations?.map((r: any) => r.OneriID) || []
        if (ids.length === 0) {
          recs = await (apiClient as any).getCampaignRecommendations('Bekliyor', 'Tümü', 'all', 'all', 'all', 1, 1000)
          ids = recs?.recommendations?.map((r: any) => r.OneriID) || []
        }
      }

      if (ids.length === 0) {
        alert("Dışa aktarılacak kampanya bulunamadı.")
        return
      }

      setExportStep('Sunucu hazırlanıyor...')
      startProgress(40, 3000)
      // Backend'i önceden uyandır (Railway cold start önlemi)
      try { await fetch('/api/health/', { signal: AbortSignal.timeout(5000) }) } catch (_) {}

      setExportStep('Müşteri verileri sorgulanıyor...')
      startProgress(80, 50000)

      const apiBase = (window as any).__API_BASE__ || 'https://api.xpluscrm.com'
      const downloadUrl = `${apiBase}/api/kampanya-onerileri/disa-aktar/?ids=${ids.join(',')}`
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 90000) // 90s timeout
      const authToken = localStorage.getItem('auth_token')
      const response = await fetch(downloadUrl, {
        signal: controller.signal,
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      })
      clearTimeout(timeoutId)

      if (progressInterval) clearInterval(progressInterval)

      if (!response.ok) {
        const contentType = response.headers.get('content-type') || ''
        if (contentType.includes('text/html')) {
          throw new Error(`Sunucu hatası (${response.status}). Lütfen daha az kampanya seçerek tekrar deneyin.`)
        }
        const errorText = await response.text()
        throw new Error(errorText || `HTTP ${response.status}`)
      }

      setExportProgress(85)
      setExportStep('Excel dosyası oluşturuluyor...')
      const blob = await response.blob()

      setExportProgress(95)
      setExportStep('İndirme başlatılıyor...')
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const disposition = response.headers.get('Content-Disposition')
      const filenameMatch = disposition?.match(/filename="?([^"]+)"?/)
      a.download = filenameMatch?.[1] || `Kampanya_Listesi_${new Date().toISOString().slice(0,10)}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setExportProgress(100)
      setExportStep('Tamamlandı!')
      await new Promise(r => setTimeout(r, 800))
    } catch (error) {
      if (progressInterval) clearInterval(progressInterval)
      console.error('Export error:', error)
      alert("Hata: " + error)
    } finally {
      setIsExporting(false)
      setExportProgress(0)
      setExportStep('')
    }
  }



  const getPriorityColor = (p: number) => {
    if (p === 1) return '#ef4444'
    if (p === 2) return '#f59e0b'
    return '#3b82f6'
  }

  // Sabit kampanya tipleri (Sistem yeteneklerini göstermek için)
  // Sabit kampanya tipleri (Sistem yeteneklerini göstermek için)
  const campaignTabs = [
    { id: 'Cross-Sell', label: 'Çapraz Satış', icon: <IconArrowsCross size={18} stroke={1.8} /> },
    { id: 'Clearance', label: 'Stok Eritme', icon: <IconFlame size={18} stroke={1.8} /> },
    { id: 'Loyalty', label: 'RFM Kampanya', icon: <IconHeart size={18} stroke={1.8} /> },
    { id: 'Win-Back', label: 'Churn Kampanya', icon: <IconHeartBroken size={18} stroke={1.8} /> }
  ]

  const campaignLabels: Record<string, string> = {
    'Cross-Sell': 'Çapraz Satış',
    'Clearance': 'Stok Eritme',
    'Loyalty': 'RFM Kampanya',
    'Win-Back': 'Churn Kampanya'
  }
  
  // API'den gelen hiyerarşiyi kullan (ana > alt1 > alt2)
  const sortedAnaCategories = Object.keys(categoryHierarchy).sort()

  // Filtrelenmiş ve sıralanmış öneriler
  const filteredRecommendations = recommendations.filter(r => {
    // Reddedilenleri listede gösterme
    if (r.OneriDurumu === 'Reddedildi') return false
    // Kategori ve Tip filtreleri artık backend tarafında yapılıyor.
    // Sadece Çapraz Satış (Cross-Sell) için uygulanan metrik filtreleri burada kalıyor (anlık geri bildirim için).
    if (activeTab === 'Cross-Sell') {
      const lift = r.Lift ?? extractMetric(r.VeriOzeti, /(?:Lift|Güven Değer):\s*([\d,.]+)/)
      const confidence = r.Guven ?? extractMetric(r.VeriOzeti, /(?:Confidence|Güven Oran):\s*([\d,.]+)/)
      const fis = r.FisSayisi ?? extractMetric(r.VeriOzeti, /(?:Ortak Fiş|Kategori Fiş|Toplam Fiş Sayısı|Fiş):\s*([\d,.]+)/)
      
      if (lift < minLift) return false
      if (confidence < minConfidence) return false
      if (fis < minFis) return false
    }
    return true
  })

  // Gruplama mantığı - Render sırasında hesaplanır
  const groupedRecommendations = filteredRecommendations.reduce((acc, r) => {
    const groupKey = r.KampanyaTipi === 'Cross-Sell'
      ? (r.KaynakKategoriAd || r.HedefSegment?.replace(' Alıcıları', ''))
      : r.HedefSegment;

    // Cross-Sell için daha açıklayıcı grup başlığı
    const displayKey = r.KampanyaTipi === 'Cross-Sell'
      ? `${groupKey} Kategorisinden Alışveriş Yapanlar İçin Öneriler`
      : groupKey;
    
    if (!acc[displayKey]) {
      acc[displayKey] = {
        key: displayKey,
        sourceCategory: groupKey, // Filtrelemede kullanmak için orijinal adı sakla
        type: r.KampanyaTipi,
        items: [],
        totalCiro: 0,
        totalMusteri: 0,
        totalHedef: 0,
        totalFis: 0,
        maxOncelik: 3,
        latestDate: r.OlusturmaTarihi
      };
    }
    
    acc[displayKey].items.push(r);

    if (r.HedefMusteriSayisi) {
      acc[displayKey].totalMusteri += Math.round(r.HedefMusteriSayisi * 0.15);
      // Kaynak kategorinin toplam alıcısı — tüm item'larda aynı, sadece bir kez set et
      if (!acc[displayKey].totalHedef) acc[displayKey].totalHedef = r.HedefMusteriSayisi;
      const potCiro = r.PotansiyelCiro || 0;
      acc[displayKey].totalCiro += potCiro;
      acc[displayKey]._ciroCount = (acc[displayKey]._ciroCount || 0) + 1;
    }
    if (r.FisSayisi) acc[displayKey].totalFis += r.FisSayisi;
    acc[displayKey].maxOncelik = Math.min(acc[displayKey].maxOncelik, r.OncelikSeviye || 3);
    
    return acc;
  }, {} as Record<string, any>);

  // Sıralama backend SQL tarafından yapılıyor — frontend'de sadece gruplama korunur
  const displayGroups = Object.values(groupedRecommendations);

  return (
    <div style={{ padding: '24px', background: '#f8fafc', minHeight: '100vh' }}>
      <style>{`
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '0 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600, color: '#334155' }}>Otomatik Kampanya Önerileri</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
              <p style={{ margin: 0, color: '#64748b', fontSize: '0.85rem' }}>AI ve Veri Analizi tarafından üretilen stratejik fırsatlar</p>
              {lastRefreshed && (
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 10px',
                  borderRadius: '16px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  background: isStale ? '#fef3c7' : '#ecfdf5',
                  color: isStale ? '#92400e' : '#065f46',
                  border: `1px solid ${isStale ? '#fcd34d' : '#a7f3d0'}`
                }}>
                  {isStale && <IconAlertTriangle size={12} stroke={2} />}
                  Son güncelleme: {(() => {
                    try {
                      const d = new Date(lastRefreshed)
                      return d.toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric' })
                    } catch { 
                      return lastRefreshed && lastRefreshed.split('T')[0] 
                    }
                  })()}

                  {isStale && ' — Güncelleniyor...'}
                </span>
              )}
            </div>
          </div>
          <button 
            onClick={() => loadRecommendations(true)}
            style={{ padding: '10px 20px', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}
          >
            <IconRefresh size={16} stroke={2} style={{ marginRight: 6 }} /> Yenile
          </button>
        </div>

        {/* TAB SİSTEMİ */}
        <div style={{ marginBottom: '24px', borderBottom: '1px solid #e2e8f0', background: 'white', borderRadius: '12px 12px 0 0', padding: '0 16px' }}>
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', justifyContent: 'center' }}>
            {campaignTabs.map(tab => {
              // Get count from tabCounts state (populated on load and status change)
              const displayCount = tabCounts[tab.id] ?? 0;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id)
                    setCategoryFilter('all')
                    setYoneticiFilter('all')
                    setBrandFilter('all')
                  }}
                  style={{
                    padding: '16px 20px',
                    background: 'transparent',
                    color: activeTab === tab.id ? '#6366f1' : '#64748b',
                    border: 'none',
                    borderBottom: activeTab === tab.id ? '3px solid #6366f1' : '3px solid transparent',
                    cursor: 'pointer',
                    fontWeight: activeTab === tab.id ? 700 : 500,
                    fontSize: '0.95rem',
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    opacity: displayCount === 0 ? 0.6 : 1
                  }}
                  onMouseEnter={(e) => {
                    if (activeTab !== tab.id) {
                      e.currentTarget.style.color = '#4f46e5'
                      e.currentTarget.style.borderBottom = '3px solid #e2e8f0'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeTab !== tab.id) {
                      e.currentTarget.style.color = '#64748b'
                      e.currentTarget.style.borderBottom = '3px solid transparent'
                    }
                  }}
                >
                  <span style={{ display: 'flex' }}>{tab.icon}</span>
                  <span>{tab.label}</span>
                  <span style={{ 
                    fontSize: '0.75rem', 
                    background: activeTab === tab.id ? '#6366f1' : '#f1f5f9',
                    color: activeTab === tab.id ? 'white' : '#64748b',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontWeight: 700
                  }}>
                    {displayCount.toLocaleString('tr-TR')}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* SIRALAMA VE KATEGORİ FİLTRESİ */}
        <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
          
          {/* Kategori Yöneticisi Filtresi - Sadece Cross-Sell */}
          {activeTab === 'Cross-Sell' && <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: '#64748b' }}> Kategori Yöneticisi:</span>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setYoneticiDropdownOpen(!yoneticiDropdownOpen)
                  setBrandDropdownOpen(false)
                  setCategoryDropdownOpen(false)
                }}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  background: 'white',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: 500,
                  color: '#475569',
                  minWidth: '200px',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span>{yoneticiFilter === 'all' ? 'Tüm Yöneticiler' : (yoneticiler.find(b => b.id.toString() === yoneticiFilter.toString())?.name || yoneticiFilter)}</span>
                <span style={{ marginLeft: '8px', display: 'flex' }}>{yoneticiDropdownOpen ? <IconChevronUp size={14} stroke={2} /> : <IconChevronDown size={14} stroke={2} />}</span>
              </button>

              {yoneticiDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  zIndex: 200,
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  maxHeight: '400px',
                  overflowY: 'auto',
                  minWidth: '250px',
                  marginTop: '4px'
                }}>
                  <div style={{ 
                    position: 'sticky', 
                    top: 0, 
                    background: 'white', 
                    padding: '8px', 
                    borderBottom: '1px solid #e2e8f0',
                    zIndex: 2
                  }}>
                    <input
                      type="text"
                      placeholder="Kategori yöneticisi ara..."
                      value={yoneticiSearch}
                      onChange={(e) => setYoneticiSearch(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        fontSize: '0.85rem'
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>

                  <div
                    onClick={() => { setYoneticiFilter('all'); setYoneticiDropdownOpen(false) }}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      background: yoneticiFilter === 'all' ? '#e0f2fe' : 'transparent',
                      fontWeight: 600,
                      borderBottom: '1px solid #e2e8f0'
                    }}
                  >
                     Tüm Yöneticiler
                  </div>

                  {yoneticiler
                    .filter(b => (filterCounts.yonetici[b.id.toString()] ?? 0) > 0)
                    .filter(b => !yoneticiSearch || normalizeForSearch(b.name).includes(normalizeForSearch(yoneticiSearch)))
                    .map(b => (
                      <div
                        key={b.id}
                        onClick={() => { setYoneticiFilter(b.id.toString()); setYoneticiDropdownOpen(false) }}
                        style={{
                          padding: '8px 12px',
                          cursor: 'pointer',
                          background: yoneticiFilter.toString() === b.id.toString() ? '#e0f2fe' : 'transparent',
                          borderBottom: '1px solid #f1f5f9',
                          fontSize: '0.9rem',
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                        }}
                      >
                        <span>{b.name}</span>
                        {filterCounts.yonetici[b.id.toString()] !== undefined && (
                          <span style={{ fontSize: '0.75rem', color: '#6366f1', fontWeight: 600, background: '#eef2ff', padding: '1px 6px', borderRadius: '10px' }}>
                            {filterCounts.yonetici[b.id.toString()]}
                          </span>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>}


          {/* Marka Filtresi - Sadece Cross-Sell */}
          {activeTab === 'Cross-Sell' && <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: '#64748b' }}> Marka:</span>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setBrandDropdownOpen(!brandDropdownOpen)
                  setYoneticiDropdownOpen(false)
                  setCategoryDropdownOpen(false)
                }}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  background: 'white',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: 500,
                  color: '#475569',
                  minWidth: '200px',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span>{brandFilter === 'all' ? 'Tüm Markalar' : (brands.find(b => b.id.toString() === brandFilter.toString())?.name || brandFilter)}</span>
                <span style={{ marginLeft: '8px', display: 'flex' }}>{brandDropdownOpen ? <IconChevronUp size={14} stroke={2} /> : <IconChevronDown size={14} stroke={2} />}</span>
              </button>

              {brandDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  zIndex: 200,
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  maxHeight: '400px',
                  overflowY: 'auto',
                  minWidth: '250px',
                  marginTop: '4px'
                }}>
                  <div style={{ 
                    position: 'sticky', 
                    top: 0, 
                    background: 'white', 
                    padding: '8px', 
                    borderBottom: '1px solid #e2e8f0',
                    zIndex: 2
                  }}>
                    <input
                      type="text"
                      placeholder="Marka ara..."
                      value={brandSearch}
                      onChange={(e) => setBrandSearch(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        fontSize: '0.85rem'
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>

                  <div
                    onClick={() => { setBrandFilter('all'); setBrandBothSides(false); setBrandDropdownOpen(false) }}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      background: brandFilter === 'all' ? '#e0f2fe' : 'transparent',
                      fontWeight: 600,
                      borderBottom: '1px solid #e2e8f0'
                    }}
                  >
                     Tüm Markalar
                  </div>

                  {brands
                    .filter(b => (filterCounts.marka_a[b.id.toString()] ?? 0) > 0 || (filterCounts.marka_b[b.id.toString()] ?? 0) > 0)
                    .filter(b => !brandSearch || normalizeForSearch(b.name).includes(normalizeForSearch(brandSearch)))
                    .map(b => (
                      <div
                        key={b.id}
                        onClick={() => { setBrandFilter(b.id.toString()); setBrandDropdownOpen(false) }}
                        style={{
                          padding: '8px 12px',
                          cursor: 'pointer',
                          background: brandFilter.toString() === b.id.toString() ? '#e0f2fe' : 'transparent',
                          borderBottom: '1px solid #f1f5f9',
                          fontSize: '0.9rem',
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                        }}
                      >
                        <span>{b.name}</span>
                        <span style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                          {filterCounts.marka_a[b.id.toString()] !== undefined && (
                            <span title="Kaynak kategoride" style={{ fontSize: '0.7rem', color: '#6366f1', fontWeight: 600, background: '#eef2ff', padding: '1px 5px', borderRadius: '10px' }}>
                              {filterCounts.marka_a[b.id.toString()]}
                            </span>
                          )}
                          {filterCounts.marka_b[b.id.toString()] !== undefined && (
                            <span title="Her iki kategoride" style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 600, background: '#f0fdf4', padding: '1px 5px', borderRadius: '10px' }}>
                              {filterCounts.marka_b[b.id.toString()]}
                            </span>
                          )}
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>}

          {activeTab === 'Cross-Sell' && brandFilter !== 'all' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.85rem', color: brandBothSides ? '#6366f1' : '#64748b', fontWeight: brandBothSides ? 600 : 400 }}>
                {brandBothSides ? '↔ Her iki kategoride marka' : 'Sadece kaynak kategoride'}
              </span>
              <button
                onClick={() => setBrandBothSides(!brandBothSides)}
                style={{
                  width: '40px', height: '22px', borderRadius: '11px',
                  border: 'none', cursor: 'pointer',
                  background: brandBothSides ? '#6366f1' : '#cbd5e1',
                  position: 'relative', transition: 'background 0.2s', flexShrink: 0
                }}
              >
                <span style={{
                  position: 'absolute', top: '3px',
                  left: brandBothSides ? '21px' : '3px',
                  width: '16px', height: '16px',
                  borderRadius: '50%', background: 'white',
                  transition: 'left 0.2s', boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                }} />
              </button>
            </div>
          )}


          {/* Kategori Filtresi - Sadece Çapraz Satış için gösterilir */}
          {activeTab === 'Cross-Sell' && (
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: '#64748b' }}> Kategori:</span>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setCategoryDropdownOpen(!categoryDropdownOpen)
                  setYoneticiDropdownOpen(false)
                  setBrandDropdownOpen(false)
                }}
                style={{
                  padding: '8px 16px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  background: 'white',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: 500,
                  color: '#475569',
                  minWidth: '200px',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span>{categoryFilter === 'all' ? 'Tüm Kategoriler' : categoryFilter}</span>
                <span style={{ marginLeft: '8px', display: 'flex' }}>{categoryDropdownOpen ? <IconChevronUp size={14} stroke={2} /> : <IconChevronDown size={14} stroke={2} />}</span>
              </button>
              
              {categoryDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  zIndex: 100,
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                  maxHeight: '400px',
                  overflowY: 'auto',
                  minWidth: '280px',
                  marginTop: '4px'
                }}>
                  {/* Kategori Ara */}
                  <div style={{ 
                    position: 'sticky', 
                    top: 0, 
                    background: 'white', 
                    padding: '8px', 
                    borderBottom: '1px solid #e2e8f0',
                    zIndex: 2
                  }}>
                    <input
                      type="text"
                      placeholder="Kategori ara..."
                      value={categorySearch}
                      onChange={(e) => setCategorySearch(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        fontSize: '0.85rem'
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>

                  {/* Tüm Kategoriler seçeneği */}
                  <div
                    onClick={() => { setCategoryFilter('all'); setCategoryDropdownOpen(false) }}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      background: categoryFilter === 'all' ? '#e0f2fe' : 'transparent',
                      fontWeight: 600,
                      borderBottom: '1px solid #e2e8f0'
                    }}
                  >
                     Tüm Kategoriler
                  </div>
                  
                  {/* Hiyerarşik kategoriler */}
                  {sortedAnaCategories
                    .filter(ana => {
                      // Ana kategorinin kendisi veya altındaki herhangi bir kategori kampanya içeriyorsa göster
                      const hasCount = (filterCounts.kategori[ana] ?? 0) > 0 ||
                        Object.entries(categoryHierarchy[ana] || {}).some(([alt1, alt2List]) =>
                          (filterCounts.kategori[alt1] ?? 0) > 0 ||
                          (alt2List as string[]).some(alt2 => (filterCounts.kategori[alt2] ?? 0) > 0)
                        )
                      if (!hasCount) return false
                      if (!categorySearch) return true
                      const s = normalizeForSearch(categorySearch)
                      const anaMatch = normalizeForSearch(ana).includes(s)
                      const childrenMatch = Object.entries(categoryHierarchy[ana] || {}).some(([alt1, alt2List]) => {
                        if (normalizeForSearch(alt1).includes(s)) return true
                        return (alt2List as string[]).some(alt2 => normalizeForSearch(alt2).includes(s))
                      })
                      return anaMatch || childrenMatch
                    })
                    .map((ana: string) => (
                    <div key={ana}>
                      {/* Ana kategori başlığı */}
                      <div
                        onClick={() => {
                          setExpandedCategories(prev => {
                            const next = new Set(prev)
                            if (next.has(ana)) next.delete(ana)
                            else next.add(ana)
                            return next
                          })
                        }}
                        style={{
                          padding: '8px 12px',
                          cursor: 'pointer',
                          background: '#f8fafc',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          borderBottom: '1px solid #f1f5f9'
                        }}
                      >
                        <span><IconFolder size={14} stroke={1.8} /></span>
                        <span style={{ flex: 1 }}>{ana}</span>
                        {filterCounts.kategori[ana] !== undefined && (
                          <span style={{ fontSize: '0.7rem', color: '#6366f1', fontWeight: 600, background: '#eef2ff', padding: '1px 5px', borderRadius: '10px' }}>
                            {filterCounts.kategori[ana]}
                          </span>
                        )}
                        <span style={{ display: 'flex', marginLeft: '4px' }}>
                          {expandedCategories.has(ana) ? <IconChevronUp size={14} stroke={2} /> : <IconChevronDown size={14} stroke={2} />}
                        </span>
                      </div>
                      
                      {/* Alt kategoriler (açıksa veya arama yapılıyorsa) */}
                      {(expandedCategories.has(ana) || categorySearch) && (
                        <div style={{ background: '#fafbfc' }}>
                          {Object.entries(categoryHierarchy[ana] || {})
                            .filter(([alt1, alt2List]) => {
                                // Alt1 veya alt2'lerinden biri kampanya içeriyorsa göster
                                const hasCount = (filterCounts.kategori[alt1] ?? 0) > 0 ||
                                  (alt2List as string[]).some(alt2 => (filterCounts.kategori[alt2] ?? 0) > 0)
                                if (!hasCount) return false
                                if (!categorySearch) return true
                                const s = normalizeForSearch(categorySearch)
                                return normalizeForSearch(alt1).includes(s) ||
                                  (alt2List as string[]).some(alt2 => normalizeForSearch(alt2).includes(s))
                            })
                            .map(([alt1, alt2List]) => (
                            <div key={alt1}>
                              {/* Alt1 */}
                              <div
                                onClick={() => { setCategoryFilter(alt1); setCategoryDropdownOpen(false) }}
                                style={{
                                  padding: '6px 12px 6px 28px',
                                  cursor: 'pointer',
                                  background: categoryFilter === alt1 ? '#e0f2fe' : 'transparent',
                                  fontSize: '0.9rem',
                                  display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                                }}
                              >
                                <span>├─ {alt1}</span>
                                {filterCounts.kategori[alt1] !== undefined && (
                                  <span style={{ fontSize: '0.7rem', color: '#6366f1', fontWeight: 600, background: '#eef2ff', padding: '1px 5px', borderRadius: '10px', flexShrink: 0 }}>
                                    {filterCounts.kategori[alt1]}
                                  </span>
                                )}
                              </div>
                              {/* Alt2'ler */}
                               {(alt2List as string[])
                                .filter(alt2 => (filterCounts.kategori[alt2] ?? 0) > 0)
                                .filter(alt2 => !categorySearch || normalizeForSearch(alt2).includes(normalizeForSearch(categorySearch)))
                                .map((alt2: string) => (
                                <div
                                  key={alt2}
                                  onClick={() => { setCategoryFilter(alt2); setCategoryDropdownOpen(false) }}
                                  style={{
                                    padding: '5px 12px 5px 44px',
                                    cursor: 'pointer',
                                    background: categoryFilter === alt2 ? '#e0f2fe' : 'transparent',
                                    fontSize: '0.85rem',
                                    color: '#64748b',
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                                  }}
                                >
                                  <span>└── {alt2}</span>
                                  {filterCounts.kategori[alt2] !== undefined && (
                                    <span style={{ fontSize: '0.7rem', color: '#6366f1', fontWeight: 600, background: '#eef2ff', padding: '1px 5px', borderRadius: '10px', flexShrink: 0 }}>
                                      {filterCounts.kategori[alt2]}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

          {/* Sıralama ve Metrikler - Sadece Cross-Sell için gösterilir */}
          {activeTab === 'Cross-Sell' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
              {/* Sıralama */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.9rem', color: '#64748b' }}>Sırala:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    background: 'white',
                    fontSize: '0.9rem',
                    cursor: 'pointer',
                    fontWeight: 500,
                    color: '#475569'
                  }}
                >
                  <option value="default">Varsayılan (Öncelik)</option>
                  <option value="lift">Lift</option>
                  <option value="confidence"> Güven</option>
                  <option value="fis_sayisi"> Fiş Sayısı</option>
                  <option value="potansiyel_ciro"> Potansiyel Ciro</option>
                </select>

                <button
                  onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
                  style={{
                    padding: '8px',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    background: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title={sortOrder === 'desc' ? 'Azalan' : 'Artan'}
                >
                  {sortOrder === 'desc' ? <IconSortDescending size={16} stroke={2} /> : <IconSortAscending size={16} stroke={2} />}
                </button>
              </div>

              {/* Minimum Metrik Filtreleri */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Min Lift:</span>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={minLift}
                    onChange={(e) => setMinLift(parseFloat(e.target.value) || 0)}
                    style={{
                      width: '60px',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      border: '1px solid #e2e8f0',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Min Güven %:</span>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    max="100"
                    placeholder="5"
                    value={minConfidence ? Math.round(minConfidence * 100) : ''}
                    onChange={(e) => setMinConfidence((parseFloat(e.target.value) || 0) / 100)}
                    style={{
                      width: '70px',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      border: '1px solid #e2e8f0',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Min Fiş:</span>
                  <input
                    type="number"
                    step="10"
                    min="0"
                    value={minFis}
                    onChange={(e) => setMinFis(parseInt(e.target.value) || 0)}
                    style={{
                      width: '70px',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      border: '1px solid #e2e8f0',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
              </div>
            </div>
          )}

        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {activeTab === 'Cross-Sell' ? (
            categoriesLoading ? (
              <div style={{ padding: '40px', textAlign: 'center', background: 'white', borderRadius: '12px' }}>Yükleniyor...</div>
            ) : sourceCategories.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', background: 'white', borderRadius: '12px' }}>Öneri bulunamadı.</div>
            ) : (<>
              {sourceCategories.map((cat: any) => {
                const key = cat.kaynak_kategori_ad
                const catState = openCategoryItems[key]
                const isOpen = !!catState
                const items = (catState?.items || []).filter((r: any) => r.OneriDurumu !== 'Reddedildi')
                const hasMoreItems = catState?.hasMore || false
                const isLoading = loadingCategoryItems[key]
                return (
                  <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                    <div
                      onClick={() => loadCategoryItems(key)}
                      style={{
                        padding: '20px 24px',
                        background: '#ffffff',
                        borderRadius: isOpen ? '12px 12px 0 0' : '12px',
                        border: `1px solid ${isOpen ? '#e2e8f0' : '#f1f5f9'}`,
                        boxShadow: isOpen ? '0 4px 12px rgba(0,0,0,0.03)' : '0 1px 3px rgba(0,0,0,0.02)',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                          <div style={{ width: '44px', height: '44px', background: 'linear-gradient(135deg, #1e1b4b, #312e81)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '1.2rem', flexShrink: 0 }}>⇄</div>
                          <div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>KATEGORİ GRUBU</div>
                            <div style={{ fontSize: '1.05rem', fontWeight: 600, color: '#1e293b' }}>{key} Kategorisinden Alışveriş Yapanlar İçin Öneriler</div>
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexShrink: 0 }}>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>HEDEF KİTLE</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#6366f1' }}>{cat.toplam_hedef?.toLocaleString('tr-TR')}</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>POTANSİYEL CİRO</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981' }}>₺{Math.round(cat.toplam_ciro).toLocaleString('tr-TR')}</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>TOP. FİŞ</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#334155' }}>{cat.toplam_fis?.toLocaleString('tr-TR')}</div>
                          </div>
                          <div style={{ background: '#6366f1', color: 'white', borderRadius: '20px', padding: '4px 14px', fontWeight: 700, fontSize: '0.9rem', minWidth: '70px', textAlign: 'center' }}>
                            {isLoading ? '...' : cat.kampanya_sayisi} Öneri
                          </div>
                          <span style={{ color: '#94a3b8', fontSize: '1.2rem' }}>{isOpen ? '∧' : '∨'}</span>
                        </div>
                      </div>
                    </div>
                    {isOpen && items.length > 0 && (
                      <div style={{ background: '#f8fafc', borderRadius: '0 0 12px 12px', border: '1px solid #e2e8f0', borderTop: 'none', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', textAlign: 'right', paddingBottom: '4px' }}>
                          {items.length} / {catState?.total || items.length} kampanya gösteriliyor
                        </div>
                        {items.map((r: any) => {
                          const isOneriSelected = selectedOneriId === r.OneriID;
                          return (
                            <div
                              key={r.OneriID}
                              onClick={() => {
                                if (isOneriSelected) setSelectedOneriId(null)
                                else {
                                  setSelectedOneriId(r.OneriID)
                                  loadAiSummary(r.OneriID)
                                }
                              }}
                              style={{
                                background: 'white',
                                borderRadius: '10px',
                                border: `1px solid ${isOneriSelected ? '#e2e8f0' : '#f1f5f9'}`,
                                padding: '14px 16px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                position: 'relative'
                              }}
                              onMouseEnter={(e) => {
                                if (!isOneriSelected) {
                                  e.currentTarget.style.borderColor = '#cbd5e1';
                                  e.currentTarget.style.background = '#fafbfc';
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (!isOneriSelected) {
                                  e.currentTarget.style.borderColor = '#f1f5f9';
                                  e.currentTarget.style.background = 'white';
                                }
                              }}
                            >
                              {/* Bireysel Ürün/Kategori Akışı */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <span style={{ padding: '2px 8px', borderRadius: '4px', background: getPriorityColor(r.OncelikSeviye) + '10', color: getPriorityColor(r.OncelikSeviye), fontSize: '0.6rem', fontWeight: 700 }}>
                                    {r.OncelikSeviye === 1 ? <><IconAlertTriangle size={12} stroke={2} style={{ verticalAlign: 'middle', marginRight: 2 }} /> ACİL</> : `PRIORITY ${r.OncelikSeviye}`}
                                  </span>
                                </div>
                                <span style={{ fontSize: '0.65rem', color: '#94a3b8' }}>{r.OlusturmaTarihi}</span>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                <div style={{ flex: '0 0 160px' }}>
                                  {r.KaynakKategoriAd && r.KampanyaTipi === 'Cross-Sell' && (
                                    <div style={{ marginBottom: '4px', fontSize: '0.7rem', color: '#4f46e5', fontWeight: 700, background: '#eef2ff', padding: '2px 8px', borderRadius: '4px', display: 'inline-block' }}>
                                      {r.KaynakKategoriAd} alanlara öneriliyor
                                    </div>
                                  )}
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Kategori</div>
                                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#64748b' }}>{r.KategoriAdi}</div>
                                </div>
                                <div style={{ color: '#e2e8f0' }}>›</div>
                                <div style={{ flex: '1.2' }}>
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Önerilen Ürün(ler)</div>
                                  {(() => {
                                    let products: any[] = [];
                                    try {
                                      if (typeof r.OnerilenUrunler === 'string') {
                                        products = JSON.parse(r.OnerilenUrunler);
                                      } else if (Array.isArray(r.OnerilenUrunler)) {
                                        products = r.OnerilenUrunler;
                                      }
                                    } catch (e) {
                                      console.error("Parse error:", e);
                                    }
                                    products.sort((a: any, b: any) => ((b.ort || 0) * 0.75) - ((a.ort || 0) * 0.75))
                                    if (products.length > 0) {
                                      const firstProduct = products[0];
                                      const otherCount = products.length - 1;
                                      return (
                                        <div
                                          style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                                          onClick={(e) => handleCategoryClick(e, r.KategoriAdi, r.OnerilenUrunler, r.HedefMusteriSayisi, r.OnerilenMinTutar, r.PotansiyelCiro)}
                                        >
                                          <span style={{ borderBottom: '1px dashed #94a3b8', transition: 'border-color 0.2s' }}>{firstProduct.ad || r.UrunAdi}</span>
                                          {otherCount > 0 && (
                                            <span style={{ fontSize: '0.65rem', background: '#e0e7ff', color: '#4f46e5', padding: '2px 6px', borderRadius: '12px', fontWeight: 700 }}>
                                              +{otherCount} Öneri
                                            </span>
                                          )}
                                        </div>
                                      )
                                    }
                                    return (
                                      <div
                                        style={{ fontSize: '0.925rem', fontWeight: 600, color: '#334155', cursor: 'pointer' }}
                                        onClick={(e) => handleCategoryClick(e, r.KategoriAdi)}
                                      >
                                        {r.UrunAdi || '-'}
                                      </div>
                                    )
                                  })()}
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Hedef Kitle</div>
                                  <div style={{ fontSize: '0.925rem', fontWeight: 700, color: '#3b82f6' }}>{(r.HedefMusteriSayisi || 0).toLocaleString('tr-TR')}</div>
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Potansiyel Ciro</div>
                                  <div style={{ fontSize: '0.925rem', fontWeight: 700, color: '#10b981' }}>
                                    ₺{Math.round(r.PotansiyelCiro || 0).toLocaleString('tr-TR')}
                                  </div>
                                </div>
                                {r.KampanyaTipi === 'Cross-Sell' && r.Lift !== undefined && r.Lift > 0 && (
                                  <div style={{ flex: '1', textAlign: 'right', minWidth: '120px' }}>
                                    <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Lift / Güven / Fiş</div>
                                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>
                                      {r.Lift.toFixed(2)} / %{((r.Guven || 0) * 100).toFixed(1).replace('.0', '')} / {r.FisSayisi || 0}
                                    </div>
                                  </div>
                                )}
                                <div style={{ display: 'flex', gap: '6px' }}>
                                  <button
                                    style={{ padding: '6px 12px', background: isOneriSelected ? '#334155' : '#f8fafc', color: isOneriSelected ? 'white' : '#64748b', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer' }}
                                  >
                                    {isOneriSelected ? 'Özeti Kapat' : 'AI Özet'}
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveCampaignForVariants(r);
                                      setVariantProducerOpened(true);
                                    }}
                                    style={{ padding: '6px 12px', background: 'white', color: '#8b5cf6', border: '1px solid #8b5cf6', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer' }}
                                  >
                                    Varyant Üret
                                  </button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); handleAddToBasket(r.OneriID); }}
                                    style={{ padding: '6px 12px', background: locallyApprovedIds.has(r.OneriID) ? '#d1fae5' : 'white', color: locallyApprovedIds.has(r.OneriID) ? '#065f46' : '#6366f1', border: `1px solid ${locallyApprovedIds.has(r.OneriID) ? '#6ee7b7' : '#6366f1'}`, borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: locallyApprovedIds.has(r.OneriID) ? 'default' : 'pointer' }}
                                    disabled={locallyApprovedIds.has(r.OneriID)}
                                  >{locallyApprovedIds.has(r.OneriID) ? '✓ Sepette' : 'Dışa Aktar'}</button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); handleApproveToCalendar(r); }}
                                    style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '132px', padding: '6px 12px', background: '#10b981', color: 'white', border: 'none', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', boxSizing: 'border-box' }}
                                  >Onayla</button>
                                </div>
                              </div>

                              {/* AI Summary embedded */}
                              {isOneriSelected && (
                                <div style={{ marginTop: '14px', borderRadius: '12px', overflow: 'hidden', border: '1px solid #e0e7ff', boxShadow: '0 2px 8px rgba(99,102,241,0.07)' }}>
                                  <div style={{ background: 'linear-gradient(90deg, #6366f1 0%, #818cf8 100%)', padding: '10px 18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'white', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Kampanya Analizi</span>
                                  </div>
                                  <div style={{ padding: '20px', background: 'white' }}>
                                    {loadingAi ? (
                                      <div style={{ color: '#6366f1', fontWeight: 600, fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#6366f1', opacity: 0.6, animation: 'pulse 1s infinite' }} />
                                        Analiz hazırlanıyor...
                                      </div>
                                    ) : (
                                      <div style={{ fontSize: '0.875rem', color: '#1e293b', lineHeight: 1.75 }}>
                                        <ReactMarkdown
                                          remarkPlugins={[remarkGfm]}
                                          components={{
                                            h3: ({ children }) => (
                                              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#312e81', marginBottom: '16px', paddingBottom: '10px', borderBottom: '2px solid #e0e7ff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                {children}
                                              </div>
                                            ),
                                            strong: ({ children }) => <strong style={{ color: '#1e293b', fontWeight: 700 }}>{children}</strong>,
                                            p: ({ children }) => <p style={{ margin: '0 0 12px 0', color: '#334155' }}>{children}</p>,
                                            ul: ({ children }) => <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px' }}>{children}</ul>,
                                            li: ({ children }) => (
                                              <li style={{ marginBottom: '6px', color: '#334155', paddingLeft: '4px' }}>{children}</li>
                                            ),
                                            table: ({ children }) => (
                                              <div style={{ overflowX: 'auto', margin: '16px 0', borderRadius: '10px', border: '1px solid #e0e7ff', boxShadow: '0 1px 4px rgba(99,102,241,0.06)' }}>
                                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>{children}</table>
                                              </div>
                                            ),
                                            thead: ({ children }) => <thead style={{ background: 'linear-gradient(90deg, #eef2ff 0%, #e0e7ff 100%)' }}>{children}</thead>,
                                            th: ({ children }) => (
                                              <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: '#4338ca', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{children}</th>
                                            ),
                                            tbody: ({ children }) => <tbody>{children}</tbody>,
                                            tr: ({ children, ...props }: any) => {
                                              const extractText = (n: any): string => {
                                                if (!n) return ''
                                                if (typeof n === 'string') return n
                                                if (typeof n === 'number') return String(n)
                                                if (Array.isArray(n)) return n.map(extractText).join('')
                                                if (n?.props?.children !== undefined) return extractText(n.props.children)
                                                return ''
                                              }
                                              const cells = Array.isArray(children) ? children.filter(Boolean) : [children]
                                              const firstText = extractText(cells[0])
                                              let bg = 'transparent'
                                              let borderLeft = 'none'
                                              if (firstText.includes('kategorisi toplam') || firstText.includes('ulaşılacak kitle') || firstText.includes('almamış hedef kitle')) {
                                                bg = '#f3e8ff'; borderLeft = '4px solid #a855f7'
                                              } else if (firstText.includes('fiş') || firstText.includes('birlikte alan')) {
                                                bg = '#eff6ff'; borderLeft = '4px solid #3b82f6'
                                              } else if (firstText.includes('Mevcut birlikte')) {
                                                bg = '#fff7ed'; borderLeft = '4px solid #fb923c'
                                              } else if (firstText.startsWith('↳')) {
                                                bg = '#fff7ed'; borderLeft = '4px solid #fed7aa'
                                              } else if (firstText.includes('önerilen ürün potansiyel') || firstText.includes('önerilen ürün tahmini ROI')) {
                                                bg = '#f0fdf4'; borderLeft = '4px solid #22c55e'
                                              } else if (firstText.includes('Potansiyel birlikte')) {
                                                bg = '#dcfce7'; borderLeft = '4px solid #16a34a'
                                              } else if (firstText.includes('Birlikte tahmini ROI')) {
                                                bg = '#dcfce7'; borderLeft = '4px solid #16a34a'
                                              }
                                              return <tr style={{ borderTop: '1px solid #e0e7ff', background: bg, borderLeft }} {...(props as any)}>{children}</tr>
                                            },
                                            td: ({ children }) => {
                                              const text = children?.toString?.() || ''
                                              const isSubRow = text.startsWith('↳')
                                              return (
                                                <td style={{
                                                  padding: isSubRow ? '7px 16px 7px 28px' : '10px 16px',
                                                  color: isSubRow ? '#64748b' : '#1e293b',
                                                  fontSize: isSubRow ? '0.82rem' : undefined,
                                                  verticalAlign: 'middle'
                                                }}>{children}</td>
                                              )
                                            },
                                          }}
                                        >{aiSummary}</ReactMarkdown>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                        {hasMoreItems && (
                          <div style={{ textAlign: 'center', paddingTop: '8px' }}>
                            <button
                              onClick={(e) => { e.stopPropagation(); loadMoreCategoryItems(key) }}
                              disabled={isLoading}
                              style={{
                                padding: '10px 28px',
                                background: isLoading ? '#e2e8f0' : 'white',
                                border: '1px solid #6366f1',
                                color: isLoading ? '#94a3b8' : '#6366f1',
                                borderRadius: '8px',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                cursor: isLoading ? 'not-allowed' : 'pointer',
                              }}
                            >
                              {isLoading ? 'Yükleniyor...' : `Daha Fazla Yükle (${(catState?.total || 0) - items.length} kaldı)`}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </>)
          ) : (
            displayGroups.map((group: any) => {
              const isSelected = selectedGroupKey === group.key;
              return (
                <div key={group.key} style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                  {/* SEGMENT ANA KART */}
                  <div
                    onClick={() => setSelectedGroupKey(isSelected ? null : group.key)}
                    style={{
                      padding: '20px 24px',
                      background: '#ffffff',
                      borderRadius: isSelected ? '12px 12px 0 0' : '12px',
                      border: `1px solid ${isSelected ? '#e2e8f0' : '#f1f5f9'}`,
                      boxShadow: isSelected ? '0 4px 12px rgba(0,0,0,0.03)' : '0 1px 3px rgba(0,0,0,0.02)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      position: 'relative'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{
                          width: '44px',
                          height: '44px',
                          borderRadius: '10px',
                          background: isSelected ? '#334155' : '#f8fafc',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '1.3rem',
                          color: isSelected ? 'white' : '#64748b',
                          transition: 'all 0.3s'
                        }}>
                          {group.type === 'Cross-Sell' ? <IconArrowsCross size={22} stroke={1.8} /> : group.type === 'Loyalty' ? <IconHeart size={22} stroke={1.8} /> : <IconHeartBroken size={22} stroke={1.8} />}
                        </div>
                        <div>
                          <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.025em', marginBottom: '2px' }}>
                            {group.type === 'Cross-Sell' ? 'Kategori Grubu' : 'Müşteri Segmenti'}
                          </div>
                          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#334155', lineHeight: 1.3 }}>
                            {group.key}
                          </h3>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '24px', textAlign: 'right', alignItems: 'center' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Hedef Kitle</div>
                          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#3b82f6' }}>{(group.totalHedef || 0).toLocaleString('tr-TR')}</div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Potansiyel Ciro</div>
                          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#10b981' }}>₺{Math.round(group.totalCiro || 0).toLocaleString('tr-TR')}</div>
                        </div>
                        {group.type === 'Cross-Sell' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                            <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Top. Fiş</div>
                            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#6366f1' }}>{group.totalFis?.toLocaleString('tr-TR')}</div>
                          </div>
                        )}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: '40px' }}>
                          <div style={{
                            padding: '4px 12px',
                            borderRadius: '20px',
                            background: isSelected ? '#6366f115' : '#f1f5f9',
                            color: '#6366f1',
                            fontSize: '0.75rem',
                            fontWeight: 700
                          }}>
                            {group.items.length} Öneri
                          </div>
                        </div>
                        <div style={{ fontSize: '1.2rem', color: '#94a3b8' }}>
                          {isSelected ? <IconChevronUp size={18} stroke={2} /> : <IconChevronDown size={18} stroke={2} />}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* DETAY LİSTESİ */}
                  {isSelected && (
                    <div style={{
                      background: '#f8fafc',
                      borderRadius: '0 0 16px 16px',
                      border: '1px solid #6366f1',
                      borderTop: 'none',
                      padding: '20px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                      animation: 'slideDown 0.3s ease-out'
                    }}>
                      {(() => {
                        // RFM/Win-Back: tüm ürünleri TEK kart içinde göster (Cross-Sell mantığı)
                        if (group.type !== 'Cross-Sell') {
                          const allItems = group.items;
                          const repItem = allItems[0];
                          const allIds = allItems.map((i: any) => i.OneriID);
                          const isOneriSelected = allIds.some((id: number) => selectedOneriId === id);
                          const totalCiro = allItems.reduce((s: number, i: any) => s + (i.PotansiyelCiro || 0), 0);
                          return [(
                            <div
                              key="segment-card"
                              onClick={() => {
                                if (isOneriSelected) setSelectedOneriId(null)
                                else {
                                  setSelectedOneriId(repItem.OneriID)
                                  loadAiSummary(repItem.OneriID)
                                }
                              }}
                              style={{
                                background: 'white',
                                borderRadius: '10px',
                                border: `1px solid ${isOneriSelected ? '#6366f1' : '#f1f5f9'}`,
                                padding: '14px 16px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                position: 'relative'
                              }}
                              onMouseEnter={(e) => {
                                if (!isOneriSelected) {
                                  e.currentTarget.style.borderColor = '#cbd5e1';
                                  e.currentTarget.style.background = '#fafbfc';
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (!isOneriSelected) {
                                  e.currentTarget.style.borderColor = '#f1f5f9';
                                  e.currentTarget.style.background = 'white';
                                }
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <span style={{ padding: '2px 8px', borderRadius: '4px', background: getPriorityColor(repItem.OncelikSeviye) + '10', color: getPriorityColor(repItem.OncelikSeviye), fontSize: '0.6rem', fontWeight: 700 }}>
                                    {repItem.OncelikSeviye === 1 ? <><IconAlertTriangle size={12} stroke={2} style={{ verticalAlign: 'middle', marginRight: 2 }} /> ACİL</> : `PRIORITY ${repItem.OncelikSeviye}`}
                                  </span>
                                </div>
                                <span style={{ fontSize: '0.65rem', color: '#94a3b8' }}>{repItem.OlusturmaTarihi}</span>
                              </div>

                              {/* Ürün tablosu — her satır bir öneri */}
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                                {allItems.map((item: any, idx: number) => (
                                  <div key={item.OneriID} style={{
                                    display: 'flex', alignItems: 'center', gap: '12px',
                                    padding: '8px 12px', borderRadius: '8px',
                                    background: idx % 2 === 0 ? '#f8fafc' : 'white',
                                    border: '1px solid #f1f5f9'
                                  }}>
                                    <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#6366f115', color: '#6366f1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.65rem', fontWeight: 700, flexShrink: 0 }}>
                                      {idx + 1}
                                    </div>
                                    <div style={{ flex: '0 0 140px', minWidth: 0 }}>
                                      <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Kategori</div>
                                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.KategoriAdi || '-'}</div>
                                    </div>
                                    <div style={{ color: '#e2e8f0', flexShrink: 0 }}>›</div>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                      <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Önerilen Ürün</div>
                                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.UrunAdi || '-'}</div>
                                    </div>
                                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                      <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Pot. Ciro</div>
                                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#10b981' }}>₺{Math.round(item.PotansiyelCiro || 0).toLocaleString('tr-TR')}</div>
                                    </div>
                                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                      <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>İndirim</div>
                                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f59e0b' }}>%{item.OnerilenIndirim || 0}</div>
                                    </div>
                                  </div>
                                ))}
                              </div>

                              {/* Alt satır: toplam metrikler + butonlar */}
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '8px', borderTop: '1px solid #f1f5f9' }}>
                                <div style={{ display: 'flex', gap: '24px' }}>
                                  <div>
                                    <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Hedef Kitle</div>
                                    <div style={{ fontSize: '0.925rem', fontWeight: 700, color: '#3b82f6' }}>{(repItem.HedefMusteriSayisi || 0).toLocaleString('tr-TR')}</div>
                                  </div>
                                  <div>
                                    <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Toplam Pot. Ciro</div>
                                    <div style={{ fontSize: '0.925rem', fontWeight: 700, color: '#10b981' }}>₺{Math.round(totalCiro).toLocaleString('tr-TR')}</div>
                                  </div>
                                </div>
                                <div style={{ display: 'flex', gap: '6px' }}>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setAiSummary('');
                                      setSelectedOneriId(isOneriSelected ? null : repItem.OneriID);
                                      if (!isOneriSelected) loadAiSummary(repItem.OneriID);
                                    }}
                                    style={{ padding: '6px 12px', background: isOneriSelected ? '#334155' : '#f8fafc', color: isOneriSelected ? 'white' : '#64748b', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer' }}
                                  >
                                    {isOneriSelected ? 'Özeti Kapat' : 'AI Özet'}
                                  </button>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveCampaignForVariants(repItem);
                                      setVariantProducerOpened(true);
                                    }}
                                    style={{ padding: '6px 12px', background: '#f5f3ff', color: '#7c3aed', border: '1px solid #ddd6fe', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                                  >
                                    <IconSparkles size={12} /> Varyantlar
                                  </button>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveCampaignForSchedule(repItem);
                                      setSchedulerOpened(true);
                                    }}
                                    style={{ padding: '6px 12px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                                    title="Bu öneriyi takvime ekle"
                                  >
                                    <IconCalendar size={12} /> Planla
                                  </button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); allIds.forEach((id: number) => handleAddToBasket(id)); }}
                                    style={{ padding: '6px 12px', background: allIds.every((id: number) => locallyApprovedIds.has(id)) ? '#d1fae5' : 'white', color: allIds.every((id: number) => locallyApprovedIds.has(id)) ? '#065f46' : '#6366f1', border: `1px solid ${allIds.every((id: number) => locallyApprovedIds.has(id)) ? '#6ee7b7' : '#6366f1'}`, borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: allIds.every((id: number) => locallyApprovedIds.has(id)) ? 'default' : 'pointer' }}
                                    disabled={allIds.every((id: number) => locallyApprovedIds.has(id))}
                                  >{allIds.every((id: number) => locallyApprovedIds.has(id)) ? '✓ Sepette' : 'Dışa Aktar'}</button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); allItems.forEach((item: any) => handleApproveToCalendar(item)); }}
                                    style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '132px', padding: '6px 12px', background: '#10b981', color: 'white', border: 'none', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', boxSizing: 'border-box' }}
                                  >Onayla</button>
                                </div>
                              </div>

                              {/* AI Summary embedded */}
                              {isOneriSelected && (
                                <div style={{ marginTop: '14px', borderRadius: '12px', overflow: 'hidden', border: '1px solid #e0e7ff', boxShadow: '0 2px 8px rgba(99,102,241,0.07)' }}>
                                  <div style={{ background: 'linear-gradient(90deg, #6366f1 0%, #818cf8 100%)', padding: '10px 18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'white', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Kampanya Analizi</span>
                                  </div>
                                  <div style={{ padding: '20px', background: 'white' }}>
                                    {loadingAi ? (
                                      <div style={{ color: '#6366f1', fontWeight: 600, fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#6366f1', opacity: 0.6, animation: 'pulse 1s infinite' }} />
                                        Analiz hazırlanıyor...
                                        </div>
                                      ) : (
                                    <div style={{ fontSize: '0.875rem', color: '#1e293b', lineHeight: 1.75 }}>
                                      <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                          h3: ({ children }) => (
                                            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#312e81', marginBottom: '16px', paddingBottom: '10px', borderBottom: '2px solid #e0e7ff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                              {children}
                                            </div>
                                          ),
                                          strong: ({ children }) => <strong style={{ color: '#1e293b', fontWeight: 700 }}>{children}</strong>,
                                          p: ({ children }) => <p style={{ margin: '0 0 12px 0', color: '#334155' }}>{children}</p>,
                                          ul: ({ children }) => <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px' }}>{children}</ul>,
                                          li: ({ children }) => (
                                            <li style={{ marginBottom: '6px', color: '#334155', paddingLeft: '4px' }}>{children}</li>
                                          ),
                                          table: ({ children }) => (
                                            <div style={{ overflowX: 'auto', margin: '16px 0', borderRadius: '10px', border: '1px solid #e0e7ff', boxShadow: '0 1px 4px rgba(99,102,241,0.06)' }}>
                                              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>{children}</table>
                                            </div>
                                          ),
                                          thead: ({ children }) => <thead style={{ background: 'linear-gradient(90deg, #eef2ff 0%, #e0e7ff 100%)' }}>{children}</thead>,
                                          th: ({ children }) => (
                                            <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: '#4338ca', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', whiteSpace: 'nowrap' }}>{children}</th>
                                          ),
                                          tbody: ({ children }) => <tbody>{children}</tbody>,
                                          tr: ({ children, ...props }: any) => {
                                            const extractText = (n: any): string => {
                                              if (!n) return ''
                                              if (typeof n === 'string') return n
                                              if (typeof n === 'number') return String(n)
                                              if (Array.isArray(n)) return n.map(extractText).join('')
                                              if (n?.props?.children !== undefined) return extractText(n.props.children)
                                              return ''
                                            }
                                            const cells = Array.isArray(children) ? children.filter(Boolean) : [children]
                                            const firstText = extractText(cells[0])
                                            let bg = 'transparent'
                                            let borderLeft = 'none'
                                            if (firstText.includes('kategorisi toplam') || firstText.includes('ulaşılacak kitle') || firstText.includes('almamış hedef kitle')) {
                                              bg = '#f3e8ff'; borderLeft = '4px solid #a855f7'
                                            } else if (firstText.includes('fiş') || firstText.includes('birlikte alan')) {
                                              bg = '#eff6ff'; borderLeft = '4px solid #3b82f6'
                                            } else if (firstText.includes('Mevcut birlikte')) {
                                              bg = '#fff7ed'; borderLeft = '4px solid #fb923c'
                                            } else if (firstText.startsWith('↳')) {
                                              bg = '#fff7ed'; borderLeft = '4px solid #fed7aa'
                                            } else if (firstText.includes('önerilen ürün potansiyel') || firstText.includes('önerilen ürün tahmini ROI')) {
                                              bg = '#f0fdf4'; borderLeft = '4px solid #22c55e'
                                            } else if (firstText.includes('Potansiyel birlikte')) {
                                              bg = '#dcfce7'; borderLeft = '4px solid #16a34a'
                                            } else if (firstText.includes('Birlikte tahmini ROI')) {
                                              bg = '#dcfce7'; borderLeft = '4px solid #16a34a'
                                            }
                                            return <tr style={{ borderTop: '1px solid #e0e7ff', background: bg, borderLeft }} {...(props as any)}>{children}</tr>
                                          },
                                          td: ({ children }) => {
                                            const text = children?.toString?.() || ''
                                            const isSubRow = text.startsWith('↳')
                                            return (
                                              <td style={{
                                                padding: isSubRow ? '7px 16px 7px 28px' : '10px 16px',
                                                color: isSubRow ? '#64748b' : '#1e293b',
                                                fontSize: isSubRow ? '0.82rem' : undefined,
                                                verticalAlign: 'middle'
                                              }}>{children}</td>
                                            )
                                          },
                                        }}
                                      >{aiSummary}</ReactMarkdown>
                                    </div>
                                  )}
                                </div>
                              </div>
                              )}
                            </div>
                          )];
                        }
                        // Cross-Sell: her item ayrı kart (mevcut davranış)
                        return group.items.map((r: any) => {
                          const isOneriSelected = selectedOneriId === r.OneriID;
                          return (
                            <div
                              key={r.OneriID}
                              onClick={() => {
                                if (isOneriSelected) setSelectedOneriId(null)
                                else {
                                  setSelectedOneriId(r.OneriID)
                                  loadAiSummary(r.OneriID)
                                }
                              }}
                              style={{
                                background: 'white',
                                borderRadius: '10px',
                                border: `1px solid ${isOneriSelected ? '#e2e8f0' : '#f1f5f9'}`,
                                padding: '14px 16px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                position: 'relative'
                              }}
                              onMouseEnter={(e) => {
                                if (!isOneriSelected) {
                                  e.currentTarget.style.borderColor = '#cbd5e1';
                                  e.currentTarget.style.background = '#fafbfc';
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (!isOneriSelected) {
                                  e.currentTarget.style.borderColor = '#f1f5f9';
                                  e.currentTarget.style.background = 'white';
                                }
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <span style={{ padding: '2px 8px', borderRadius: '4px', background: getPriorityColor(r.OncelikSeviye) + '10', color: getPriorityColor(r.OncelikSeviye), fontSize: '0.6rem', fontWeight: 700 }}>
                                    {r.OncelikSeviye === 1 ? <><IconAlertTriangle size={12} stroke={2} style={{ verticalAlign: 'middle', marginRight: 2 }} /> ACİL</> : `PRIORITY ${r.OncelikSeviye}`}
                                  </span>
                                </div>
                                <span style={{ fontSize: '0.65rem', color: '#94a3b8' }}>{r.OlusturmaTarihi}</span>
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                <div style={{ flex: '0 0 160px' }}>
                                  {r.KaynakKategoriAd && r.KampanyaTipi === 'Cross-Sell' && (
                                    <div style={{ marginBottom: '4px', fontSize: '0.7rem', color: '#4f46e5', fontWeight: 700, background: '#eef2ff', padding: '2px 8px', borderRadius: '4px', display: 'inline-block' }}>
                                      {r.KaynakKategoriAd} alanlara öneriliyor
                                    </div>
                                  )}
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Kategori</div>
                                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#64748b' }}>{r.KategoriAdi}</div>
                                </div>
                                <div style={{ color: '#e2e8f0' }}>›</div>
                                <div style={{ flex: '1.2' }}>
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Önerilen Ürün(ler)</div>
                                  {(() => {
                                    let products: any[] = [];
                                    try {
                                      if (typeof r.OnerilenUrunler === 'string') products = JSON.parse(r.OnerilenUrunler);
                                      else if (Array.isArray(r.OnerilenUrunler)) products = r.OnerilenUrunler;
                                    } catch (e) { console.error("Parse error:", e); }
                                    products.sort((a: any, b: any) => ((b.ort || 0) * 0.75) - ((a.ort || 0) * 0.75))
                                    if (products.length > 0) {
                                      const firstProduct = products[0];
                                      const otherCount = products.length - 1;
                                      return (
                                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                                          onClick={(e) => handleCategoryClick(e, r.KategoriAdi, r.OnerilenUrunler, r.HedefMusteriSayisi, r.OnerilenMinTutar, r.PotansiyelCiro)}>
                                          <span style={{ borderBottom: '1px dashed #94a3b8' }}>{firstProduct.ad || r.UrunAdi}</span>
                                          {otherCount > 0 && <span style={{ fontSize: '0.65rem', background: '#e0e7ff', color: '#4f46e5', padding: '2px 6px', borderRadius: '12px', fontWeight: 700 }}>+{otherCount} Öneri</span>}
                                        </div>
                                      )
                                    }
                                    return <div style={{ fontSize: '0.925rem', fontWeight: 600, color: '#334155', cursor: 'pointer' }} onClick={(e) => handleCategoryClick(e, r.KategoriAdi)}>{r.UrunAdi || '-'}</div>
                                  })()}
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Hedef Kitle</div>
                                  <div style={{ fontSize: '0.925rem', fontWeight: 700, color: '#3b82f6' }}>{(r.HedefMusteriSayisi || 0).toLocaleString('tr-TR')}</div>
                                </div>
                                <div style={{ flex: 1, textAlign: 'right' }}>
                                  <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Potansiyel Ciro</div>
                                  <div style={{ fontSize: '0.925rem', fontWeight: 700, color: '#10b981' }}>₺{Math.round(r.PotansiyelCiro || 0).toLocaleString('tr-TR')}</div>
                                </div>
                                {r.Lift !== undefined && r.Lift > 0 && (
                                  <div style={{ flex: '1', textAlign: 'right', minWidth: '120px' }}>
                                    <div style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Lift / Güven / Fiş</div>
                                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>{r.Lift.toFixed(2)} / %{((r.Guven || 0) * 100).toFixed(1).replace('.0', '')} / {r.FisSayisi || 0}</div>
                                  </div>
                                )}
                                <div style={{ display: 'flex', gap: '6px' }}>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setAiSummary('');
                                      setSelectedOneriId(isOneriSelected ? null : r.OneriID);
                                      if (!isOneriSelected) loadAiSummary(r.OneriID);
                                    }}
                                    style={{ padding: '6px 12px', background: isOneriSelected ? '#334155' : '#f8fafc', color: isOneriSelected ? 'white' : '#64748b', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer' }}
                                  >
                                    {isOneriSelected ? 'Özeti Kapat' : 'AI Özet'}
                                  </button>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveCampaignForVariants(r);
                                      setVariantProducerOpened(true);
                                    }}
                                    style={{ padding: '6px 12px', background: '#f5f3ff', color: '#7c3aed', border: '1px solid #ddd6fe', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                                  >
                                    <IconSparkles size={12} /> Varyantlar
                                  </button>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setActiveCampaignForSchedule(r);
                                      setSchedulerOpened(true);
                                    }}
                                    style={{ padding: '6px 12px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                                    title="Bu öneriyi takvime ekle"
                                  >
                                    <IconCalendar size={12} /> Planla
                                  </button>
                                  <button onClick={(e) => { e.stopPropagation(); handleAddToBasket(r.OneriID); }} style={{ padding: '6px 12px', background: locallyApprovedIds.has(r.OneriID) ? '#d1fae5' : 'white', color: locallyApprovedIds.has(r.OneriID) ? '#065f46' : '#6366f1', border: `1px solid ${locallyApprovedIds.has(r.OneriID) ? '#6ee7b7' : '#6366f1'}`, borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: locallyApprovedIds.has(r.OneriID) ? 'default' : 'pointer' }} disabled={locallyApprovedIds.has(r.OneriID)}>{locallyApprovedIds.has(r.OneriID) ? '✓ Sepette' : 'Dışa Aktar'}</button>
                                  <button onClick={(e) => { e.stopPropagation(); handleApproveToCalendar(r); }} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '132px', padding: '6px 12px', background: '#10b981', color: 'white', border: 'none', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', boxSizing: 'border-box' }}>Onayla</button>
                                </div>
                              </div>
                              {isOneriSelected && (
                                <div style={{ marginTop: '14px', borderRadius: '12px', overflow: 'hidden', border: '1px solid #e0e7ff', boxShadow: '0 2px 8px rgba(99,102,241,0.07)' }}>
                                  <div style={{ background: 'linear-gradient(90deg, #6366f1 0%, #818cf8 100%)', padding: '10px 18px' }}>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'white', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Kampanya Analizi</span>
                                  </div>
                                  <div style={{ padding: '20px', background: 'white' }}>
                                    {loadingAi ? (
                                      <div style={{ color: '#6366f1', fontWeight: 600, fontSize: '0.875rem' }}>Analiz hazırlanıyor...</div>
                                    ) : (
                                      <div style={{ fontSize: '0.875rem', color: '#1e293b', lineHeight: 1.75 }}>
                                        <div style={{ marginBottom: '16px', padding: '8px 12px', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fde68a', fontSize: '0.75rem', color: '#b45309', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                            <IconAlertTriangle size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                                            <div>
                                                <b>Önemli Not:</b> Bu alan şu anda istatistiksel verilere dayanan otomatik şablonlarla oluşturulmuştur (Gerçek LLM değildir). Yapay zeka destekli detaylı kampanya pazar analizi için aşağıdaki butonu kullanabilirsiniz.
                                            </div>
                                        </div>
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{aiSummary}</ReactMarkdown>
                                        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                                            <AISummaryButton contextType="campaign_profile" contextId={r.OneriID?.toString()} variant="light" label="Gerçek AI Analizi" />
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        });
                      })()}
                    </div>
                  )}
                </div>
              )
            })
          )}

          <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '0.85rem', color: '#94a3b8' }}>
            {activeTab === 'Cross-Sell' 
              ? `${sourceCategories.length} / ${categoriesTotalCount} grup yüklendi`
              : `${recommendations.length} / ${totalCount} öneri yüklendi`}
          </div>

          {activeTab !== 'Cross-Sell' && hasMore && (
            <div style={{ marginTop: '12px', textAlign: 'center', paddingBottom: '40px' }}>
              <button
                onClick={() => loadRecommendations(false)}
                disabled={loadingMore}
                style={{
                  padding: '12px 32px',
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  cursor: loadingMore ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  color: '#6366f1',
                  transition: 'all 0.2s',
                  fontSize: '0.95rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                }}
                onMouseEnter={(e) => {
                  if (!loadingMore) {
                    e.currentTarget.style.background = '#f8fafc';
                    e.currentTarget.style.borderColor = '#6366f1';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!loadingMore) {
                    e.currentTarget.style.background = 'white';
                    e.currentTarget.style.borderColor = '#e2e8f0';
                  }
                }}
              >
                {loadingMore ? 'Yükleniyor...' : ' Daha Fazla Öneri Yükle'}
              </button>
            </div>
          )}

          {activeTab === 'Cross-Sell' && categoriesHasMore && (
            <div style={{ marginTop: '12px', textAlign: 'center', paddingBottom: '40px' }}>
              <button
                onClick={() => loadSourceCategories(false)}
                disabled={categoriesLoading}
                style={{
                  padding: '12px 32px',
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  cursor: categoriesLoading ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  color: '#6366f1',
                  transition: 'all 0.2s',
                  fontSize: '0.95rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                }}
                onMouseEnter={(e) => {
                  if (!categoriesLoading) {
                    e.currentTarget.style.background = '#f8fafc';
                    e.currentTarget.style.borderColor = '#6366f1';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!categoriesLoading) {
                    e.currentTarget.style.background = 'white';
                    e.currentTarget.style.borderColor = '#e2e8f0';
                  }
                }}
              >
                {categoriesLoading ? 'Yükleniyor...' : ' Daha Fazla Grup Yükle'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Alternative Products Modal */}
      {altModalOpen && (
        <div 
          style={{ 
            position: 'fixed', 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            zIndex: 1000, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            padding: '20px'
          }}
        >
          {/* Backdrop */}
          <div 
            style={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              right: 0, 
              bottom: 0, 
              background: 'rgba(15, 23, 42, 0.6)',
              backdropFilter: 'blur(4px)'
            }}
            onClick={() => setAltModalOpen(false)}
          />
          
          {/* Content */}
          <div 
            style={{ 
              position: 'relative',
              width: '100%',
              maxWidth: '600px',
              background: 'white',
              borderRadius: '16px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
              overflow: 'hidden',
              animation: 'slideDown 0.3s ease-out'
            }}
          >
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1e293b' }}>Alternatif Ürün Önerileri</h3>
                <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#64748b' }}>{altCategory} kategorisindeki önerilen {altProducts.length} ürün</p>
              </div>
              <button 
                onClick={() => setAltModalOpen(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.25rem' }}
              >✕</button>
            </div>

            <div style={{ padding: '24px', maxHeight: '70vh', overflowY: 'auto' }}>
              {altLoading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>Ürünler yükleniyor...</div>
              ) : altProducts.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {altProducts.map((p, idx) => (
                    <div
                      key={p.id ?? idx}
                      onClick={() => {
                        if (p.id) {
                          setAltModalOpen(false)
                          navigate(`/urunler?productId=${p.id}`)
                        }
                      }}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '12px 16px',
                        background: '#fff',
                        borderRadius: '10px',
                        border: '1px solid #f1f5f9',
                        transition: 'all 0.2s',
                        cursor: p.id ? 'pointer' : 'default'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#6366f1';
                        e.currentTarget.style.background = '#fcfdff';
                        e.currentTarget.style.transform = 'translateX(5px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#f1f5f9';
                        e.currentTarget.style.background = '#fff';
                        e.currentTarget.style.transform = 'translateX(0)';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '28px', height: '28px', background: '#f1f5f9', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, color: '#64748b' }}>
                          {idx + 1}
                        </div>
                        <div>
                          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#334155' }}>{p.ad}</div>
                          {(p.customer_count != null || p.receipt_count != null || p.quantity != null) && (
                            <div style={{ display: 'flex', gap: '8px', marginTop: '2px' }}>
                              {p.customer_count != null && <div style={{ fontSize: '0.7rem', color: '#64748b', background: '#f1f5f9', padding: '1px 6px', borderRadius: '4px' }}><span style={{ fontWeight: 700, color: '#444' }}>{p.customer_count}</span> Müşteri</div>}
                              {p.receipt_count != null && <div style={{ fontSize: '0.7rem', color: '#64748b', background: '#f1f5f9', padding: '1px 6px', borderRadius: '4px' }}><span style={{ fontWeight: 700, color: '#444' }}>{p.receipt_count}</span> Fiş</div>}
                              {p.quantity != null && <div style={{ fontSize: '0.7rem', color: '#64748b', background: '#f1f5f9', padding: '1px 6px', borderRadius: '4px' }}><span style={{ fontWeight: 700, color: '#444' }}>{p.quantity}</span> Adet</div>}
                            </div>
                          )}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', minWidth: '160px' }}>
                        {p.potansiyel_ciro != null && (
                          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#10b981' }}>
                            ₺{p.potansiyel_ciro?.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </div>
                        )}
                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>
                          {p.normal_fiyat != null && (
                            <span style={{ textDecoration: 'line-through', color: '#94a3b8', marginRight: '4px' }}>
                              ₺{p.normal_fiyat?.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                          )}
                          {p.kampanya_fiyat != null && (
                            <span style={{ color: '#6366f1', fontWeight: 600 }}>
                              ₺{p.kampanya_fiyat?.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (%25↓)
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>Bu kategoriye ait ürün bulunamadı.</div>
              )}
            </div>

            <div style={{ padding: '16px 24px', background: '#f8fafc', borderTop: '1px solid #f1f5f9', textAlign: 'right' }}>
              <button 
                onClick={() => setAltModalOpen(false)}
                style={{ padding: '8px 20px', background: '#6366f1', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}
              >Anladım</button>
            </div>
          </div>
        </div>
      )}
      {/* KAMPANYA SEPETİ / EXPORT OVERLAY */}
      {approvedTotalCount > 0 && (
        <div style={{
          position: 'fixed',
          bottom: '30px',
          right: '30px',
          zIndex: 1000,
          background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
          padding: '16px 24px',
          borderRadius: '16px',
          boxShadow: '0 10px 25px rgba(79, 70, 229, 0.4)',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          cursor: 'pointer',
          animation: 'slideDown 0.5s ease-out reverse'
        }}
        onClick={() => { setExportModalOpen(true); loadApprovedCampaigns(); }}
        >
          <div style={{ position: 'relative' }}>
             <span style={{ fontSize: '1.5rem' }}>🛒</span>
             <span style={{ 
               position: 'absolute', 
               top: '-8px', 
               right: '-8px', 
               background: '#ef4444', 
               color: 'white', 
               fontSize: '0.65rem', 
               padding: '2px 6px', 
               borderRadius: '10px',
               fontWeight: 900,
               border: '2px solid white'
             }}>
               {approvedTotalCount}
             </span>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>Kampanya Sepeti</div>
            <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>{approvedTotalCount} kampanya dışa aktarılmaya hazır</div>
          </div>
          <div style={{ 
            background: 'rgba(255,255,255,0.2)', 
            padding: '6px 12px', 
            borderRadius: '8px', 
            fontSize: '0.8rem', 
            fontWeight: 600 
          }}>
            İncele & Aktar
          </div>
        </div>
      )}

      {/* EXPORT MODAL */}
      {exportModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 2000,
          padding: '20px'
        }}>
          <div style={{
            background: 'white',
            borderRadius: '20px',
            width: '100%',
            maxWidth: '600px',
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            animation: 'slideDown 0.3s ease-out'
          }}>
            <div style={{ padding: '24px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#1e293b' }}> Kampanya İşlem Merkezi</h2>
                <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.8rem' }}>Onaylanmış kampanyaları toplu olarak yönetin ve dışa aktarın</p>
              </div>
              <button onClick={() => setExportModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#94a3b8' }}>&times;</button>
            </div>
            
            <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
              <div style={{ 
                background: '#f8fafc', 
                padding: '16px', 
                borderRadius: '12px', 
                border: '1px solid #e2e8f0',
                marginBottom: '20px' 
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ fontSize: '2rem' }}></div>
                  <div>
                    <div style={{ fontWeight: 700, color: '#334155' }}>Toplu Müşteri Listesi Çıkarma</div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                      Onayladığınız <b>{approvedTotalCount}</b> kampanya için hedef müşteri bilgilerini (Ad, Telefon, Segment) Excel formatında indirebilirsiniz.
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Sepetteki Kampanyalar:</span>
                <button 
                    onClick={handleClearBasket}
                    style={{ background: 'none', border: 'none', color: '#ef4444', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', padding: '4px 8px', borderRadius: '4px' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#fef2f2'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
                >
                    🗑 Sepeti Temizle
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px', maxHeight: '200px', overflowY: 'auto', paddingRight: '4px' }}>
                {loadingApproved ? (
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', textAlign: 'center', padding: '10px' }}>Yükleniyor...</div>
                ) : approvedCampaigns.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', textAlign: 'center', padding: '10px' }}>Sepetiniz boş.</div>
                ) : approvedCampaigns.map(r => (
                    <div key={r.OneriID} style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        padding: '10px 12px', 
                        background: '#f8fafc', 
                        borderRadius: '8px', 
                        border: '1px solid #e2e8f0',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '1rem' }}>{r.KampanyaTipi === 'Cross-Sell' ? '' : ''}</span>
                            <div>
                                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#334155' }}>
                                    {r.KampanyaTipi === 'Cross-Sell' ? r.KategoriAdi : r.HedefSegment}
                                </div>
                                <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{Math.round(r.PotansiyelCiro || 0).toLocaleString('tr-TR')} ₺ Potansiyel</div>
                            </div>
                        </div>
                        <button 
                            onClick={() => handleRemoveFromBasket(r.OneriID)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', color: '#cbd5e1', padding: '4px' }}
                            onMouseEnter={(e) => e.currentTarget.style.color = '#ef4444'}
                            onMouseLeave={(e) => e.currentTarget.style.color = '#cbd5e1'}
                        >
                            &times;
                        </button>
                    </div>
                ))}
              </div>

              <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '12px' }}>Gelecek Özellikler (Hazırlık Aşamasında):</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ padding: '12px', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fef3c7', opacity: 0.7 }}>
                  <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>✉</div>
                  <div style={{ fontWeight: 600, fontSize: '0.75rem', color: '#92400e' }}>E-Posta Gönderimi</div>
                  <div style={{ fontSize: '0.65rem', color: '#b45309' }}>Hedef kitleye otomatik mail tasarımı gönderin</div>
                </div>
                <div style={{ padding: '12px', background: '#ecfdf5', borderRadius: '8px', border: '1px solid #d1fae5', opacity: 0.7 }}>
                  <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>📱</div>
                  <div style={{ fontWeight: 600, fontSize: '0.75rem', color: '#065f46' }}>SMS/WhatsApp</div>
                  <div style={{ fontSize: '0.65rem', color: '#047857' }}>Entegre kanallar üzerinden bildirim gönderin</div>
                </div>
              </div>
            </div>

            <div style={{ padding: '20px 24px', borderTop: '1px solid #f1f5f9' }}>
              {isExporting && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.8rem', color: '#6366f1', fontWeight: 600 }}>{exportStep}</span>
                    <span style={{ fontSize: '0.8rem', color: '#6366f1', fontWeight: 700 }}>{exportProgress}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: '#e0e7ff', borderRadius: '99px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${exportProgress}%`,
                      background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
                      borderRadius: '99px',
                      transition: 'width 0.3s ease'
                    }} />
                  </div>
                </div>
              )}
              <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => setExportModalOpen(false)}
                disabled={isExporting}
                style={{ flex: 1, padding: '12px', background: '#f1f5f9', color: '#64748b', border: 'none', borderRadius: '10px', fontWeight: 600, cursor: isExporting ? 'not-allowed' : 'pointer', opacity: isExporting ? 0.5 : 1 }}
              >
                Kapat
              </button>
              <button
                onClick={() => handleExportExcel()}
                disabled={isExporting}
                style={{
                  flex: 2,
                  padding: '12px',
                  background: isExporting ? '#a5b4fc' : '#6366f1',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  fontWeight: 600,
                  cursor: isExporting ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  transition: 'background 0.2s'
                }}
              >
                {isExporting ? `İşleniyor... ${exportProgress}%` : ' Excel Listesini İndir'}
              </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* GLOBAL EXPORT PROGRESS OVERLAY */}
      {isExporting && (
        <div style={{
          position: 'fixed',
          bottom: '32px',
          right: '32px',
          zIndex: 3000,
          background: 'white',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
          padding: '20px 24px',
          minWidth: '320px',
          border: '1px solid #e0e7ff',
          animation: 'slideDown 0.3s ease-out'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#1e293b' }}>Excel Hazırlanıyor</div>
              <div style={{ fontSize: '0.78rem', color: '#6366f1', marginTop: '1px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{exportStep}</div>
            </div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#6366f1', flexShrink: 0 }}>{exportProgress}%</div>
          </div>
          <div style={{ width: '100%', height: '6px', background: '#e0e7ff', borderRadius: '99px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${exportProgress}%`,
              background: exportProgress === 100
                ? 'linear-gradient(90deg, #10b981, #059669)'
                : 'linear-gradient(90deg, #6366f1, #8b5cf6)',
              borderRadius: '99px',
              transition: 'width 0.4s ease'
            }} />
          </div>
        </div>
      )}

      {variantProducerOpened && activeCampaignForVariants && (
        <CampaignVariantProducer
          opened={variantProducerOpened}
          onClose={() => setVariantProducerOpened(false)}
          campaignDetail={activeCampaignForVariants}
        />
      )}

      <CampaignScheduler 
        opened={schedulerOpened} 
        onClose={() => setSchedulerOpened(false)} 
        initialData={{
          title: `${activeCampaignForSchedule?.KategoriAdi} - ${activeCampaignForSchedule?.KampanyaTipi} Kampanyası`,
          description: `${activeCampaignForSchedule?.UrunAdi || activeCampaignForSchedule?.KategoriAdi} ürünü için hazırlanan özel fırsat.`,
          segment: activeCampaignForSchedule?.KampanyaTipi === 'Cross-Sell' ? 'Sampiyonlar' : 'Risk Altindakiler'
        }}
      />
    </div>
  )
}
