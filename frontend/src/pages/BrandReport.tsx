import { useState, useEffect, useMemo, useRef } from 'react'
import { 
  IconBriefcase, IconTrendingUp, IconCurrencyDollar,
  IconChartBar, IconChevronDown, IconChevronRight, IconSearch,
  IconX, IconCheck, IconPackage,
  IconAlertCircle
} from '@tabler/icons-react'
import { Alert } from '@mantine/core'
import apiClient from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'
import useDashboardStore from '../stores/dashboardStore'
import useUIStore from '../stores/uiStore'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import BrandPortal from '../components/BrandPortal'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/DashboardHome.css'

interface BrandData {
  topBrands: { name: string; sales: number; units: number; customers: number; avgPrice: number; growth: number; marketShare: number; color: string }[]
  brandPerformance: { 
    totalBrands: number; 
    activeBrands: number; 
    topPerformers: number; 
    declining: number;
    totalSales: number;
  }
  categoryDistribution: { category: string; brands: number; sales: number; topBrand: string }[]
  categoryHierarchy?: any
}

const emptyData: BrandData = {
  topBrands: [],
  brandPerformance: { totalBrands: 0, activeBrands: 0, topPerformers: 0, declining: 0, totalSales: 0 },
  categoryDistribution: [],
  categoryHierarchy: {}
}

const brandColors = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', '#f97316', '#ef4444', '#06b6d4', '#84cc16']

export default function BrandReport() {
  const { 
    selectedDataSourceId, 
    selectedYear, 
    selectedMonth, 
    selectedStartDate, 
    selectedEndDate,
    selectedRegion,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedSegments,
    selectedCategories,
    setSelectedCategories
  } = useDashboardStore()

  const [initialLoading, setInitialLoading] = useState(true)
  const [filterLoading, setFilterLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<BrandData>(emptyData)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  
  // Brand Portal State
  const [selectedBrandForPortal, setSelectedBrandForPortal] = useState<string | null>(null)
  const [isPortalOpen, setIsPortalOpen] = useState(false)

  // Category Search & Brand Search State
  const [categoryHierarchy, setCategoryHierarchy] = useState<any>({})
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false)
  const [brandSearch, setBrandSearch] = useState('')
  const [debouncedBrandSearch, setDebouncedBrandSearch] = useState('')
  const [brandSuggestions, setBrandSuggestions] = useState<string[]>([])
  const [showBrandSuggestions, setShowBrandSuggestions] = useState(false)
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set())

  const pageSize = 10
  const filterDebounceRef = useRef<NodeJS.Timeout | null>(null)
  const brandSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const openBrandPortal = (name: string) => {
    setSelectedBrandForPortal(name)
    setIsPortalOpen(true)
  }

  // Fetch Brand Suggestions
  useEffect(() => {
    const fetchSuggestions = async () => {
        if (!selectedDataSourceId || brandSearch.length < 1) {
            setBrandSuggestions([])
            setShowBrandSuggestions(false)
            return
        }
        
        try {
            const suggestions = await apiClient.getBrandSuggestions(selectedDataSourceId, brandSearch)
            setBrandSuggestions(suggestions || [])
            setShowBrandSuggestions((suggestions || []).length > 0)
        } catch (error: any) {
            if (!error.message?.includes('Network Error')) {
              console.error('Error fetching brand suggestions:', error)
            }
        }
    }

    const timer = setTimeout(fetchSuggestions, 300)
    return () => clearTimeout(timer)
  }, [brandSearch, selectedDataSourceId])

  // Debounce Brand Search - Arttırılmış süre (performans için)
  useEffect(() => {
    if (brandSearchTimeoutRef.current) clearTimeout(brandSearchTimeoutRef.current)
    brandSearchTimeoutRef.current = setTimeout(() => {
        setDebouncedBrandSearch(brandSearch)
    }, 800) // 500ms -> 800ms
    return () => { if (brandSearchTimeoutRef.current) clearTimeout(brandSearchTimeoutRef.current) }
  }, [brandSearch])

  // Load Data Trigger
  useEffect(() => {
    if (selectedDataSourceId) {
      if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current)
      
      const isInitial = !data.topBrands.length
      if (isInitial) setInitialLoading(true)
      else setFilterLoading(true)

      filterDebounceRef.current = setTimeout(() => {
        setPage(1)
        setHasMore(true)
        loadData(true, 1)
      }, 300)
    }
    return () => { if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current) }
  }, [selectedDataSourceId, selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedRegion, selectedCustomerType, selectedApprovalStatus, selectedCategories, debouncedBrandSearch])

  const loadData = async (reset: boolean, pageNum: number) => {
    if (!selectedDataSourceId) {
      setInitialLoading(false)
      setFilterLoading(false)
      return
    }
    
    try {
      const filters: any = {
        year: selectedYear,
        month: selectedMonth,
        start_date: selectedStartDate,
        end_date: selectedEndDate,
        region: selectedRegion,
        customer_type: selectedCustomerType,
        approval_status: selectedApprovalStatus,
        segment: (selectedSegments && selectedSegments.length > 0) ? selectedSegments[0] : undefined,
        category: selectedCategories,
        brand_search: debouncedBrandSearch,
        page: pageNum,
        limit: pageSize
      }

      // Timeout handling - 130 saniye (backend'den daha uzun sürebilir)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 130000) // 130 saniye
      
      try {
        const result = await apiClient.getBrandReport(selectedDataSourceId, filters)
        clearTimeout(timeoutId)
      
        if (result.categoryHierarchy) {
          setCategoryHierarchy(result.categoryHierarchy)
        }
      
      // Update Global Filters if available in response
      if (result.availableRegions && result.availableRegions.length > 0) {
          useDashboardStore.getState().setAvailableRegions(result.availableRegions)
      }
      if (result.availableCustomerTypes && result.availableCustomerTypes.length > 0) {
          useDashboardStore.getState().setAvailableCustomerTypes(result.availableCustomerTypes)
      }
      if (result.availableApprovalStatuses && result.availableApprovalStatuses.length > 0) {
          useDashboardStore.getState().setAvailableApprovalStatuses(result.availableApprovalStatuses)
      }

      const newBrands = (result.topBrands || []).map((b: any, idx: number) => ({
        ...b,
        color: brandColors[( (pageNum - 1) * pageSize + idx) % brandColors.length]
      }))

      if (reset || pageNum === 1) {
        setData(result)
      } else {
        setData(prev => ({
          ...result,
          topBrands: [...prev.topBrands, ...newBrands]
        }))
      }
      setHasMore(newBrands.length === pageSize)
    } catch (err: any) {
      if (!err.message?.includes('Network Error')) {
        console.error(err)
        notifications.show({
          title: 'Hata',
          message: 'Marka raporu yüklenirken bir hata oluştu.',
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
        setError('Hata oluştu.')
      }
      if (pageNum === 1) setData(emptyData)
    } finally {
      setInitialLoading(false)
      setFilterLoading(false)
    }
  } catch (err: any) {
    console.error('loadData error:', err)
  }
  }

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (data && data.topBrands.length > 0) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Marka Raporu', {
        page: 'brand_report',
        data_source_id: selectedDataSourceId,
        performance: data.brandPerformance,
        top_brands_count: data.topBrands.length,
        selected_categories: selectedCategories
      });
    }
  }, [data, selectedDataSourceId, selectedCategories]);

  const loadMoreBrands = () => {
    if (filterLoading || !hasMore) return
    const nextPage = page + 1
    setPage(nextPage)
    loadData(false, nextPage)
  }

  const toggleCategory = (cat: string) => {
    const nextCategories = selectedCategories.includes(cat)
      ? selectedCategories.filter(c => c !== cat)
      : [...selectedCategories, cat];
    setSelectedCategories(nextCategories);
  }

  const toggleExpand = (cat: string, e: React.MouseEvent) => {
      e.stopPropagation()
      setExpandedCats(prev => {
          const next = new Set(prev)
          if (next.has(cat)) next.delete(cat)
          else next.add(cat)
          return next
      })
  }

  const renderCategoryTree = (nodes: any, level = 0) => {
      return Object.keys(nodes).sort().map(key => {
          const children = nodes[key]
          const isExpandable = children && (Array.isArray(children) ? children.length > 0 : Object.keys(children).length > 0)
          const isExpanded = expandedCats.has(key)
          const isSelected = selectedCategories.includes(key)
          
          return (
              <div key={key} style={{ marginLeft: level * 12 }}>
                  <div 
                      onClick={() => toggleCategory(key)}
                      style={{
                          padding: '6px 8px', borderRadius: '6px', cursor: 'pointer',
                          background: isSelected ? '#eff6ff' : 'transparent',
                          color: isSelected ? '#2563eb' : '#374151',
                          display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9em'
                      }}
                      onMouseOver={e => !isSelected && (e.currentTarget.style.background = '#f9fafb')}
                      onMouseOut={e => !isSelected && (e.currentTarget.style.background = 'transparent')}
                  >
                        {isExpandable && (
                           <span 
                               onClick={(e) => toggleExpand(key, e)}
                               style={{ fontSize: '0.7em', width: '12px', cursor: 'pointer', color: '#9ca3af', display: 'flex', alignItems: 'center' }}
                           >
                               {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
                           </span>
                        )}
                        {!isExpandable && <span style={{ width: '12px' }} />}
                        
                        <div style={{
                            width: '14px', height: '14px', borderRadius: '4px',
                            border: isSelected ? 'none' : '2px solid #d1d5db',
                            background: isSelected ? '#2563eb' : 'white',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '10px'
                        }}>
                            {isSelected && <IconCheck size={10} stroke={4} />}
                        </div>
                        {key}
                  </div>
                  {isExpandable && isExpanded && (
                      <div style={{ borderLeft: '1px solid #e5e7eb', marginLeft: '6px' }}>
                          {Array.isArray(children) 
                              ? children.map(child => (
                                  <div key={child} style={{ marginLeft: (level + 1) * 12 + 6 }}>
                                    <div 
                                        onClick={() => toggleCategory(child)}
                                        style={{
                                            padding: '4px 8px', borderRadius: '4px', cursor: 'pointer',
                                            background: selectedCategories.includes(child) ? '#eff6ff' : 'transparent',
                                            color: selectedCategories.includes(child) ? '#2563eb' : '#4b5563',
                                            display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85em'
                                        }}
                                    >
                                        <div style={{ width: '12px' }} />
                                        <div style={{
                                            width: '12px', height: '12px', borderRadius: '3px',
                                            border: selectedCategories.includes(child) ? 'none' : '1px solid #d1d5db',
                                            background: selectedCategories.includes(child) ? '#2563eb' : 'white',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '8px'
                                        }}>
                                            {selectedCategories.includes(child) && <IconCheck size={8} stroke={4} />}
                                        </div>
                                        {child}
                                    </div>
                                  </div>
                              ))
                              : renderCategoryTree(children, level + 1)
                          }
                      </div>
                  )}
              </div>
          )
      })
  }

  const hasData = data.topBrands && data.topBrands.length > 0

  const topBrandsWithStableColors = useMemo(() => {
     return (data.topBrands || []).map((b, idx) => ({
       ...b,
       color: brandColors[idx % brandColors.length]
     }))
  }, [data.topBrands])

  if(!selectedDataSourceId) return <div className="products-page"><div className="empty-state">Veri kaynağı seçin</div></div>

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Marka Performans Raporu</h1>
        <AISummaryButton 
          contextType="marka_raporu" 
          contextId={selectedDataSourceId} 
          contextData={{ brand_count: data.brandPerformance?.totalBrands }}
        />
      </div>

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} title="Hata" color="red" mb="md" variant="light">
          {error}
        </Alert>
      )}

      {hasData && !initialLoading && (
        <div style={{ marginBottom: '24px' }}>
          <AIInsightCard 
            contextType="marka_raporu" 
            contextId={selectedDataSourceId.toString()} 
            title="Marka Analitik Yorumu"
            data={data}
          />
        </div>
      )}

      <LoadingOverlay loading={initialLoading || filterLoading}>
      {!hasData && !initialLoading ? (
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '60px',
          textAlign: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
        }}>
          <div style={{ marginBottom: '16px' }}><IconChartBar size={64} stroke={1.3} color="#9ca3af" /></div>
          <h2 style={{ color: '#374151', marginBottom: '8px' }}>Veri Bulunamadı</h2>
          <p style={{ color: '#6b7280' }}>
            Seçili filtreler için marka verisi bulunamadı.
          </p>
          <button onClick={() => { setSelectedCategories([]); setBrandSearch(''); }} style={{ marginTop: '16px', color: '#2563eb', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}>Filtreleri Temizle</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '24px' }}>
          {/* Performans Özeti */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
            <KpiCard {...KPI_COLORS.indigo} label="Toplam Marka" value={String(data.brandPerformance?.totalBrands || 0)} sub="Sistemdeki toplam marka" icon={<IconBriefcase size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.green}  label="Aktif Marka"  value={String(data.brandPerformance?.activeBrands || 0)} sub="Satışı olan markalar" icon={<IconTrendingUp size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.amber}  label="En İyi Performans" value={String(data.brandPerformance?.topPerformers || 0)} sub="Yüksek performanslı" icon={<IconPackage size={80} stroke={1.2} />} />
            <KpiCard {...KPI_COLORS.pink}   label="Toplam Satış" value={`₺${((data.brandPerformance?.totalSales || 0) / 1000000).toFixed(2)}M`} sub="Toplam marka cirosu" icon={<IconCurrencyDollar size={80} stroke={1.2} />} />
          </div>

          {/* En İyi Markalar - With Category Search & Brand Search */}
          <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}> En Çok Satan Markalar</h2>
                
                <div style={{ display: 'flex', gap: '12px' }}>
                    {/* Brand Search Input */}
                    <div style={{ position: 'relative' }}>
                        <IconSearch size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
                        <input
                            type="text"
                            placeholder="Marka Ara..."
                            value={brandSearch}
                            onChange={(e) => setBrandSearch(e.target.value)}
                            style={{
                                padding: '10px 14px',
                                paddingLeft: '36px',
                                paddingRight: '36px',
                                borderRadius: '8px',
                                border: '1px solid #e5e7eb',
                                width: '200px',
                                fontSize: '0.9em',
                                outline: 'none'
                            }}
                        />
                        {brandSearch && (
                            <button 
                                onClick={() => { setBrandSearch(''); setBrandSuggestions([]); setShowBrandSuggestions(false); }}
                                style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                            ><IconX size={16} /></button>
                        )}

                        {showBrandSuggestions && brandSuggestions.length > 0 && (
                            <div style={{
                                position: 'absolute', top: '105%', left: 0, width: '100%', minWidth: '220px',
                                background: 'white', border: '1px solid #e5e7eb',
                                borderRadius: '12px', boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                                zIndex: 30, padding: '4px', maxHeight: '300px', overflowY: 'auto'
                            }}>
                                {brandSuggestions.map((s, idx) => (
                                    <div 
                                        key={idx}
                                        onClick={() => {
                                            setBrandSearch(s)
                                            setBrandSuggestions([])
                                            setShowBrandSuggestions(false)
                                        }}
                                        style={{ 
                                            padding: '10px 14px', cursor: 'pointer', borderRadius: '8px',
                                            fontSize: '0.9em', transition: 'background 0.2s',
                                            borderBottom: idx === brandSuggestions.length - 1 ? 'none' : '1px solid #f3f4f6'
                                        }}
                                        onMouseOver={e => e.currentTarget.style.background = '#f3f4f6'}
                                        onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                                    >
                                        {s}
                                    </div>
                                ))}
                            </div>
                        )}
                        {showBrandSuggestions && <div style={{ position: 'fixed', inset: 0, zIndex: 25 }} onClick={() => setShowBrandSuggestions(false)} />}
                    </div>

                    {/* Hierarchical Category Dropdown */}
                    <div style={{ position: 'relative', width: '280px' }}>
                        <div 
                            onClick={() => setShowCategoryDropdown(!showCategoryDropdown)}
                            style={{
                                border: selectedCategories.length ? '2px solid #4f46e5' : '1px solid #e5e7eb',
                                borderRadius: '8px',
                                padding: '10px 16px',
                                cursor: 'pointer',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                background: showCategoryDropdown ? '#f9fafb' : 'white',
                                color: selectedCategories.length ? '#4f46e5' : '#374151',
                                fontWeight: selectedCategories.length ? 600 : 400
                            }}
                        >
                            <span>
                                {selectedCategories.length > 0 
                                    ? `${selectedCategories.length} Kategori Seçili` 
                                    : 'Tüm Kategoriler'}
                            </span>
                            <IconChevronDown size={14} />
                        </div>

                        {showCategoryDropdown && (
                             <>
                                <div style={{ position: 'fixed', inset: 0, zIndex: 10 }} onClick={() => setShowCategoryDropdown(false)} />
                                <div style={{
                                    position: 'absolute', top: '105%', right: 0, width: '100%', minWidth: '320px',
                                    background: 'white', border: '1px solid #e5e7eb',
                                    borderRadius: '12px', boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                                    zIndex: 20, padding: '12px', maxHeight: '450px', overflowY: 'auto'
                                }}>
                                    {selectedCategories.length > 0 && (
                                        <div 
                                            onClick={() => setSelectedCategories([])}
                                            style={{ padding: '8px', color: '#ef4444', fontSize: '0.9em', cursor: 'pointer', fontWeight: 600, borderBottom: '1px solid #f3f4f6', marginBottom: '8px', textAlign: 'right' }}
                                        >
                                            Seçimi Temizle
                                        </div>
                                    )}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                        {Object.keys(categoryHierarchy).length > 0 ? (
                                            renderCategoryTree(categoryHierarchy)
                                        ) : (
                                            <div style={{ padding: '12px', textAlign: 'center', color: '#9ca3af' }}>Yükleniyor...</div>
                                        )}
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gap: '12px' }}>
              {data.topBrands.map((brand, idx) => (
                <div 
                  key={idx} 
                  onClick={() => openBrandPortal(brand.name)}
                  style={{ 
                    padding: '16px 20px', 
                    borderRadius: '12px', 
                    background: `${brand.color}08`, 
                    border: `2px solid ${brand.color}20`, 
                    display: 'grid', 
                    gridTemplateColumns: '60px 1fr repeat(4, 120px)', 
                    alignItems: 'center', 
                    gap: '16px',
                    cursor: 'pointer',
                    transition: 'transform 0.2s, box-shadow 0.2s'
                  }}
                  onMouseOver={e => {
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
                  }}
                  onMouseOut={e => {
                    e.currentTarget.style.transform = 'none'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: brand.color }}>#{idx + 1}</div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{brand.name}</div>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Pazar Payı: %{brand.marketShare}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Satış</div>
                    <div style={{ fontWeight: 700 }}>₺{Math.round(brand.sales).toLocaleString('tr-TR')}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Adet</div>
                    <div style={{ fontWeight: 700 }}>{Math.round(brand.units).toLocaleString('tr-TR')}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Müşteri</div>
                    <div style={{ fontWeight: 700 }}>{(brand.customers || 0).toLocaleString('tr-TR')}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Ort. Fiyat</div>
                    <div style={{ fontWeight: 700 }}>₺{(brand.avgPrice || 0).toFixed(0)}</div>
                  </div>
                </div>
              ))}
            </div>

            {hasMore && (
              <button 
                onClick={loadMoreBrands}
                disabled={filterLoading}
                style={{ marginTop: '20px', width: '100%', padding: '12px', background: '#f3f4f6', border: 'none', borderRadius: '12px', color: '#4b5563', fontWeight: 600, cursor: filterLoading ? 'default' : 'pointer', transition: 'background 0.2s' }}
                onMouseOver={e => !filterLoading && (e.currentTarget.style.background = '#e5e7eb')}
                onMouseOut={e => !filterLoading && (e.currentTarget.style.background = '#f3f4f6')}
              >
                {filterLoading ? 'Yükleniyor...' : 'Daha Fazla Yükle'}
              </button>
            )}
          </div>

          {/* Pazar Payı Dağılımı */}
          <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
            <h2 style={{ marginBottom: '20px', fontSize: '1.25rem', fontWeight: 600 }}> Pazar Payı Dağılımı</h2>
            <div style={{ display: 'flex', height: '40px', borderRadius: '8px', overflow: 'hidden' }}>
              {topBrandsWithStableColors.slice(0, 5).map((brand, idx) => (
                <div key={idx} style={{ width: `${brand.marketShare}%`, background: brand.color, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 600, fontSize: '0.8rem', transition: 'width 0.5s' }} title={`${brand.name}: %${brand.marketShare}`}>
                  {brand.marketShare > 10 ? `${brand.name} %${brand.marketShare}` : ''}
                </div>
              ))}
              {topBrandsWithStableColors.length > 5 && (
                <div style={{ flex: 1, background: '#9ca3af', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 600, fontSize: '0.8rem' }}>Diğer</div>
              )}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '16px' }}>
              {topBrandsWithStableColors.slice(0, 5).map((brand, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: brand.color }} />
                  <span style={{ fontSize: '0.875rem' }}>{brand.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      </LoadingOverlay>

      {/* Brand Portal Modal */}
      {selectedBrandForPortal && (
        <BrandPortal 
          isOpen={isPortalOpen} 
          onClose={() => setIsPortalOpen(false)} 
          brandName={selectedBrandForPortal} 
        />
      )}
    </div>
  )
}
