import { useState, useEffect, useRef, useCallback, useMemo, useReducer } from 'react'
import { formatPercent } from '../utils/format'
import { useSearchParams } from 'react-router-dom'
import apiClient from '../api/client'
import RevenueChart from '../components/RevenueChart'
import FilterPanel, { FilterState as FilterPanelState } from '../components/FilterPanel'
import LoadingOverlay from '../components/LoadingOverlay'
import InlineSpinner from '../components/InlineSpinner'
import useDashboardStore from '../stores/dashboardStore'
import ProductPortal from '../components/ProductPortal'
import {
  IconBox, IconBuildingStore, IconCurrencyLira,
  IconChartBar, IconTrendingUp, IconSearch, IconX,
  IconTrophy, IconPlayerPlay,
  IconTag, IconReceipt
} from '@tabler/icons-react'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import '../styles/ProductsTree.css'
import '../styles/DashboardHome.css'



// Skeleton Component
const Skeleton = ({ className, style }: any) => (
  <div className={`skeleton ${className}`} style={style}></div>
)

// Performans metrikleri hook'u - kart bazlı yükleme sürelerini ölçer
const usePerformanceMetrics = () => {
  const metricsRef = useRef<Record<string, { start: number; end?: number; duration?: number }>>({})

  const startMeasure = useCallback((name: string) => {
    metricsRef.current[name] = { start: performance.now() }
  }, [])

  const endMeasure = useCallback((name: string): number => {
    const metric = metricsRef.current[name]
    if (metric && !metric.end) {
      metric.end = performance.now()
      metric.duration = metric.end - metric.start
      // PerfOverlay'e gönder (eğer aktifse)
      if (typeof window !== 'undefined' && (window as any).__perfStore) {
        (window as any).__perfStore.marks[name] = metric.duration
      }
      return metric.duration
    }
    return 0
  }, [])

  const getMetrics = useCallback(() => {
    return Object.entries(metricsRef.current).map(([name, data]) => ({
      name,
      duration: data.duration || 0
    }))
  }, [])

  return { startMeasure, endMeasure, getMetrics }
}

// Filter state için reducer - 13 ayrı setState yerine tek dispatch
interface FilterState {
  selectedCategories: string[]
  selectedBrand: string
  selectedProducts: string[]
  searchTerm: string
  searchResults: { id?: number; name: string; brand: string; category: string; sales: number }[]
  categorySearch: string
  brandSearch: string
  showCategoryDropdown: boolean
  showBrandDropdown: boolean
  expandedUstKat: Set<string>
  expandedAnaKat: Set<string>
  expandedAltKat1: Set<string>
}

type FilterAction =
  | { type: 'RESET_ALL' }
  | { type: 'SET_CATEGORIES'; payload: string[] }
  | { type: 'SET_BRAND'; payload: string }
  | { type: 'SET_PRODUCTS'; payload: string[] }
  | { type: 'SET_SEARCH_TERM'; payload: string }
  | { type: 'SET_SEARCH_RESULTS'; payload: { id?: number; name: string; brand: string; category: string; sales: number }[] }
  | { type: 'SET_CATEGORY_SEARCH'; payload: string }
  | { type: 'SET_BRAND_SEARCH'; payload: string }
  | { type: 'SET_SHOW_CATEGORY_DROPDOWN'; payload: boolean }
  | { type: 'SET_SHOW_BRAND_DROPDOWN'; payload: boolean }
  | { type: 'SET_EXPANDED_UST_KAT'; payload: Set<string> }
  | { type: 'SET_EXPANDED_ANA_KAT'; payload: Set<string> }
  | { type: 'SET_EXPANDED_ALT_KAT1'; payload: Set<string> }
  | { type: 'TOGGLE_PRODUCT'; payload: string }

const initialFilterState: FilterState = {
  selectedCategories: [],
  selectedBrand: '',
  selectedProducts: [],
  searchTerm: '',
  searchResults: [],
  categorySearch: '',
  brandSearch: '',
  showCategoryDropdown: false,
  showBrandDropdown: false,
  expandedUstKat: new Set(),
  expandedAnaKat: new Set(),
  expandedAltKat1: new Set()
}

function filterReducer(state: FilterState, action: FilterAction): FilterState {
  switch (action.type) {
    case 'RESET_ALL':
      return { ...initialFilterState }
    case 'SET_CATEGORIES':
      return { ...state, selectedCategories: action.payload, selectedProducts: [] }
    case 'SET_BRAND':
      return { ...state, selectedBrand: action.payload }
    case 'SET_PRODUCTS':
      return { ...state, selectedProducts: action.payload }
    case 'SET_SEARCH_TERM':
      return { ...state, searchTerm: action.payload }
    case 'SET_SEARCH_RESULTS':
      return { ...state, searchResults: action.payload }
    case 'SET_CATEGORY_SEARCH':
      return { ...state, categorySearch: action.payload }
    case 'SET_BRAND_SEARCH':
      return { ...state, brandSearch: action.payload }
    case 'SET_SHOW_CATEGORY_DROPDOWN':
      return { ...state, showCategoryDropdown: action.payload }
    case 'SET_SHOW_BRAND_DROPDOWN':
      return { ...state, showBrandDropdown: action.payload }
    case 'SET_EXPANDED_UST_KAT':
      return { ...state, expandedUstKat: action.payload }
    case 'SET_EXPANDED_ANA_KAT':
      return { ...state, expandedAnaKat: action.payload }
    case 'SET_EXPANDED_ALT_KAT1':
      return { ...state, expandedAltKat1: action.payload }
    case 'TOGGLE_PRODUCT': {
      const productName = action.payload
      const newSelection = state.selectedProducts.includes(productName)
        ? state.selectedProducts.filter(p => p !== productName)
        : [...state.selectedProducts, productName]
      return { ...state, selectedProducts: newSelection }
    }
    default:
      return state
  }
}

// Debounce sabiti - 50ms yerine 300ms (performans için)
const FILTER_DEBOUNCE_MS = 300

interface Analytics {
  totalBrands: number
  totalCategories: number
  totalProducts: number
  totalRevenue: number
  totalQuantity?: number
  totalReceipts?: number
  averageOrderValue?: number
  averageProductPrice?: number
  hasProductColumn?: boolean
  priceRanges: { range: string; count: number }[]
  topBrands: { name: string; sales: number }[]
  topProducts: { 
    id?: number; 
    name: string; 
    sales: number; 
    count: number; 
    brand: string; 
    category: string; 
    customerCount?: number; 
    frequency?: number;
    perf_kat?: string;
    trend?: string;
    stok_durumu?: string;
    uyari?: string;
    kat_payi?: number;
    kat_perf?: string;
  }[]
  topCategories?: { name: string; sales: number }[]
  salesByMonth: { month: string; sales: number }[]
  superCategoryRevenue?: { category: string; revenue: number }[]
  productCategories?: { category: string; revenue: number }[]
}

// Türkçe karakter normalizasyonu
const normalizeTurkish = (text: string) => {
  if (typeof text !== 'string') return ''
  if (!text) return ''
  return text
    .replace(/Ğ/g, 'g')
    .replace(/Ü/g, 'u')
    .replace(/Ş/g, 's')
    .replace(/I/g, 'i')
    .replace(/İ/g, 'i')
    .replace(/Ö/g, 'o')
    .replace(/Ç/g, 'c')
    .replace(/ğ/g, 'g')
    .replace(/ü/g, 'u')
    .replace(/ş/g, 's')
    .replace(/ı/g, 'i')
    .replace(/ö/g, 'o')
    .replace(/ç/g, 'c')
    .toLowerCase()
}

export default function Products() {
  const {
    selectedDataSourceId,
    selectedYear,
    selectedMonth,
    selectedStartDate,
    selectedEndDate,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedRegion,
    setAvailableYears: setGlobalAvailableYears,
    setAvailableRegions,
    setAvailableCustomerTypes,
    setAvailableApprovalStatuses
  } = useDashboardStore()

  const [searchParams, setSearchParams] = useSearchParams()
  const urlProductId = searchParams.get('productId')

  // Performans metrikleri hook'u
  const { startMeasure, endMeasure, getMetrics } = usePerformanceMetrics()

  const [loading, setLoading] = useState(false)
  const [filterLoading, setFilterLoading] = useState(false) // Filtre uygulama loading'i
  const [isApiCallInProgress, setIsApiCallInProgress] = useState(false) // Global API loading state

  // Product Portal state
  const [portalProductId, setPortalProductId] = useState<number>(0)
  const [portalProductName, setPortalProductName] = useState('')
  const [isPortalOpen, setIsPortalOpen] = useState(false)

  const openProductPortal = async (productId: number | undefined, productName: string) => {
    if (productId != null && productId > 0) {
      setPortalProductId(productId)
      setPortalProductName(productName)
      setIsPortalOpen(true)
      return
    }
    // id yoksa arama ile bul
    try {
      const res = await apiClient.searchProducts(selectedDataSourceId!, productName, 1)
      if (res.results && res.results.length > 0 && res.results[0].id != null && res.results[0].id > 0) {
        setPortalProductId(res.results[0].id)
        setPortalProductName(productName)
        setIsPortalOpen(true)
      } else {
        console.warn('[Products] Search returned no valid ID for:', productName)
      }
    } catch (e) {
      console.error('[Products] Product ID lookup failed:', e)
    }
  }

  // Filter state - useReducer ile batch update (13 re-render yerine 1)
  const [filterState, dispatch] = useReducer(filterReducer, initialFilterState)
  const {
    selectedCategories,
    selectedBrand,
    selectedProducts,
    searchTerm,
    searchResults,
    categorySearch,
    brandSearch,
    showCategoryDropdown,
    showBrandDropdown,
    expandedUstKat,
    expandedAnaKat,
    expandedAltKat1
  } = filterState

  // Setter fonksiyonları - eski API ile uyumluluk için (fonksiyonel update destekli)
  const setSelectedCategories = useCallback((catsOrFn: string[] | ((prev: string[]) => string[])) => {
    if (typeof catsOrFn === 'function') {
      dispatch({ type: 'SET_CATEGORIES', payload: catsOrFn(filterState.selectedCategories) })
    } else {
      dispatch({ type: 'SET_CATEGORIES', payload: catsOrFn })
    }
  }, [filterState.selectedCategories])

  const setSelectedBrand = useCallback((brand: string) => dispatch({ type: 'SET_BRAND', payload: brand }), [])

  const setSelectedProducts = useCallback((prodsOrFn: string[] | ((prev: string[]) => string[])) => {
    if (typeof prodsOrFn === 'function') {
      dispatch({ type: 'SET_PRODUCTS', payload: prodsOrFn(filterState.selectedProducts) })
    } else {
      dispatch({ type: 'SET_PRODUCTS', payload: prodsOrFn })
    }
  }, [filterState.selectedProducts])

  const setSearchTerm = useCallback((term: string) => dispatch({ type: 'SET_SEARCH_TERM', payload: term }), [])
  const setSearchResults = useCallback((results: { id?: number; name: string; brand: string; category: string; sales: number }[]) => dispatch({ type: 'SET_SEARCH_RESULTS', payload: results }), [])
  const setCategorySearch = useCallback((search: string) => dispatch({ type: 'SET_CATEGORY_SEARCH', payload: search }), [])
  const setBrandSearch = useCallback((search: string) => dispatch({ type: 'SET_BRAND_SEARCH', payload: search }), [])
  const setShowCategoryDropdown = useCallback((show: boolean) => dispatch({ type: 'SET_SHOW_CATEGORY_DROPDOWN', payload: show }), [])
  const setShowBrandDropdown = useCallback((show: boolean) => dispatch({ type: 'SET_SHOW_BRAND_DROPDOWN', payload: show }), [])

  const setExpandedUstKat = useCallback((expandedOrFn: Set<string> | ((prev: Set<string>) => Set<string>)) => {
    if (typeof expandedOrFn === 'function') {
      dispatch({ type: 'SET_EXPANDED_UST_KAT', payload: expandedOrFn(filterState.expandedUstKat) })
    } else {
      dispatch({ type: 'SET_EXPANDED_UST_KAT', payload: expandedOrFn })
    }
  }, [filterState.expandedUstKat])

  const setExpandedAnaKat = useCallback((expandedOrFn: Set<string> | ((prev: Set<string>) => Set<string>)) => {
    if (typeof expandedOrFn === 'function') {
      dispatch({ type: 'SET_EXPANDED_ANA_KAT', payload: expandedOrFn(filterState.expandedAnaKat) })
    } else {
      dispatch({ type: 'SET_EXPANDED_ANA_KAT', payload: expandedOrFn })
    }
  }, [filterState.expandedAnaKat])

  const setExpandedAltKat1 = useCallback((expandedOrFn: Set<string> | ((prev: Set<string>) => Set<string>)) => {
    if (typeof expandedOrFn === 'function') {
      dispatch({ type: 'SET_EXPANDED_ALT_KAT1', payload: expandedOrFn(filterState.expandedAltKat1) })
    } else {
      dispatch({ type: 'SET_EXPANDED_ALT_KAT1', payload: expandedOrFn })
    }
  }, [filterState.expandedAltKat1])

  // Data
  const [globalStats, setGlobalStats] = useState<Analytics | null>(null) // Genel özet (ilk açılış)
  const [currentStats, setCurrentStats] = useState<Analytics | null>(null) // Seçime göre değişen özet
  const [categoriesList, setCategoriesList] = useState<string[]>([])
  const [brandsList, setBrandsList] = useState<string[]>([])
  const [flatCategoriesList, setFlatCategoriesList] = useState<string[]>([])
  const [categoryHierarchy, setCategoryHierarchy] = useState<any>({})
  const [searchLoading, setSearchLoading] = useState(false)

  // DonutChart State
  const [hoveredSlice, setHoveredSlice] = useState<string | null>(null)
  const [showOthersBreakdown, setShowOthersBreakdown] = useState(false)
  const [donutViewMode, setDonutViewMode] = useState<'category' | 'brand'>('category')

  const pieLegendRef = useRef<HTMLDivElement>(null)
  const pieOthersRef = useRef<HTMLDivElement>(null)
  const donutData = useMemo(() => {
    if (!currentStats) return []
    return donutViewMode === 'category'
      ? (currentStats.topCategories || []).map((c: any) => ({ name: c.name || c.category || 'Bilinmeyen', revenue: c.sales || c.revenue || 0 }))
      : (currentStats.topBrands || []).map((b: any) => ({ name: b.name || 'Bilinmeyen', revenue: b.sales || b.revenue || 0 }))
  }, [currentStats, donutViewMode])
  const handleSliceClick = useCallback((_data: { name: string }) => {
    if (donutViewMode === 'category') {
      setSelectedCategories(prev => prev.includes(_data.name) ? prev : [...prev, _data.name])
    }
  }, [donutViewMode])

  // Dropdown search (local)
  const [categorySearchLoading, setCategorySearchLoading] = useState(false)
  const [brandSearchLoading, setBrandSearchLoading] = useState(false)
  const categorySearchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const brandSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Available years/months from data
  const [availableYears, setAvailableYears] = useState<number[]>([])
  const [availableMonths, setAvailableMonths] = useState<number[]>([])

  // Performance optimization refs
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const lastSearchRef = useRef<string>('')
  const filterRequestIdRef = useRef<number>(0) // Son filtre isteğini takip et
  const filterDebounceRef = useRef<NodeJS.Timeout | null>(null) // Filtre debounce
  const globalStatsRef = useRef<Analytics | null>(null) // Race condition önlemek için
  const isRequestInProgressRef = useRef<boolean>(false) // Concurrent request'leri önlemek için
  const globalAbortControllerRef = useRef<AbortController | null>(null) // Request iptali için

  // Tüm filtreleri tek bir hash'e dönüştür - useEffect dependency optimizasyonu
  const filterHash = useMemo(() => JSON.stringify({
    categories: selectedCategories.slice().sort(),
    brand: selectedBrand,
    products: selectedProducts.slice().sort(),
    year: selectedYear,
    month: selectedMonth,
    startDate: selectedStartDate,
    endDate: selectedEndDate,
    customerType: selectedCustomerType,
    approvalStatus: selectedApprovalStatus,
    region: selectedRegion
  }), [selectedCategories, selectedBrand, selectedProducts, selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  // 1. İlk Yükleme (Hızlı Açılış)
  useEffect(() => {
    if (selectedDataSourceId) {
      // DataSource değişince eski state'i temizle - TEK DISPATCH ile
      dispatch({ type: 'RESET_ALL' })
      setAvailableYears([])
      setAvailableMonths([])
      setCategoriesList([])
      setBrandsList([])
      setFlatCategoriesList([])
      setCategoryHierarchy({})
      setGlobalStats(null)
      setCurrentStats(null)
      loadInitialData()
    }
  }, [selectedDataSourceId])

  // globalStats değiştiğinde ref'i güncelle (dependency race condition'ı önlemek için)
  useEffect(() => {
    globalStatsRef.current = globalStats
  }, [globalStats])

  // Debug: currentStats değişikliklerini izle
  useEffect(() => {
  }, [currentStats])

  // 2. Filtre değişikliklerini tek bir useEffect'te yönet (debounce ile)
  // Optimize edildi: 15 dependency yerine filterHash kullanılıyor
  useEffect(() => {
    if (!selectedDataSourceId || !globalStatsRef.current) return

    // Önceki debounce timer'ı temizle
    if (filterDebounceRef.current) {
      clearTimeout(filterDebounceRef.current)
    }

    // Ürün seçilmişse öncelik ondadır (debounce ile)
    if (selectedProducts.length > 0) {
      // 300ms debounce - performans için artırıldı (50ms'den)
      filterDebounceRef.current = setTimeout(() => {
        startMeasure('filter_apply')
        loadSelectedProductsData(selectedProducts)
      }, FILTER_DEBOUNCE_MS)
      return
    }

    // Herhangi bir filtre aktifse loadFilteredData kullan
    const hasFilters = selectedCategories.length > 0 ||
                       selectedBrand ||
                       selectedYear ||
                       selectedMonth ||
                       selectedStartDate ||
                       selectedEndDate ||
                       selectedCustomerType ||
                       selectedApprovalStatus ||
                       selectedRegion

    if (hasFilters) {
      // 300ms debounce - birden fazla hızlı state değişikliğini tek çağrıya birleştir
      filterDebounceRef.current = setTimeout(() => {
        startMeasure('filter_apply')
        loadFilteredData()
      }, FILTER_DEBOUNCE_MS)
    } else {
      // Hiç filtre yoksa global stats göster
      setCurrentStats(globalStatsRef.current)
    }

    // Cleanup
    return () => {
      if (filterDebounceRef.current) {
        clearTimeout(filterDebounceRef.current)
      }
    }
  }, [filterHash, selectedDataSourceId, startMeasure])

  // Dropdown search debounce (local)
  useEffect(() => {
    if (categorySearchTimeoutRef.current) {
      clearTimeout(categorySearchTimeoutRef.current)
    }
    if (!showCategoryDropdown) {
      setCategorySearchLoading(false)
      return
    }
    setCategorySearchLoading(true)
    categorySearchTimeoutRef.current = setTimeout(() => {
      setCategorySearchLoading(false)
    }, 150)
    return () => {
      if (categorySearchTimeoutRef.current) clearTimeout(categorySearchTimeoutRef.current)
    }
  }, [categorySearch, showCategoryDropdown])

  useEffect(() => {
    if (brandSearchTimeoutRef.current) {
      clearTimeout(brandSearchTimeoutRef.current)
    }
    if (!showBrandDropdown) {
      setBrandSearchLoading(false)
      return
    }
    setBrandSearchLoading(true)
    brandSearchTimeoutRef.current = setTimeout(() => {
      setBrandSearchLoading(false)
    }, 150)
    return () => {
      if (brandSearchTimeoutRef.current) clearTimeout(brandSearchTimeoutRef.current)
    }
  }, [brandSearch, showBrandDropdown])

  // NEW: Handle direct navigation to a product from URL
  useEffect(() => {
    if (urlProductId && selectedDataSourceId) {
      // Parametreyi temizle ki geri dönüldüğünde veya sayfa yenilendiğinde tekrar açılmasın
      setSearchParams({}, { replace: true })
      
      const id = parseInt(urlProductId)
      if (!isNaN(id)) {
        openProductPortal(id, 'Ürün Detayı')
      }
    }
  }, [urlProductId, selectedDataSourceId])

  // 4. Arama
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    if (searchTerm.length < 2) {
      setSearchResults([])
      setSearchLoading(false)
      return
    }
    
    if (searchTerm === lastSearchRef.current) {
      return
    }
    
    setSearchLoading(true)
    
    searchTimeoutRef.current = setTimeout(() => {
      performSearch(searchTerm)
    }, 150)

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchTerm, selectedDataSourceId])


  const loadInitialData = async () => {
    try {
      startMeasure('initial_load')
      if (!globalStats) {
        setLoading(true)
      }
      // Yıl/ay filtresi varsa onu da gönder
      const data = await apiClient.getDataSourceAnalytics(
        selectedDataSourceId,
        [], // segments
        [], // categories
        [], // brands
        selectedYear || undefined,
        selectedMonth || undefined,
        selectedStartDate || undefined,
        selectedEndDate || undefined
      )
      
      if (data.availableYears) {
        setAvailableYears(data.availableYears)
        setGlobalAvailableYears(data.availableYears) // Global store'a da aktar
      }
      if (data.availableMonths) setAvailableMonths(data.availableMonths)

      // Yeni filtre dataları
      if (data.availableRegions) setAvailableRegions(data.availableRegions)
      if (data.availableCustomerTypes) setAvailableCustomerTypes(data.availableCustomerTypes)
      if (data.availableApprovalStatuses) setAvailableApprovalStatuses(data.availableApprovalStatuses)

      if (data.analytics) {
        const stats: Analytics = {
            totalBrands: data.analytics.totalBrands || 0,
            totalCategories: data.analytics.totalCategories || 0,
            totalProducts: data.analytics.totalProducts || 0,
            totalRevenue: data.analytics.totalRevenue || 0,
            hasProductColumn: data.analytics.hasProductColumn,
            priceRanges: data.analytics.priceRanges || [],
            topBrands: data.analytics.topBrands || [],
            topCategories: (data.analytics.productCategories || []).map((c: any) => ({
              name: c.category || 'Bilinmeyen',
              sales: c.revenue || 0
            })),
            topProducts: (data.analytics.topProducts || data.analytics.productRevenue || []).map((p: any) => ({
              id: p.id,
              name: p.name || 'Bilinmeyen',
              sales: p.sales || p.revenue || 0,
              count: p.count || 0,
              brand: p.brand || '-',
              category: p.category || '-',
              customerCount: p.customer_count || 0,
              frequency: p.frequency || 0
            })),
            salesByMonth: data.analytics.salesByMonth || [],
            superCategoryRevenue: data.analytics.superCategoryRevenue || [],
            productCategories: data.analytics.productCategories || []
        }
        setGlobalStats(stats)
        setCurrentStats(stats)
        
        setCategoryHierarchy(data.categoryHierarchy || {})

        if (data.categoryHierarchy) {
          const allCategories = new Set<string>()
          Object.keys(data.categoryHierarchy || {}).forEach((ustKat) => {
            allCategories.add(String(ustKat))
            const ana = (data.categoryHierarchy || {})[ustKat] || {}
            Object.keys(ana).forEach((anaKat) => {
              allCategories.add(String(anaKat))
              const alt1Obj = ana[anaKat] || {}
              Object.keys(alt1Obj).forEach((alt1) => {
                allCategories.add(String(alt1))
                const alt2Arr = alt1Obj[alt1] || []
                if (Array.isArray(alt2Arr)) {
                   alt2Arr.forEach((alt2: any) => allCategories.add(String(alt2)))
                }
              })
            })
          })
          setFlatCategoriesList(Array.from(allCategories).sort((a, b) => a.localeCompare(b, 'tr')))
        }

        if (data.brandByCategory) {
          const allBrands = new Set<string>()
          Object.values<any>(data.brandByCategory).forEach((brands) => {
            if (Array.isArray(brands)) {
              brands.forEach((b) => {
                if (b) allBrands.add(String(b))
              })
            }
          })
          setBrandsList(Array.from(allBrands).sort((a, b) => a.localeCompare(b, 'tr')))
        }
        
        if (stats.topCategories) {
            setCategoriesList(stats.topCategories.map(c => c.name).sort())
        }
      }
    } catch (err: any) {
      console.error('[Products] loadInitialData error:', err?.message || err)
    } finally {
      setLoading(false)
      endMeasure('initial_load')
    }
  }

  const loadFilteredData = async () => {
    // Eğer zaten request devam ediyorsa bekle
    if (isRequestInProgressRef.current) {
      return
    }

    // Her çağrıda yeni bir request ID oluştur
    const currentRequestId = ++filterRequestIdRef.current

    try {
      // Önceki request'i iptal et
      if (globalAbortControllerRef.current) {
        globalAbortControllerRef.current.abort()
      }

      // Hiç filtre yoksa global stats'ı kullan
      if (!selectedYear && !selectedMonth && !selectedStartDate && !selectedEndDate && !selectedBrand && selectedCategories.length === 0 && selectedProducts.length === 0 && !selectedCustomerType && !selectedApprovalStatus && !selectedRegion) {
        setCurrentStats(globalStatsRef.current)
        setFilterLoading(false)
        setIsApiCallInProgress(false)
        return
      }

      // Request durumunu güncelle
      isRequestInProgressRef.current = true
      globalAbortControllerRef.current = new AbortController()

      setFilterLoading(true)
      setIsApiCallInProgress(true) // Global API loading state

      const data = await apiClient.getProductAnalytics(
        selectedDataSourceId,
        selectedCategories, // Multi-select kategoriler
        selectedBrand ? [selectedBrand] : [],
        selectedProducts,
        selectedYear || undefined,
        selectedMonth || undefined,
        selectedStartDate || undefined,
        selectedEndDate || undefined,
        selectedCustomerType || undefined,
        selectedApprovalStatus || undefined,
        selectedRegion || undefined
      )

      // Eğer bu istek artık güncel değilse (yeni bir istek yapıldıysa), sonucu ignore et
      if (currentRequestId !== filterRequestIdRef.current) {
        return
      }

      if (!data.analytics) {
        console.warn('[Products] No analytics data in response!')
        console.warn('[Products] Full response structure:', Object.keys(data))
        // Boş stats oluştur ki UI çökmesin
        const emptyStats = {
          totalBrands: 0,
          totalCategories: 0,
          totalProducts: 0,
          totalRevenue: 0,
          hasProductColumn: false,
          priceRanges: [],
          topBrands: [],
          topCategories: [],
          topProducts: [],
          salesByMonth: []
        }
        setCurrentStats(emptyStats)
        return
      }

      if (data.analytics) {
        const stats: Analytics = {
          totalBrands: data.analytics.totalBrands || 0,
          totalCategories: data.analytics.totalCategories || 0,
          totalProducts: data.analytics.totalProducts || 0,
          totalRevenue: data.analytics.totalRevenue || 0,
          hasProductColumn: data.analytics.hasProductColumn,
          priceRanges: data.analytics.priceRanges || [],
          topBrands: data.analytics.topBrands || [],
          topCategories: (data.analytics.productCategories || []).map((c: any) => ({
            name: c.category || 'Bilinmeyen',
            sales: c.revenue || 0
          })),
          topProducts: (data.analytics.topProducts || []).map((p: any) => ({
            id: p.id,
            name: p.name || 'Bilinmeyen',
            sales: p.sales || 0,
            count: p.count || 0,
            brand: p.brand || '-',
            category: p.category || '-',
            customerCount: p.customer_count || 0,
            frequency: p.frequency || 0
          })),
          salesByMonth: data.analytics.salesByMonth || [],
          superCategoryRevenue: data.analytics.superCategoryRevenue || [],
          productCategories: data.analytics.productCategories || []
        }
        setCurrentStats(stats)
      }
    } catch (err) {
      // Hata sessizce ele alınır
      console.error('[Products] loadFilteredData error:', err)
    } finally {
      setFilterLoading(false) // Filtre loading bitir
      setIsApiCallInProgress(false) // Global API loading state
      isRequestInProgressRef.current = false // Request durumunu sıfırla
      globalAbortControllerRef.current = null // Abort controller'ı temizle
      endMeasure('filter_apply')
    }
  }

  const loadSelectedProductsData = async (products: string[]) => {
    // Eğer zaten request devam ediyorsa bekle
    if (isRequestInProgressRef.current) {
      return
    }

    try {
      // Önceki request'i iptal et
      if (globalAbortControllerRef.current) {
        globalAbortControllerRef.current.abort()
      }

      // Request durumunu güncelle
      isRequestInProgressRef.current = true
      globalAbortControllerRef.current = new AbortController()

      setFilterLoading(true)
      setIsApiCallInProgress(true) // Global API loading state
      
      const data = await apiClient.getProductAnalytics(
        selectedDataSourceId,
        selectedCategories,
        selectedBrand ? [selectedBrand] : [],
        products,
        selectedYear || undefined,
        selectedMonth || undefined,
        selectedStartDate || undefined,
        selectedEndDate || undefined,
        selectedCustomerType || undefined,
        selectedApprovalStatus || undefined,
        selectedRegion || undefined
      )
      if (data.analytics) {
        const stats = {
          ...data.analytics,
          totalRevenue: data.analytics.totalRevenue || 0,
          totalProducts: data.analytics.totalProducts || 0,
          totalBrands: data.analytics.totalBrands || 0,
          topProducts: (data.analytics.topProducts || []).map((p: any) => ({
            ...p,
            sales: p.sales || 0,
            count: p.count || 0,
            brand: p.brand || '-',
            name: p.name || 'Bilinmeyen',
            category: p.category || '-'
          })),
          salesByMonth: data.analytics.salesByMonth || []
        }
        setCurrentStats(stats)
      }
    } catch (err) {
      // Hata sessizce ele alınır
      console.error('[Products] loadSelectedProductsData error:', err)
    } finally {
      setFilterLoading(false) // Filtre loading bitir
      setIsApiCallInProgress(false) // Global API loading state
      isRequestInProgressRef.current = false // Request durumunu sıfırla
      globalAbortControllerRef.current = null // Abort controller'ı temizle
      endMeasure('filter_apply')
    }
  }
  
  // Is it a "detail" range? (<= 90 days)
  const isShortDateRange = useMemo(() => {
    if (!selectedStartDate || !selectedEndDate) return false;
    const start = new Date(selectedStartDate);
    const end = new Date(selectedEndDate);
    const diffDays = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
    return diffDays <= 90;
  }, [selectedStartDate, selectedEndDate]);

  // Frontend aggregation for monthly view
  const aggregatedMonthlyData = useMemo(() => {
    if (isShortDateRange || !currentStats?.salesByMonth) return [];
    const monthly: Record<string, number> = {};
    currentStats.salesByMonth.forEach(item => {
      if (!item.month) return;
      const monthKey = item.month.substring(0, 7); // "YYYY-MM"
      monthly[monthKey] = (monthly[monthKey] || 0) + item.sales;
    });
    return Object.keys(monthly).sort().map(key => ({
      month: key,
      sales: monthly[key]
    }));
  }, [currentStats?.salesByMonth, isShortDateRange]);

  // DonutChart callbacks
  const handleHoveredSliceChange = useCallback((slice: string | null) => {
    setHoveredSlice(slice)
  }, [])

  const handleShowOthersBreakdownChange = useCallback((show: boolean) => {
    setShowOthersBreakdown(show)
  }, [])



  // DonutChart data - categories or brands based on view mode


  const performSearch = useCallback(async (term: string) => {
    startMeasure('search_query')
    abortControllerRef.current = new AbortController()
    
    try {
      const response = await apiClient.searchProducts(selectedDataSourceId, term)
      
      if (abortControllerRef.current?.signal.aborted) {
        return
      }
      
      lastSearchRef.current = term
      
      if (response.results) {
        const results = response.results.map((p: any) => ({
          id: p.id,
          name: p.name,
          brand: p.brand || '-',
          category: p.category || '-',
          sales: p.revenue || 0
        }))
        setSearchResults(results)
      } else {
        setSearchResults([])
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') return
      setSearchResults([])
    } finally {
      setSearchLoading(false)
      endMeasure('search_query')
    }
  }, [selectedDataSourceId])

  const toggleProduct = (productName: string) => {
    const newSelection = selectedProducts.includes(productName)
      ? selectedProducts.filter(p => p !== productName)
      : [...selectedProducts, productName]
    setSelectedProducts(newSelection)
  }

  if (!selectedDataSourceId) return <div className="products-page"><div className="empty-state">Veri kaynağı seçin</div></div>

  // Loading skeleton - her zaman göster (loading durumunda)
  const LoadingSkeleton = () => (
    <div className="products-page" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Filter skeletons */}
        <div style={{ display: 'flex', gap: '16px' }}>
          <Skeleton style={{ flex: 1, height: '44px', borderRadius: '8px' }} />
          <Skeleton style={{ flex: 1, height: '44px', borderRadius: '8px' }} />
          <Skeleton style={{ flex: 2, height: '44px', borderRadius: '8px' }} />
        </div>
        {/* KPI skeletons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '20px' }}>
          <Skeleton style={{ height: '120px', borderRadius: '16px' }} />
          <Skeleton style={{ height: '120px', borderRadius: '16px' }} />
          <Skeleton style={{ height: '120px', borderRadius: '16px' }} />
          <Skeleton style={{ height: '120px', borderRadius: '16px' }} />
          <Skeleton style={{ height: '120px', borderRadius: '16px' }} />
        </div>
        {/* Chart skeletons */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          <Skeleton style={{ height: '360px', borderRadius: '16px' }} />
          <Skeleton style={{ height: '560px', borderRadius: '16px' }} />
        </div>
      </div>
    </div>
  )

  if (loading && !currentStats) {
    return <LoadingSkeleton />
  }

  return (
    <>
    <div className="products-page" style={{ padding: 0 }}>
    <LoadingOverlay loading={loading}>
      <div style={{ padding: '0 30px 30px 30px' }}>
      {selectedProducts.length > 0 && (
        <div className="selected-products-banner">
            <div className="selected-info">
                <span className="selected-icon">🛒</span>
                <span className="selected-count">{selectedProducts.length}</span>
                <span className="selected-text">Ürün Seçili</span>
            </div>
            <button
                className="clear-selection-btn"
                onClick={() => { setSelectedProducts([]); setSearchTerm(''); }}
            >
                <span>✕</span>
                <span>Temizle</span>
            </button>
        </div>
      )}

      <div className="products-content" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h2 style={{ margin: 0 }}>Ürün Analizi <span style={{ fontSize: '0.6em', color: '#9ca3af' }}>v29.3</span></h2>  
        </div>

            <div style={{ 
              display: 'flex', 
              flexWrap: 'wrap', 
              gap: '16px', 
              alignItems: 'flex-start',
              background: '#f8fafc',
              padding: '16px',
              borderRadius: '12px',
              border: '1px solid #e2e8f0'
            }}>
                {/* 1. Kategori Dropdown - Multi-Select Hiyerarşik */}
                <div style={{ flex: '1 1 280px', minWidth: '280px', position: 'relative' }}>
                    <button
                        onClick={() => {
                            const next = !showCategoryDropdown
                            setShowCategoryDropdown(next)
                            if (next) {
                                setCategorySearch('')
                                setShowBrandDropdown(false)
                            }
                        }}
                        style={{
                            width: '100%',
                            padding: '10px 16px',
                            fontSize: '0.95em',
                            border: selectedCategories.length > 0 ? '2px solid #4f46e5' : '1px solid #d1d5db',
                            borderRadius: '8px',
                            background: filterLoading ? '#f3f4f6' : 'white',
                            textAlign: 'left',
                            cursor: 'pointer',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            color: selectedCategories.length > 0 ? '#4f46e5' : '#374151',
                            fontWeight: selectedCategories.length > 0 ? 600 : 400,
                            transition: 'all 0.2s'
                        }}
                    >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {filterLoading && <span className="inline-spinner" style={{ width: '14px', height: '14px', border: '2px solid #e5e7eb', borderTopColor: '#4f46e5', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />}
                            {selectedCategories.length === 0 ? 'Tüm Kategoriler' :
                             selectedCategories.length === 1 ? selectedCategories[0] :
                             `${selectedCategories.length} kategori seçili`}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {selectedCategories.length > 0 && (
                                <span
                                    onClick={(e) => { e.stopPropagation(); setSelectedCategories([]); setSelectedProducts([]); }}
                                    style={{
                                        background: '#ef4444',
                                        color: 'white',
                                        borderRadius: '50%',
                                        width: '18px',
                                        height: '18px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '0.7em',
                                        fontWeight: 'bold'
                                    }}
                                >✕</span>
                            )}
                            <span style={{ fontSize: '0.8em' }}>{showCategoryDropdown ? '▲' : '▼'}</span>
                        </span>
                    </button>

                    {showCategoryDropdown && (
                        <>
                            <div
                                style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 9998, background: 'transparent' }}
                                onClick={() => { setShowCategoryDropdown(false); setCategorySearch('') }}
                            />
                            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, minWidth: '350px', background: 'white', border: '1px solid #e5e7eb', borderRadius: '12px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)', zIndex: 9999, marginTop: '4px', maxHeight: '450px', overflowY: 'auto' }}>
                                {/* Search */}
                                <div style={{ padding: '12px', borderBottom: '1px solid #e5e7eb', position: 'sticky', top: 0, background: 'white', zIndex: 2 }}>
                                    <input
                                        type="text"
                                        placeholder="Kategori ara..."
                                        value={categorySearch}
                                        onChange={(e) => setCategorySearch(e.target.value)}
                                        style={{ width: '100%', padding: '10px 14px', border: '1px solid #e5e7eb', borderRadius: '8px', outline: 'none', fontSize: '0.9em' }}
                                        autoFocus
                                    />
                                </div>

                                {/* Tümünü Seç Checkbox */}
                                <div
                                    onClick={() => {
                                        const allCats = Object.keys(categoryHierarchy)
                                        if (selectedCategories.length === allCats.length) {
                                            setSelectedCategories([])
                                        } else {
                                            setSelectedCategories(allCats)
                                        }
                                        setSelectedProducts([])
                                    }}
                                    style={{
                                        padding: '12px 16px',
                                        cursor: 'pointer',
                                        fontWeight: 600,
                                        borderBottom: '2px solid #e5e7eb',
                                        color: '#4f46e5',
                                        background: selectedCategories.length === Object.keys(categoryHierarchy).length ? '#eef2ff' : 'white',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px'
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedCategories.length === Object.keys(categoryHierarchy).length && Object.keys(categoryHierarchy).length > 0}
                                        onChange={() => {}}
                                        style={{ width: '18px', height: '18px', accentColor: '#4f46e5' }}
                                    />
                                    <span> Tümünü Seç ({Object.keys(categoryHierarchy).length})</span>
                                </div>

                                {/* Seçimi Temizle */}
                                {selectedCategories.length > 0 && (
                                    <div
                                        onClick={() => { setSelectedCategories([]); setSelectedProducts([]); }}
                                        style={{
                                            padding: '10px 16px',
                                            cursor: 'pointer',
                                            fontWeight: 500,
                                            borderBottom: '1px solid #f3f4f6',
                                            color: '#ef4444',
                                            background: '#fef2f2',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            fontSize: '0.9em'
                                        }}
                                    >
                                        <span>✕</span>
                                        <span>Seçimi Temizle ({selectedCategories.length} seçili)</span>
                                    </div>
                                )}

                                {/* Arama sonuçları veya hiyerarşik liste */}
                                {categorySearch.trim().length > 0 ? (
                                    // Arama modu - düz liste with checkboxes
                                    flatCategoriesList.filter(n => normalizeTurkish(n).includes(normalizeTurkish(categorySearch))).map((cat) => (
                                        <div
                                            key={cat}
                                            onClick={() => {
                                                setSelectedCategories(prev =>
                                                    prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
                                                )
                                                setSelectedProducts([])
                                            }}
                                            style={{
                                                padding: '10px 16px',
                                                cursor: 'pointer',
                                                borderBottom: '1px solid #f9fafb',
                                                fontSize: '0.9em',
                                                background: selectedCategories.includes(cat) ? '#eef2ff' : 'white',
                                                color: selectedCategories.includes(cat) ? '#4f46e5' : '#374151',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '10px'
                                            }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedCategories.includes(cat)}
                                                onChange={() => {}}
                                                style={{ width: '16px', height: '16px', accentColor: '#4f46e5' }}
                                            />
                                            {cat}
                                        </div>
                                    ))
                                ) : (
                                    // Hiyerarşik mod - Ana Kategori -> Alt1 -> Alt2 with checkboxes
                                    Object.keys(categoryHierarchy).sort((a, b) => a.localeCompare(b, 'tr')).map((anaKat) => {
                                        const isAnaExpanded = expandedAnaKat.has(anaKat)
                                        const alt1Data = categoryHierarchy[anaKat] || {}
                                        const hasChildren = Object.keys(alt1Data).length > 0
                                        const isSelected = selectedCategories.includes(anaKat)

                                        return (
                                            <div key={anaKat}>
                                                {/* Ana Kategori */}
                                                <div
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        padding: '12px 16px',
                                                        cursor: 'pointer',
                                                        borderBottom: '1px solid #f3f4f6',
                                                        background: isSelected ? '#eef2ff' : 'white',
                                                        fontWeight: 600,
                                                        fontSize: '0.95em',
                                                        color: isSelected ? '#4f46e5' : '#1f2937'
                                                    }}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={isSelected}
                                                        onChange={() => {
                                                            setSelectedCategories(prev =>
                                                                prev.includes(anaKat) ? prev.filter(c => c !== anaKat) : [...prev, anaKat]
                                                            )
                                                            setSelectedProducts([])
                                                        }}
                                                        onClick={(e) => e.stopPropagation()}
                                                        style={{ width: '16px', height: '16px', accentColor: '#4f46e5', marginRight: '10px' }}
                                                    />
                                                    {hasChildren && (
                                                        <span
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                setExpandedAnaKat(prev => {
                                                                    const next = new Set(prev)
                                                                    if (next.has(anaKat)) next.delete(anaKat)
                                                                    else next.add(anaKat)
                                                                    return next
                                                                })
                                                            }}
                                                            style={{ marginRight: '8px', color: '#9ca3af', fontSize: '0.8em', width: '16px' }}
                                                        >
                                                            {isAnaExpanded ? '▼' : '▶'}
                                                        </span>
                                                    )}
                                                    {!hasChildren && <span style={{ width: '24px' }} />}
                                                    <span
                                                        onClick={() => {
                                                            setSelectedCategories(prev =>
                                                                prev.includes(anaKat) ? prev.filter(c => c !== anaKat) : [...prev, anaKat]
                                                            )
                                                            setSelectedProducts([])
                                                        }}
                                                        style={{ flex: 1 }}
                                                    >
                                                         {anaKat}
                                                    </span>
                                                </div>

                                                {/* Alt Kategori 1 */}
                                                {isAnaExpanded && Object.keys(alt1Data).sort((a, b) => a.localeCompare(b, 'tr')).map((alt1) => {
                                                    const isAlt1Expanded = expandedAltKat1.has(`${anaKat}:${alt1}`)
                                                    const alt2List = alt1Data[alt1] || []
                                                    const hasAlt2 = Array.isArray(alt2List) && alt2List.length > 0
                                                    const isAlt1Selected = selectedCategories.includes(alt1)

                                                    return (
                                                        <div key={`${anaKat}:${alt1}`}>
                                                            <div
                                                                style={{
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    padding: '10px 16px 10px 40px',
                                                                    cursor: 'pointer',
                                                                    borderBottom: '1px solid #f9fafb',
                                                                    background: isAlt1Selected ? '#fef3c7' : '#fafafa',
                                                                    fontSize: '0.9em',
                                                                    color: isAlt1Selected ? '#d97706' : '#4b5563'
                                                                }}
                                                            >
                                                                <input
                                                                    type="checkbox"
                                                                    checked={isAlt1Selected}
                                                                    onChange={() => {
                                                                        setSelectedCategories(prev =>
                                                                            prev.includes(alt1) ? prev.filter(c => c !== alt1) : [...prev, alt1]
                                                                        )
                                                                        setSelectedProducts([])
                                                                    }}
                                                                    onClick={(e) => e.stopPropagation()}
                                                                    style={{ width: '14px', height: '14px', accentColor: '#d97706', marginRight: '8px' }}
                                                                />
                                                                {hasAlt2 && (
                                                                    <span
                                                                        onClick={(e) => {
                                                                            e.stopPropagation()
                                                                            setExpandedAltKat1(prev => {
                                                                                const next = new Set(prev)
                                                                                const key = `${anaKat}:${alt1}`
                                                                                if (next.has(key)) next.delete(key)
                                                                                else next.add(key)
                                                                                return next
                                                                            })
                                                                        }}
                                                                        style={{ marginRight: '8px', color: '#9ca3af', fontSize: '0.75em', width: '14px' }}
                                                                    >
                                                                        {isAlt1Expanded ? '▼' : '▶'}
                                                                    </span>
                                                                )}
                                                                {!hasAlt2 && <span style={{ width: '22px' }} />}
                                                                <span
                                                                    onClick={() => {
                                                                        setSelectedCategories(prev =>
                                                                            prev.includes(alt1) ? prev.filter(c => c !== alt1) : [...prev, alt1]
                                                                        )
                                                                        setSelectedProducts([])
                                                                    }}
                                                                    style={{ flex: 1 }}
                                                                >
                                                                     {alt1}
                                                                </span>
                                                            </div>

                                                            {/* Alt Kategori 2 */}
                                                            {isAlt1Expanded && hasAlt2 && alt2List.map((alt2: string) => {
                                                                const isAlt2Selected = selectedCategories.includes(alt2)
                                                                return (
                                                                    <div
                                                                        key={`${anaKat}:${alt1}:${alt2}`}
                                                                        onClick={() => {
                                                                            setSelectedCategories(prev =>
                                                                                prev.includes(alt2) ? prev.filter(c => c !== alt2) : [...prev, alt2]
                                                                            )
                                                                            setSelectedProducts([])
                                                                        }}
                                                                        style={{
                                                                            padding: '8px 16px 8px 70px',
                                                                            cursor: 'pointer',
                                                                            borderBottom: '1px solid #fafafa',
                                                                            background: isAlt2Selected ? '#dcfce7' : 'white',
                                                                            fontSize: '0.85em',
                                                                            color: isAlt2Selected ? '#16a34a' : '#6b7280',
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: '8px'
                                                                        }}
                                                                    >
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={isAlt2Selected}
                                                                            onChange={() => {}}
                                                                            onClick={(e) => e.stopPropagation()}
                                                                            style={{ width: '14px', height: '14px', accentColor: '#16a34a' }}
                                                                        />
                                                                         {alt2}
                                                                    </div>
                                                                )
                                                            })}
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )
                                    })
                                )}
                            </div>
                        </>
                    )}
                </div>

                {/* 2. Marka Dropdown */}
                <div style={{ flex: '1 1 200px', minWidth: '200px', position: 'relative' }}>
                    <button
                        onClick={() => {
                            const next = !showBrandDropdown
                            setShowBrandDropdown(next)
                            if (next) {
                                setBrandSearch('')
                                setShowCategoryDropdown(false)
                            }
                        }}
                        style={{
                            width: '100%',
                            padding: '10px 16px',
                            fontSize: '0.95em',
                            border: '1px solid #d1d5db',
                            borderRadius: '8px',
                            background: 'white',
                            textAlign: 'left',
                            cursor: 'pointer',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            color: selectedBrand ? '#4f46e5' : '#374151',
                            fontWeight: selectedBrand ? 600 : 400
                        }}
                    >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {selectedBrand || 'Tüm Markalar'}
                        </span>
                        <span style={{ fontSize: '0.8em', marginLeft: '8px' }}>▼</span>
                    </button>
                    
                    {showBrandDropdown && (
                        <>
                            <div 
                                style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 9998, background: 'transparent' }}
                                onClick={() => { setShowBrandDropdown(false); setBrandSearch('') }}
                            />
                            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px', boxShadow: '0 10px 30px rgba(0,0,0,0.15)', zIndex: 9999, marginTop: '4px', maxHeight: '400px', overflowY: 'auto' }}>
                                <div style={{ padding: '8px', borderBottom: '1px solid #e5e7eb', position: 'sticky', top: 0, background: 'white', zIndex: 2 }}>
                                    <input type="text" placeholder="Marka ara..." value={brandSearch} onChange={(e) => setBrandSearch(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '6px', outline: 'none', fontSize: '0.9em' }} />
                                </div>
                                <div onClick={() => { setSelectedBrand(''); setShowBrandDropdown(false); }} style={{ padding: '10px 16px', cursor: 'pointer', fontWeight: 600, borderBottom: '1px solid #f3f4f6', color: '#4f46e5' }}>Tüm Markalar</div>
                                {(brandSearch.trim().length > 0 ? 
                                    brandsList.filter(n => normalizeTurkish(n).includes(normalizeTurkish(brandSearch))) : 
                                    brandsList
                                 ).map((brand) => (
                                    <div key={brand} onClick={() => { setSelectedBrand(brand); setShowBrandDropdown(false); }} style={{ padding: '10px 16px', cursor: 'pointer', borderBottom: '1px solid #f9fafb', fontSize: '0.95em' }}>
                                        {brand}
                                    </div>
                                 ))}
                            </div>
                        </>
                    )}
                </div>

                 {/* 3. Search Box */}
                 <div style={{ flex: '2 1 300px', position: 'relative' }}>
                    <div style={{ position: 'relative' }}>
                        <input
                            type="text"
                            placeholder="Ürün adı, stok kodu ara..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            style={{ width: '100%', padding: '10px 16px', paddingLeft: '40px', paddingRight: '40px', fontSize: '0.95em', border: '1px solid #d1d5db', borderRadius: '8px', transition: 'all 0.2s', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
                        />
                         <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }}>
                            <IconSearch size={18} />
                        </div>
                         <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {searchLoading ? <InlineSpinner size={18} thickness={2} /> : searchTerm.length > 0 && (
                                <IconX size={18} style={{ cursor: 'pointer' }} onClick={() => setSearchTerm('')} />
                            )}
                        </div>
                    </div>
                    {/* Search Results Dropdown - Modern Design */}
                    {searchTerm.length >= 2 && (
                        <div className="search-results-dropdown" style={{ maxHeight: '420px', overflowY: 'auto' }}>
                            {/* Header */}
                            <div className="search-results-header">
                                <span className="title">
                                    {searchLoading ? 'Aranıyor...' : 'Arama Sonuçları'}
                                </span>
                                <span className="count">
                                    {searchResults.length} ürün bulundu
                                </span>
                            </div>

                            {/* Results */}
                            {searchResults.length > 0 ? (
                                searchResults.map((result, idx) => (
                                    <div
                                        key={idx}
                                        className={`search-result-item ${selectedProducts.includes(result.name) ? 'selected' : ''}`}
                                        onClick={() => result.id ? openProductPortal(result.id, result.name) : dispatch({ type: 'TOGGLE_PRODUCT', payload: result.name })}
                                    >
                                        <div className="result-info">
                                            <div className="result-name">{result.name}</div>
                                            <div className="result-meta">{result.category} • {result.brand}</div>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            {result.id && (
                                                <IconPlayerPlay 
                                                  size={14} 
                                                  title="Urun Portali"
                                                  style={{ padding: '4px', borderRadius: '6px', background: '#ede9fe', color: '#6366f1' }}
                                                />
                                            )}
                                            <div className="result-value">
                                                {result.sales.toLocaleString('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 })}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : !searchLoading ? (
                                <div className="search-no-results">
                                    <div className="icon"></div>
                                    <div className="text">"{searchTerm}" için sonuç bulunamadı</div>
                                </div>
                            ) : null}
                        </div>
                    )}
                 </div>
             </div>

        {/* Filter Loading Progress Bar */}
        {filterLoading && (
          <div style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            background: 'white',
            padding: '8px 0',
            marginBottom: '8px',
            borderRadius: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <div className="inline-spinner" style={{ width: '18px', height: '18px' }} />
              <span style={{ color: '#4f46e5', fontWeight: 500, fontSize: '0.9rem' }}>Filtre uygulanıyor...</span>
            </div>
            <div className="progress-bar-indeterminate" />
          </div>
        )}

        {/* Global KPI Stats */}
        {currentStats && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: '20px',
            opacity: filterLoading ? 0.6 : 1,
            transition: 'opacity 0.2s',
            pointerEvents: filterLoading ? 'none' : 'auto'
          }}>
            <KpiCard {...KPI_COLORS.indigo} label="Toplam Ciro" value={currentStats?.totalRevenue?.toLocaleString('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }) || '0 ₺'} icon={<IconCurrencyLira size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.green} label="Ürün Çeşidi" value={currentStats?.totalProducts?.toLocaleString('tr-TR') || '0'} sub="Satışı olan ürünler" icon={<IconBox size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.amber} label="Toplam Satış Adedi" value={currentStats?.totalQuantity?.toLocaleString('tr-TR') || '0'} sub="Toplam adet satıldı" icon={<IconTag size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.blue} label="Ort. Ürün Fiyatı" value={currentStats?.averageProductPrice?.toLocaleString('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }) || '0 ₺'} sub="Satılan ürün ortalaması" icon={<IconReceipt size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.indigo} label="Marka Sayısı" value={currentStats.totalBrands.toLocaleString('tr-TR')} sub="Farklı marka" icon={<IconBuildingStore size={80} stroke={1.2} />} />
          </div>
        )}

        {/* Charts - Modern Design */}
        {currentStats && (
           <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
              {/* Satış Trendi */}
              <div style={{
                background: 'white',
                borderRadius: '16px',
                padding: '24px',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                height: '360px',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
              }}>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px', color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <IconTrendingUp size={24} color="#6366f1" />
                    Satış Trendi
                  </h3>
                  <div style={{ flex: 1, minHeight: 0 }}>
                    <RevenueChart 
                        data={!isShortDateRange ? aggregatedMonthlyData : []} 
                        dailyData={isShortDateRange ? currentStats.salesByMonth.map(item => ({
                            date: item.month, // Backend 'month' key holds the date string (YYYY-MM-DD)
                            sales: item.sales
                        })) : undefined}
                        title="Satış Trendi" 
                        height="280px" 
                    />
                  </div>
              </div>
              {/* En Çok Satan Ürünler */}
              <div style={{
                background: 'white',
                borderRadius: '12px',
                padding: '20px',
                boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
                display: 'flex',
                flexDirection: 'column',
                height: '560px'
              }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: 600, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <IconTrophy size={20} color="#f59e0b" />
                    En Çok Satan Ürünler
                  </h3>
                  <div style={{ flex: 1, overflowY: 'auto' }}>
                      {currentStats.topProducts.length === 0 ? (
                        <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>
                          <div style={{ fontSize: '2rem', marginBottom: '8px' }}><IconBox size={40} stroke={1.2} /></div>
                          <div>Ürün verisi bulunamadı</div>
                        </div>
                      ) : (
                        (() => {
                          const maxSales = Math.max(...currentStats.topProducts.slice(0, 10).map(p => p.sales))
                          return currentStats.topProducts.slice(0, 10).map((p, i) => {
                            const percentage = (p.sales / maxSales) * 100
                            const colors = ['#667eea', '#11998e', '#f093fb', '#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4']
                            const color = colors[i % colors.length]
                            return (
                              <div key={i} style={{
                                padding: '16px',
                                borderRadius: '12px',
                                marginBottom: '12px',
                                border: `2px solid ${color}40`,
                                background: i < 3 ? `${color}10` : 'white',
                                transition: 'all 0.2s ease',
                                cursor: 'pointer'
                              }}
                              onClick={() => openProductPortal(p.id, p.name)}
                              onMouseEnter={(e) => { e.currentTarget.style.borderColor = color; e.currentTarget.style.transform = 'translateX(4px)' }}
                              onMouseLeave={(e) => { e.currentTarget.style.borderColor = color + '40'; e.currentTarget.style.transform = 'translateX(0)' }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                                  <div style={{
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '50%',
                                    background: color,
                                    color: 'white',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 'bold',
                                    fontSize: '0.9rem'
                                  }}>
                                    {i < 3 ? ['🥇', '🥈', '🥉'][i] : i + 1}
                                  </div>
                                  <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                      <div style={{ 
                                        fontWeight: 600, 
                                        fontSize: '0.95rem', 
                                        whiteSpace: 'nowrap', 
                                        overflow: 'hidden', 
                                        textOverflow: 'ellipsis',
                                        color: '#1f2937'
                                      }} title={p.name}>{p.name}</div>
                                      
                                      {/* Performance Badges */}
                                      {p.perf_kat === 'Yildiz' && <span style={{ padding: '2px 6px', borderRadius: '4px', background: '#fef3c7', color: '#d97706', fontSize: '0.65rem', fontWeight: 700 }}> YILDIZ</span>}
                                      {p.stok_durumu === 'Kritik' && <span style={{ padding: '2px 6px', borderRadius: '4px', background: '#fee2e2', color: '#ef4444', fontSize: '0.65rem', fontWeight: 700 }}> STOK</span>}
                                      
                                      {/* Kategori Pazar Payı */}
                                      {p.kat_payi !== undefined && (
                                        <span style={{ padding: '2px 6px', borderRadius: '4px', background: '#f1f5f9', color: '#475569', fontSize: '0.65rem', fontWeight: 700, border: '1px solid #e2e8f0' }}>
                                          %{formatPercent(p.kat_payi)} KAT. PAYI
                                        </span>
                                      )}

                                      {p.trend === 'Hizlaniyor' && <span style={{ color: '#10b981', fontSize: '0.8rem' }} title="Hızlanıyor"></span>}
                                      {p.trend === 'Yavasliyor' && <span style={{ color: '#ef4444', fontSize: '0.8rem' }} title="Yavaşlıyor"></span>}
                                    </div>
                                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{p.brand} • {p.category}</div>
                                  </div>

                                  {/* Middle Stats Area */}
                                  <div style={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    gap: '15px',
                                    padding: '0 20px',
                                    color: '#4b5563',
                                    fontSize: '0.85rem'
                                  }}>
                                    <div title="Müşteri Sayısı" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                                      <span style={{ fontSize: '1rem' }}></span>
                                      <span style={{ fontWeight: 600 }}>{p.customerCount?.toLocaleString('tr-TR')}</span>
                                      <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>Müşteri</span>
                                    </div>
                                    <div title="Toplam Adet" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                                      <span style={{ fontSize: '1rem' }}></span>
                                      <span style={{ fontWeight: 600 }}>{p.count?.toLocaleString('tr-TR')}</span>
                                      <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>Adet</span>
                                    </div>
                                  </div>

                                  <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontWeight: 700, color: color, fontSize: '1.2rem', lineHeight: 1 }}>
                                      {p.sales.toLocaleString('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 })}
                                    </div>
                                  </div>
                                </div>
                                {/* Progress bar */}
                                <div style={{
                                  height: '6px',
                                  background: '#f3f4f6',
                                  borderRadius: '3px',
                                  overflow: 'hidden'
                                }}>
                                  <div style={{
                                    height: '100%',
                                    width: `${percentage}%`,
                                    background: color,
                                    transition: 'width 0.3s'
                                  }} />
                                </div>
                              </div>
                            )
                          })
                        })()
                      )}
                  </div>
              </div>
           </div>
        )}



        {/* Tüm Markalar Sıralaması - Her zaman görünür */}
        {currentStats && currentStats.topBrands && currentStats.topBrands.length > 0 && (
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
          }}>
            <h3 style={{ marginBottom: '16px', fontSize: '1.1rem', fontWeight: 600, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <IconBuildingStore size={22} color="#4f46e5" />
              <span> Marka Bazlı Satış Sıralaması</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 400, color: '#6b7280' }}>({currentStats.topBrands.length} marka)</span>
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: '#374151' }}>#</th>
                    <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: '#374151' }}>Marka</th>
                    <th style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 600, color: '#374151' }}>Satış</th>
                    <th style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 600, color: '#374151' }}>Pay</th>
                    <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 600, color: '#374151', minWidth: '200px' }}>Grafik</th>
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const totalSales = currentStats.topBrands.reduce((sum, b) => sum + b.sales, 0)
                    const maxSales = currentStats.topBrands[0]?.sales || 1
                    const colors = ['#667eea', '#11998e', '#f093fb', '#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4']

                    return currentStats.topBrands.map((brand, idx) => {
                      const percentage = (brand.sales / maxSales) * 100
                      const sharePercentage = totalSales > 0 ? (brand.sales / totalSales) * 100 : 0
                      const color = colors[idx % colors.length]
                      const isSelected = selectedBrand === brand.name

                      return (
                        <tr
                          key={brand.name}
                          onClick={() => setSelectedBrand(isSelected ? '' : brand.name)}
                          style={{
                            borderBottom: '1px solid #f3f4f6',
                            cursor: 'pointer',
                            background: isSelected ? `${color}10` : (idx % 2 === 0 ? 'white' : '#fafafa'),
                            transition: 'background 0.2s'
                          }}
                          onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = '#f0f9ff' }}
                          onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = idx % 2 === 0 ? 'white' : '#fafafa' }}
                        >
                          <td style={{ padding: '12px 8px' }}>
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: '28px',
                              height: '28px',
                              borderRadius: '50%',
                              background: idx < 3 ? color : '#e5e7eb',
                              color: idx < 3 ? 'white' : '#6b7280',
                              fontWeight: 600,
                              fontSize: '0.8rem'
                            }}>
                              {idx < 3 ? ['🥇', '🥈', '🥉'][idx] : idx + 1}
                            </span>
                          </td>
                          <td style={{ padding: '12px 8px', fontWeight: isSelected ? 600 : 500, color: isSelected ? color : '#1f2937' }}>
                            {brand.name}
                          </td>
                          <td style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 600, color: color }}>
                            {brand.sales.toLocaleString('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 })}
                          </td>
                          <td style={{ padding: '12px 8px', textAlign: 'right', color: '#6b7280' }}>
                            %{formatPercent(sharePercentage)}
                          </td>
                          <td style={{ padding: '12px 8px' }}>
                            <div style={{
                              height: '8px',
                              background: '#f3f4f6',
                              borderRadius: '4px',
                              overflow: 'hidden'
                            }}>
                              <div style={{
                                height: '100%',
                                width: `${percentage}%`,
                                background: color,
                                transition: 'width 0.3s',
                                borderRadius: '4px'
                              }} />
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  })()}
                </tbody>
              </table>
            </div>
          </div>
        )}


      </div>
      </div>
    </LoadingOverlay>
      </div>

    <ProductPortal
      isOpen={isPortalOpen}
      onClose={() => setIsPortalOpen(false)}
      productId={portalProductId || 0}
      productName={portalProductName}
    />
    </>
  )
}