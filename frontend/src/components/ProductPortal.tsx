import React, { useState, useEffect, useRef, useMemo, memo } from 'react'
import Modal from './Modal'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import * as echarts from 'echarts'
import { 
  IconCurrencyLira, IconPackage, IconReceipt, IconUsers, 
  IconShoppingCart, IconBuildingStore, 
  IconChartBar, IconScale, IconClock, IconCalendar,
  IconTarget
} from '@tabler/icons-react'

const formatNumber = (n: number) => new Intl.NumberFormat('tr-TR').format(n)
const formatCurrency = (n: number) => new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', maximumFractionDigits: 0 }).format(n)

interface ProductPortalProps {
  isOpen: boolean
  onClose: () => void
  productId: number
  productName: string
}

interface ProductPortalData {
  product: {
    id: number; kod: string; ad: string; marka: string; marka_id: number
    kategori: string; kategori_id: number; birim?: string
  }
  summary: {
    totalRevenue: number; totalUnits: number; totalReceipts: number
    totalCustomers: number; avgPrice: number; avgBasketSize: number
  }
  monthlyTrend: { month: string; revenue: number; units: number; receipts: number; avg_price?: number; avgPrice?: number }[]
  crossSell: { 
    PRODUCT: { productId: number; productName: string; brand: string; category?: string; coOccurrence: number; confidence: number; lift: number | null }[],
    BRAND_CAT: { productId: number; productName: string; brand: string; category?: string; coOccurrence: number; confidence: number; lift: number | null }[],
    CAT_ONLY: { productId: number; productName: string; brand: string; category?: string; coOccurrence: number; confidence: number; lift: number | null }[]
  }
  customerProfile: {
    byType: { type: string; count: number; revenue: number }[]
    bySegment: { segment: string; count: number; revenue: number }[]
    byApproval: { status: string; count: number; revenue: number }[]
  }
  storePerformance: { store_id: number; store_name: string; region: string; revenue: number; units: number; receipts: number }[]
  priceDistribution: { range_label: string; count: number }[]
  comparison: {
    product: { revenue: number; units: number; customers: number }
    categoryAvg: { revenue: number; units: number; customers: number }
    brandAvg: { revenue: number; units: number; customers: number }
  }
  timePatterns: {
    byHour: { hour: number; count: number; revenue: number }[]
    byDayOfWeek: { day: number; dayName: string; count: number; revenue: number }[]
  }
  performance?: any // Detailed performance from UrunPerformansDetay
  segmentPreferences?: {
    segment: string;
    index_score: number;
    penetration: number;
    buyer_count: number;
    preference: string;
    recommendation: string;
  }[]
  categoryPerformance?: any
}

const PERF_COLORS: Record<string, string> = {
  'Yildiz': '#8b5cf6', 'Populer': '#3b82f6', 'Orta': '#10b981', 'Dusuk': '#f59e0b', 'Durgun': '#ef4444'
}

const STOK_COLORS: Record<string, string> = {
  'Tukendi': '#ef4444', 'Kritik': '#f97316', 'Dusuk': '#f59e0b', 'Normal': '#10b981', 'Fazla': '#3b82f6'
}

const SEGMENT_COLORS: Record<string, string> = {
  'Şampiyonlar': '#10b981',
  'Potansiyel Şampiyonlar': '#0ea5e9',
  'Sadık Müşteriler': '#6366f1',
  'Sadık Olmaya Adaylar': '#f59e0b',
  'Yeni Müşteriler': '#ec4899',
  'İlgi Bekleyenler': '#14b8a6',
  'Risk Altındakiler': '#f97316',
  'Uyuyanlar': '#8b5cf6',
  'Kayıp Müşteriler': '#ef4444',
  'Tekrar Kazanılanlar': '#84cc16',
  'Yüksek Harcama Yapanlar': '#06b6d4',
  'Umut Vaat Edenler': '#d97706',
  'Bilinmiyor': '#94a3b8'
}
function getSegmentColor(segment: string): string {
  // Önce tam eşleşme dene
  if (SEGMENT_COLORS[segment]) return SEGMENT_COLORS[segment]
  // "04-) Sadık Müşteriler" → "Sadık Müşteriler" formatını dene
  const stripped = segment.replace(/^\d+[-.)]+\s*/, '').trim()
  return SEGMENT_COLORS[stripped] || '#6366f1'
}

  const formatUnits = (v: number, birim?: string) => {
    if (birim === 'KG' || birim === 'Litre') return `${v.toLocaleString('tr-TR')} ${birim}`
    return `${v.toLocaleString('tr-TR')} Adet`
  }

const ProductPortal = memo(({ isOpen, onClose, productId, productName }: ProductPortalProps) => {
  const {
    selectedDataSourceId, selectedYear, selectedMonth,
    selectedStartDate, selectedEndDate, selectedRegion,
    selectedCustomerType, selectedApprovalStatus
  } = useDashboardStore()

  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ProductPortalData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [associationType, setAssociationType] = useState<'PRODUCT' | 'BRAND_CAT' | 'CAT_ONLY'>('PRODUCT')
  const chartsRef = useRef<echarts.ECharts[]>([])

  useEffect(() => {
    if (isOpen && productId != null && productId > 0 && selectedDataSourceId) {
      loadData()
    }
    return () => {
      chartsRef.current.forEach(c => c.dispose())
      chartsRef.current = []
    }
  }, [isOpen, productId, selectedDataSourceId, selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedRegion, selectedCustomerType, selectedApprovalStatus])

  const loadData = async () => {
    setLoading(true)
    setData(null)
    setError(null)
    try {
      const filters: Record<string, any> = {}
      if (selectedYear) filters.year = selectedYear
      if (selectedMonth) filters.month = selectedMonth
      if (selectedStartDate) filters.start_date = selectedStartDate
      if (selectedEndDate) filters.end_date = selectedEndDate
      if (selectedRegion) filters.region = selectedRegion
      if (selectedCustomerType) filters.customer_type = selectedCustomerType
      if (selectedApprovalStatus) filters.approval_status = selectedApprovalStatus

      const result = await apiClient.getProductPortal(selectedDataSourceId!, productId, filters)
      setData(result)
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Bilinmeyen hata'
      setError(msg)
      console.error('Product portal error:', err)
    } finally {
      setLoading(false)
    }
  }

  // Charts initialization
  useEffect(() => {
    if (loading || !data || !isOpen) return

    // Dispose previous
    chartsRef.current.forEach(c => c.dispose())
    chartsRef.current = []

    const timer = setTimeout(() => {
      initTrendChart()
      initCustomerTypeChart()
      initSegmentChart()
      initPriceChart()
      initComparisonChart()
      initHourChart()
      initDayChart()
    }, 100)

    const handleResize = () => chartsRef.current.forEach(c => c.resize())
    window.addEventListener('resize', handleResize)

    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', handleResize)
    }
  }, [loading, data, isOpen])

  function initChart(domId: string, option: echarts.EChartsOption) {
    const dom = document.getElementById(domId)
    if (!dom) return
    const chart = echarts.init(dom)
    chart.setOption(option)
    chartsRef.current.push(chart)
  }

  const tooltipStyle = {
    backgroundColor: 'rgba(255,255,255,0.98)',
    borderColor: 'transparent',
    padding: [12, 16],
    textStyle: { color: '#1f2937', fontSize: 13 },
    confine: true,
    extraCssText: 'box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-radius: 12px;'
  }

  function initTrendChart() {
    if (!data) return
    initChart('pp-trend', {
      tooltip: { 
        trigger: 'axis', 
        ...tooltipStyle,
        formatter: (params: any) => {
          let html = `<div style="font-weight:700;margin-bottom:8px;color:#1e293b;border-bottom:1px solid #f1f5f9;padding-bottom:4px">${params[0].axisValue}</div>`
          params.forEach((p: any) => {
            const color = p.color
            const val = p.seriesName === 'Ciro' ? `₺${p.value.toLocaleString('tr-TR')}` : p.value.toLocaleString('tr-TR')
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin-bottom:4px">
              <span style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:${color}"></span>${p.seriesName}:</span>
              <span style="font-weight:700">${val}</span>
            </div>`
          })
          
          // Add Avg Price from raw data
          const monthData = data.monthlyTrend.find(t => t.month === params[0].axisValue)
          const monthAvgPrice = monthData ? ((monthData as any).avg_price ?? (monthData as any).avgPrice ?? 0) : 0
          if (monthAvgPrice > 0) {
            html += `<div style="display:flex;justify-content:space-between;gap:20px;margin-top:8px;padding-top:8px;border-top:1px dashed #e2e8f0">
              <span style="display:flex;align-items:center;gap:6px">Ort. Fiyat:</span>
              <span style="font-weight:700;color:#6366f1">₺${monthAvgPrice.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>`
          }
          return html
        }
      },
      legend: { data: ['Ciro', 'Adet'], top: 0, textStyle: { fontSize: 12 } },
      grid: { top: 40, bottom: 30, left: 60, right: 60 },
      xAxis: { type: 'category', data: data.monthlyTrend.map(t => t.month), axisLabel: { color: '#6b7280', fontSize: 11 } },
      yAxis: [
        { type: 'value', name: 'Ciro', axisLabel: { color: '#6b7280', formatter: (v: number) => v >= 1000 ? `₺${(v/1000).toFixed(0)}k` : `₺${v}` }, splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } } },
        { type: 'value', name: 'Adet', axisLabel: { color: '#6b7280' }, splitLine: { show: false } }
      ],
      series: [
        {
          name: 'Ciro', type: 'bar', data: data.monthlyTrend.map(t => t.revenue),
          itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] }
        },
        {
          name: 'Adet', type: 'line', yAxisIndex: 1, data: data.monthlyTrend.map(t => t.units),
          smooth: true, symbol: 'circle', symbolSize: 6,
          lineStyle: { width: 2, color: '#10b981' }, itemStyle: { color: '#10b981' }
        }
      ]
    })
  }

  function initCustomerTypeChart() {
    if (!data || data.customerProfile.byType.length === 0) return
    const colors = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6']
    initChart('pp-type', {
      tooltip: { trigger: 'item', ...tooltipStyle, formatter: (p: any) => `${p.name}<br/>Musteri: ${formatNumber(p.value)}<br/>Oran: ${p.percent}%` },
      series: [{
        type: 'pie', radius: ['40%', '72%'], center: ['50%', '50%'],
        data: data.customerProfile.byType.map((t, i) => ({ name: t.type, value: t.count, itemStyle: { color: colors[i % colors.length] } })),
        label: { fontSize: 11 },
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }
      }]
    })
  }

  function initSegmentChart() {
    if (!data || data.customerProfile.bySegment.length === 0) return
    const segments = data.customerProfile.bySegment.filter(s => s.count > 0).slice(0, 12)
    const total = segments.reduce((sum, s) => sum + s.count, 0)
    initChart('pp-segment', {
      tooltip: {
        trigger: 'item',
        ...tooltipStyle,
        formatter: (p: any) => {
          const name = p.name.replace(/^\d+[-.)]+\s*/, '').trim()
          return `${name}<br/>${formatNumber(p.value)} Alıcı (%${p.percent})`
        }
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 10,
        bottom: 10,
        itemGap: 6,
        itemWidth: 10,
        itemHeight: 10,
        textStyle: { fontSize: 10, color: '#374151' },
        formatter: (name: string) => {
          const seg = segments.find(s => s.segment === name)
          const label = name.replace(/^\d+[-.)]+\s*/, '').trim()
          if (!seg) return label
          const pct = total > 0 ? ((seg.count / total) * 100).toFixed(1) : '0'
          const cnt = seg.count >= 1000 ? `${(seg.count / 1000).toFixed(1)}k` : seg.count.toString()
          return `${label}: ${cnt} (%${pct})`
        }
      },
      series: [{
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['28%', '50%'],
        data: segments.map(s => ({
          value: s.count,
          name: s.segment,
          itemStyle: { color: getSegmentColor(s.segment) }
        })),
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' } }
      }]
    })
  }

  function initPriceChart() {
    if (!data || !data.monthlyTrend || data.monthlyTrend.length === 0) return
    const getPrice = (t: any) => t.avg_price ?? t.avgPrice ?? 0
    const priceData = data.monthlyTrend.filter(t => getPrice(t) > 0)
    if (priceData.length === 0) return
    initChart('pp-price', {
      tooltip: {
        trigger: 'axis',
        ...tooltipStyle,
        formatter: (params: any) => {
          const p = params[0]
          return `<div style="font-size:12px"><b>${p.axisValue}</b><br/>Ort. Birim Fiyat: <b style="color:#f59e0b">₺${Number(p.value).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</b></div>`
        }
      },
      grid: { top: 20, bottom: 30, left: 60, right: 20 },
      xAxis: { type: 'category', data: priceData.map(t => t.month), axisLabel: { color: '#6b7280', fontSize: 11 } },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#6b7280', formatter: (v: number) => `₺${v.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}` },
        splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } }
      },
      series: [{
        type: 'line',
        data: priceData.map(t => getPrice(t)),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#f59e0b', width: 2.5 },
        itemStyle: { color: '#f59e0b' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(245,158,11,0.18)' }, { offset: 1, color: 'rgba(245,158,11,0)' }] } }
      }]
    })
  }

  function initComparisonChart() {
    if (!data || !data.comparison) return
    const c = data.comparison
    initChart('pp-compare', {
      tooltip: { trigger: 'axis', ...tooltipStyle },
      legend: { data: ['Ciro', 'Adet', 'Musteri'], top: 0, textStyle: { fontSize: 11 } },
      grid: { top: 40, bottom: 30, left: 50, right: 50 },
      xAxis: { type: 'category', data: ['Bu Urun', 'Kategori Ort.', 'Marka Ort.'], axisLabel: { color: '#6b7280' } },
      yAxis: [
        { 
          type: 'value', 
          name: '',
          position: 'left',
          axisLabel: { color: '#6b7280', formatter: (v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : `${v}` }, 
          splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } } 
        },
        { 
          type: 'value', 
          name: '',
          position: 'right',
          axisLabel: { color: '#6b7280', formatter: (v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : `${v}` }, 
          splitLine: { show: false } 
        }
      ],
      series: [
        { name: 'Ciro', type: 'bar', yAxisIndex: 0, data: [c.product.revenue || 0, c.categoryAvg?.revenue || 0, c.brandAvg?.revenue || 0], itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] } },
        { name: 'Adet', type: 'bar', yAxisIndex: 1, data: [c.product.units || 0, c.categoryAvg?.units || 0, c.brandAvg?.units || 0], itemStyle: { color: '#10b981', borderRadius: [4, 4, 0, 0] } },
        { name: 'Musteri', type: 'bar', yAxisIndex: 1, data: [c.product.customers || 0, c.categoryAvg?.customers || 0, c.brandAvg?.customers || 0], itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] } }
      ]
    })
  }

  function initHourChart() {
    if (!data || data.timePatterns.byHour.length === 0) return
    // Fill all 24 hours
    const hourMap: Record<number, { count: number; revenue: number }> = {}
    data.timePatterns.byHour.forEach(h => { hourMap[h.hour] = { count: h.count, revenue: h.revenue } })
    const hours = Array.from({ length: 24 }, (_, i) => i)

    initChart('pp-hour', {
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { top: 20, bottom: 30, left: 50, right: 20 },
      xAxis: { type: 'category', data: hours.map(h => `${h}:00`), axisLabel: { color: '#6b7280', fontSize: 10, interval: 1 } },
      yAxis: { type: 'value', axisLabel: { color: '#6b7280' }, splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } } },
      series: [{
        type: 'bar', data: hours.map(h => hourMap[h]?.count || 0),
        itemStyle: { color: '#3b82f6', borderRadius: [3, 3, 0, 0] }
      }]
    })
  }

  function initDayChart() {
    if (!data || data.timePatterns.byDayOfWeek.length === 0) return
    const dayNames = ['Pzt', 'Sal', 'Car', 'Per', 'Cum', 'Cmt', 'Paz']
    const dayMap: Record<number, { count: number; revenue: number }> = {}
    data.timePatterns.byDayOfWeek.forEach(d => { dayMap[d.day] = { count: d.count, revenue: d.revenue } })

    initChart('pp-day', {
      tooltip: { trigger: 'axis', ...tooltipStyle },
      grid: { top: 20, bottom: 30, left: 50, right: 20 },
      xAxis: { type: 'category', data: dayNames, axisLabel: { color: '#6b7280' } },
      yAxis: { type: 'value', axisLabel: { color: '#6b7280' }, splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } } },
      series: [{
        type: 'bar', data: [1, 2, 3, 4, 5, 6, 0].map(d => dayMap[d]?.count || 0),
        itemStyle: { color: '#ec4899', borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', fontSize: 11, color: '#6b7280' }
      }]
    })
  }

  if (!isOpen && !data) return null

  const sectionCard = (title: string, icon: React.ReactNode, children: React.ReactNode, minHeight?: string) => (
    <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '20px', minHeight }}>
      <h4 style={{ margin: '0 0 16px', fontSize: '1rem', fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
        {icon} {title}
      </h4>
      {children}
    </div>
  )

  const skeletonBase = { background: 'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)', backgroundSize: '200% 100%', animation: 'pp-shimmer 1.2s ease-in-out infinite', borderRadius: '8px' }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Urun Portali: ${productName}`} width="1200px">
      {loading && !data ? (
        <div style={{ display: 'grid', gap: '24px', padding: '8px 0' }}>
          {/* KPI skeleton */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {[...Array(6)].map((_, i) => (
              <div key={i} style={{ ...skeletonBase, height: '80px' }} />
            ))}
          </div>
          {/* Trend chart skeleton */}
          <div style={{ ...skeletonBase, height: '260px' }} />
          {/* Bottom row skeleton */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ ...skeletonBase, height: '220px' }} />
            <div style={{ ...skeletonBase, height: '220px' }} />
          </div>
        </div>
      ) : error ? (
        <div style={{ padding: '60px', textAlign: 'center' }}>
          <div style={{ color: '#ef4444', fontWeight: 700, marginBottom: '8px' }}>Veri yuklenirken bir hata olustu</div>
          <div style={{ color: '#64748b', fontSize: '0.85rem', fontFamily: 'monospace', maxWidth: '600px', margin: '0 auto', wordBreak: 'break-word' }}>{error}</div>
        </div>
      ) : data ? (
        <div style={{ display: 'grid', gap: '24px' }}>

          {/* === URUN KIMLIK BANDI === */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
             <span style={{ padding: '4px 12px', borderRadius: '20px', background: '#ede9fe', color: '#6366f1', fontWeight: 600, fontSize: '0.8rem' }}>
               Kod: {data.product.kod}
             </span>
             <span style={{ padding: '4px 12px', borderRadius: '20px', background: '#dbeafe', color: '#2563eb', fontWeight: 600, fontSize: '0.8rem' }}>
               {data.product.marka}
             </span>
             <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
               {data.product.kategori}
             </span>
             {data.product.birim && (
               <span style={{ padding: '4px 12px', borderRadius: '20px', background: '#f0fdf4', color: '#16a34a', fontWeight: 600, fontSize: '0.8rem' }}>
                 Birim: {data.product.birim}
               </span>
             )}
          </div>

          {/* === KPI KARTLARI === */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {[
              { label: 'Toplam Ciro', value: formatCurrency(data.summary.totalRevenue), icon: <IconCurrencyLira size={20} />, color: '#4f46e5' },
              { label: 'Satilan Adet', value: formatNumber(data.summary.totalUnits), icon: <IconPackage size={20} />, color: '#10b981' },
              { label: 'Fis Sayisi', value: formatNumber(data.summary.totalReceipts), icon: <IconReceipt size={20} />, color: '#f59e0b' },
              { label: 'Musteri Sayisi', value: formatNumber(data.summary.totalCustomers), icon: <IconUsers size={20} />, color: '#3b82f6' },
              { label: 'Ort. Birim Fiyat', value: formatCurrency(data.summary.avgPrice), icon: <IconCurrencyLira size={20} />, color: '#8b5cf6' },
              { label: 'Ort. Sepet Tutari', value: formatCurrency(data.summary.avgBasketSize), icon: <IconShoppingCart size={20} />, color: '#ec4899' }
            ].map((kpi, i) => (
              <div key={i} style={{ padding: '18px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0', borderLeft: `4px solid ${kpi.color}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600 }}>{kpi.label}</span>
                  <span>{kpi.icon}</span>
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#1e293b' }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          {/* === PERFORMANS ANALIZI (DETAY) === */}
          {data.performance && (
            <div style={{ 
              background: '#f8fafc', 
              borderRadius: '16px', 
              padding: '24px', 
              border: '1px solid #e2e8f0',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: '24px'
            }}>
              {/* Row 1: Trend & Status */}
              <div style={{ gridColumn: 'span 3', display: 'flex', gap: '16px', marginBottom: '8px' }}>
                <div style={{ 
                  padding: '8px 16px', 
                  borderRadius: '12px', 
                  background: PERF_COLORS[data.performance.PerformansKategori] || '#6366f1',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                   {data.performance.PerformansKategori} Ürün
                </div>
                <div style={{ 
                  padding: '8px 16px', 
                  borderRadius: '12px', 
                  background: STOK_COLORS[data.performance.StokDurumu] || '#94a3b8',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.9rem'
                }}>
                   Stok: {data.performance.StokDurumu || 'Bilinmiyor'} ({Math.round(data.performance.StokMiktari || 0)} Adet)
                </div>
                <div style={{ 
                  padding: '8px 16px', 
                  borderRadius: '12px', 
                  background: data.performance.Trend_7_30 > 0 ? '#dcfce7' : data.performance.Trend_7_30 < 0 ? '#fee2e2' : '#f1f5f9',
                  color: data.performance.Trend_7_30 > 0 ? '#166534' : data.performance.Trend_7_30 < 0 ? '#991b1b' : '#64748b',
                  fontWeight: 700,
                  fontSize: '0.9rem'
                }}>
                  {data.performance.Trend_7_30 > 0 ? ' Artış Trendi' : data.performance.Trend_7_30 < 0 ? ' Düşüş Trendi' : ' Nötr Trend'}
                </div>
                <div style={{ 
                  padding: '8px 16px', 
                  borderRadius: '12px', 
                  background: data.performance.UyariDurumu && data.performance.UyariDurumu !== 'Normal' ? '#fef3c7' : '#f0fdf4',
                  color: data.performance.UyariDurumu && data.performance.UyariDurumu !== 'Normal' ? '#92400e' : '#166534',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  border: data.performance.UyariDurumu && data.performance.UyariDurumu !== 'Normal' ? '1px solid #f59e0b' : 'none'
                }}>
                  {data.performance.UyariDurumu || 'Normal'}
                </div>
              </div>

              {/* Row 2: Sales Periods */}
              <div style={{ background: 'white', padding: '16px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, marginBottom: '12px' }}>Son 7 Gün</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#1e293b' }}>{formatCurrency(data.performance.Son7GunCiro || 0)}</div>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{formatNumber(data.performance.Son7GunSatis || 0)} Satış · {data.performance.Son7GunMusteriSayisi || 0} Müşteri</div>
              </div>

              <div style={{ background: 'white', padding: '16px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, marginBottom: '12px' }}>Son 30 Gün</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#1e293b' }}>{formatCurrency(data.performance.Son30GunCiro || 0)}</div>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{formatNumber(data.performance.Son30GunSatis || 0)} Satış · {data.performance.Son30GunMusteriSayisi || 0} Müşteri</div>
              </div>

              <div style={{ background: 'white', padding: '16px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600, marginBottom: '12px' }}>Son 90 Gün</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#1e293b' }}>{formatCurrency(data.performance.Son90GunCiro || 0)}</div>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{formatNumber(data.performance.Son90GunSatis || 0)} Satış · {data.performance.Son90GunMusteriSayisi || 0} Müşteri</div>
              </div>

              {/* Row 3: Advanced Metrics */}
              <div style={{ gridColumn: 'span 3', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Kategori Sırası</div>
                  <div style={{ fontWeight: 700, color: '#1e293b' }}>#{data.performance.KategoriIcindeSira || '-'}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Günlük Ort. Satış</div>
                  <div style={{ fontWeight: 700, color: '#1e293b' }}>{(data.performance.GunlukOrtSatis || 0).toFixed(1)} Adet</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Tahmini Stok Ömrü</div>
                  <div style={{ fontWeight: 700, color: '#1e293b' }}>{Math.round(data.performance.TahminiStokGunu || 0)} Gün</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Birliktelik Potansiyeli</div>
                  <div style={{ fontWeight: 700, color: '#1e293b' }}>{Math.round(data.performance.CrossSellPotansiyeli || 0)} Skor</div>
                </div>
              </div>
            </div>
          )}

          {/* === KATEGORİ VE SEGMENT ANALİZİ === */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px' }}>
            {/* Kategori Karnesi */}
            {data.categoryPerformance && data.categoryPerformance.PazarPayi != null && sectionCard('Kategori Karnesi', <IconChartBar size={20} color="#4f46e5" />,
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: '#64748b' }}>Pazar Payı</span>
                  <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#4f46e5' }}>%{data.categoryPerformance.PazarPayi?.toFixed(2)}</span>
                </div>
                <div style={{ height: '8px', background: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(100, (data.categoryPerformance.PazarPayi || 0) * 5)}%`, height: '100%', background: '#4f46e5', borderRadius: '4px' }} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Kategori Durumu</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#1e293b' }}>{data.categoryPerformance.PerformansKategori}</div>
                  </div>
                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Trend Momentum</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: data.categoryPerformance.Trend > 0 ? '#10b981' : '#ef4444' }}>
                      {data.categoryPerformance.Momentum}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>
                  * Bu ürün {data.categoryPerformance.KategoriAdi} kategorisinde yer almaktadır.
                </div>
              </div>
            )}

            {/* RFM Segment Pasta Grafiği */}
            {sectionCard('Alıcıların RFM Segmenti', <IconTarget size={20} color="#6366f1" />,
              data.customerProfile.bySegment.length > 0 ? (
                <div id="pp-segment" style={{ height: '320px', width: '100%' }} />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Segment verisi bulunamadı.</div>
              )
            )}
          </div>

          {/* === SATIS TRENDI + BIRLIKTELIK === */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '24px' }}>
            {sectionCard('Satis Trendi', '',
              <div id="pp-trend" style={{ height: '320px', width: '100%' }} />
            )}
            {sectionCard('Birlikte Satilan Urunler', '',
              <>
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: '8px', padding: '2px', gap: '2px' }}>
                    {[
                      { id: 'PRODUCT', label: 'Ürün' },
                      { id: 'BRAND_CAT', label: 'Marka+Kat' },
                      { id: 'CAT_ONLY', label: 'Kategori' }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setAssociationType(tab.id as any)}
                        style={{
                          flex: 1, padding: '6px 4px', border: 'none', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600,
                          cursor: 'pointer', transition: 'all 0.2s',
                          background: associationType === tab.id ? 'white' : 'transparent',
                          color: associationType === tab.id ? '#6366f1' : '#64748b',
                          boxShadow: associationType === tab.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
                        }}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>
                {data.crossSell[associationType].length > 0 ? (
                  <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                    {data.crossSell[associationType].slice(0, 10).map((item, i) => {
                      const maxCo = Math.max(...data.crossSell[associationType].slice(0, 10).map(c => c.coOccurrence))
                      const pct = maxCo > 0 ? (item.coOccurrence / maxCo) * 100 : 0
                      return (
                        <div key={i} style={{ padding: '10px 12px', borderBottom: '1px solid #f1f5f9', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={item.productName}>{item.productName}</div>
                              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{item.brand}{item.category ? ` · ${item.category}` : ''}</div>
                            </div>
                            <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '12px' }}>
                              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#8b5cf6' }}>{item.coOccurrence} fis</div>
                              {item.lift != null && <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Lift: {item.lift.toFixed(1)}</div>}
                            </div>
                          </div>
                          <div style={{ height: '4px', background: '#f1f5f9', borderRadius: '2px', overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: '#8b5cf6', borderRadius: '2px', transition: 'width 0.5s ease' }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                    Birliktelik verisi bulunamadi.
                  </div>
                )}
              </>
            )}
          </div>

          {/* === MUSTERI PROFILI + MAGAZA === */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {sectionCard('Musteri Profili', <IconUsers size={20} color="#6366f1" />,
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', marginBottom: '8px' }}>Musteri Tipi</div>
                <div id="pp-type" style={{ height: '200px', width: '100%' }} />
              </div>,
              '240px'
            )}
            {sectionCard('Magaza Performansi', <IconBuildingStore size={20} color="#10b981" />,
              data.storePerformance.length > 0 ? (
                <div style={{ maxHeight: '260px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #f1f5f9', position: 'sticky', top: 0, background: 'white' }}>
                        <th style={{ padding: '10px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Magaza</th>
                        <th style={{ padding: '10px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Bolge</th>
                        <th style={{ padding: '10px', textAlign: 'right', color: '#64748b', fontWeight: 600 }}>Ciro</th>
                        <th style={{ padding: '10px', textAlign: 'right', color: '#64748b', fontWeight: 600 }}>Adet</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.storePerformance.map((s, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '10px', fontWeight: 500, color: '#1e293b' }}>{s.store_name}</td>
                          <td style={{ padding: '10px', color: '#64748b' }}>
                            <span style={{ padding: '2px 8px', borderRadius: '10px', background: '#f0fdf4', color: '#16a34a', fontSize: '0.75rem', fontWeight: 600 }}>{s.region || '-'}</span>
                          </td>
                          <td style={{ padding: '10px', textAlign: 'right', fontWeight: 600, color: '#6366f1' }}>{formatCurrency(s.revenue)}</td>
                          <td style={{ padding: '10px', textAlign: 'right' }}>{formatNumber(s.units)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Magaza verisi bulunamadi.</div>
              )
            )}
          </div>

          {/* === FIYAT DAGILIMI + KARSILASTIRMA === */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {sectionCard('Birim Fiyat Geçmişi', <IconScale size={20} color="#f59e0b" />,
              data.monthlyTrend && data.monthlyTrend.some(t => (t.avg_price ?? t.avgPrice ?? 0) > 0) ? (
                <div id="pp-price" style={{ height: '250px', width: '100%' }} />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Fiyat verisi bulunamadi.</div>
              )
            )}
            {sectionCard('Kategori & Marka Karsilastirmasi', <IconChartBar size={20} color="#3b82f6" />,
              <div id="pp-compare" style={{ height: '250px', width: '100%' }} />
            )}
          </div>

          {/* === ZAMAN ORUNTULERI === */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {sectionCard('Saat Bazli Dagılım', <IconClock size={20} color="#3b82f6" />,
              <div id="pp-hour" style={{ height: '220px', width: '100%' }} />
            )}
            {sectionCard('Gun Bazli Dagılım', <IconCalendar size={20} color="#ec4899" />,
              <div id="pp-day" style={{ height: '220px', width: '100%' }} />
            )}
          </div>

        </div>
      ) : (
        <div style={{ padding: '60px', textAlign: 'center', color: '#ef4444' }}>
          Veri yuklenirken bir hata olustu.
        </div>
      )}

      <style>{`
        @keyframes pp-spin {
          to { transform: rotate(360deg); }
        }
        @keyframes pp-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </Modal>
  )
})

export default ProductPortal
