import { useState, useEffect, useMemo, lazy, Suspense } from 'react'
import { formatPercent } from '../utils/format'
import {
  IconRefreshDot,
  IconUserMinus,
  IconHeartHandshake,
  IconReceipt,
  IconUsersGroup,
  IconChartLine,
  IconChartBar,
  IconCoin,
  IconAlertTriangle,
  IconSparkles,
  IconBell,
} from '@tabler/icons-react'
import { Skeleton, Group, Text as MantineText, Button, Badge, SegmentedControl } from '@mantine/core'
import { useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import useUIStore from '../stores/uiStore'
const RevenueChart = lazy(() => import('../components/RevenueChart'))
const ComparisonChart = lazy(() => import('../components/ComparisonChart'))
import InlineSpinner from '../components/InlineSpinner'
import SegmentStrip from '../components/SegmentStrip'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { MorningBriefing } from '../components/ai/MorningBriefing'
import { notifications } from '@mantine/notifications'
import { useChatStore } from '../stores/chatStore'
import '../styles/DashboardHome.css'

interface CustomerSegment {
  segment: string
  count: number
  revenue?: number
  transactions?: number
  avgRevenue?: number
  customerPercent?: number
  revenuePercent?: number
}

interface AnalyticsData {
  totalRevenue: number
  customerSegments: CustomerSegment[]
  salesByMonth: { month: string; sales: number }[]
  totalReceipts?: number
  totalCustomers?: number
  totalRegisteredCustomers?: number
  totalProducts?: number
  averageOrderValue?: number
  avgTransactionsPerCustomer?: number
  avgRevenuePerCustomer?: number
  everPurchasedCount?: number
  neverPurchasedCount?: number
  approvedCustomerCount?: number
  unapprovedCustomerCount?: number
  loyaltyShare?: number
  totalBrands?: number
  breakdown?: { registered: number; showPlus: number }
  churnRate?: number
  averageCLV?: number
  comparisonStats?: {
    revenue: { [year: string]: number[] }
    receipts: { [year: string]: number[] }
    customers: { [year: string]: number[] }
  }
}

const DashboardSkeleton = () => (
  <div className="dashboard-skeleton">
    <Skeleton height={400} radius="lg" animate />
    <Skeleton height={80} radius="md" animate />
    <div className="skeleton-grid">
      {[...Array(6)].map((_, i) => (
        <Skeleton key={i} height={140} radius="lg" animate />
      ))}
    </div>
    <div className="skeleton-row">
      <Skeleton height={350} radius="lg" animate />
      <Skeleton height={350} radius="lg" animate />
    </div>
  </div>
)

export default function DashboardHome() {
  const {
    selectedYear,
    selectedMonth,
    selectedStartDate,
    selectedEndDate,
    selectedCategories,
    selectedBrands,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedRegion,
    selectedDataSourceId,
  } = useDashboardStore()

  const navigate = useNavigate()
  const [kpisLoading, setKpisLoading] = useState(true)
  const [trendLoading, setTrendLoading] = useState(true)
  const [comparisonLoading, setComparisonLoading] = useState(true)
  const [segmentsLoading, setSegmentsLoading] = useState(true)
  const [initialLoaded, setInitialLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [anomalies, setAnomalies] = useState<any[]>([])
  const [anomalyNarrative, setAnomalyNarrative] = useState('')
  const [trendGranularity, setTrendGranularity] = useState<'daily' | 'weekly' | 'monthly'>('monthly')
  const [analytics, setAnalytics] = useState<AnalyticsData>({
    totalRevenue: 0,
    customerSegments: [],
    salesByMonth: [],
  })





  useEffect(() => {
    const controller = new AbortController();
    
    const params = {
      year: selectedYear,
      month: selectedMonth,
      start_date: selectedStartDate,
      end_date: selectedEndDate,
      categories: selectedCategories.join(','),
      brands: selectedBrands.join(','),
      customer_type: selectedCustomerType,
      approval_status: selectedApprovalStatus,
      region: selectedRegion,
    }

    setKpisLoading(true)
    setTrendLoading(true)
    setComparisonLoading(true)
    setSegmentsLoading(true)
    setError(null)

    // Unified fetch for all dashboard components
    apiClient.getDashboardFullSummary(params)
      .then(data => {
        if (controller.signal.aborted) return;
        
        setAnalytics(prev => ({
          ...prev,
          totalRevenue: data.totalRevenue || 0,
          totalReceipts: data.totalReceipts || 0,
          totalCustomers: data.totalCustomers || 0,
          totalRegisteredCustomers: data.totalRegisteredCustomers || 0,
          totalProducts: data.totalProducts || 0,
          totalBrands: data.totalBrands || 0,
          averageOrderValue: data.averageOrderValue || 0,
          avgTransactionsPerCustomer: data.avgTransactionsPerCustomer || 0,
          avgRevenuePerCustomer: data.avgRevenuePerCustomer || 0,
          loyaltyShare: data.loyaltyShare || 0,
          churnRate: data.churnRate || 0,
          salesByMonth: data.salesByMonth || [],
          customerSegments: data.customerSegments || [],
          comparisonStats: data.comparisonStats,
          breakdown: data.breakdown,
          everPurchasedCount: data.everPurchasedCount,
          neverPurchasedCount: data.neverPurchasedCount,
        }))
      })
      .catch(err => {
        if (err.name === 'AbortError') return;
        console.error('Dashboard Full Summary Failed', err);
        notifications.show({
          title: 'Hata',
          message: 'Dashboard verileri yüklenirken bir sorun oluştu.',
          color: 'red'
        });
        setError('Veriler yüklenemedi. Lütfen tekrar deneyin.');
      })
      .finally(() => {
        setKpisLoading(false);
        setTrendLoading(false);
        setComparisonLoading(false);
        setSegmentsLoading(false);
        setInitialLoaded(true);
      });

    // CLV analysis still separate if needed or integrated later
    if (selectedDataSourceId) {
      apiClient.getCLVAnalysis(selectedDataSourceId, {
        start_date: selectedStartDate,
        end_date: selectedEndDate,
      })
        .then(data => setAnalytics(prev => ({ ...prev, averageCLV: data?.summary?.averageCLV ?? 0 })))
        .catch(err => console.error('CLV Fetch Failed', err))
    }

    // Anomalileri Yükle
    apiClient.detectAnomalies(Number(selectedDataSourceId) || 0)
      .then(data => {
        setAnomalies(data.anomalies || [])
        setAnomalyNarrative(data.narrative || '')
      })
      .catch(err => console.error('Anomali Yükleme Hatası', err))

    return () => controller.abort();
  }, [
    selectedYear,
    selectedMonth,
    selectedStartDate,
    selectedEndDate,
    selectedCategories,
    selectedBrands,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedRegion,
    selectedDataSourceId,
    trendGranularity,
  ])

  // AI için global bağlamı (context) güncelle: Mağaza veya filtre değişince AI'ya bildir
  useEffect(() => {
    const { attachPageContext } = useChatStore.getState();
    attachPageContext('Dashboard', {
      page: 'dashboard_home',
      data_source_id: selectedDataSourceId,
      filters: {
        year: selectedYear,
        month: selectedMonth,
        startDate: selectedStartDate,
        endDate: selectedEndDate,
        categories: selectedCategories,
        brands: selectedBrands
      },
      summary_data: {
        revenue: analytics.totalRevenue,
        customers: analytics.totalCustomers,
        clv: analytics.averageCLV,
        churn: analytics.churnRate
      }
    });
  }, [selectedDataSourceId, selectedYear, selectedMonth, selectedStartDate, selectedEndDate, analytics.totalRevenue]);

  // Otomatik granülarite seçimi
  useEffect(() => {
    if (!selectedStartDate || !selectedEndDate) {
        setTrendGranularity('monthly')
        return
    }
    const daysDiff = (new Date(selectedEndDate).getTime() - new Date(selectedStartDate).getTime()) / (1000 * 60 * 60 * 24)
    if (daysDiff < 30) setTrendGranularity('daily')
    else if (daysDiff < 90) setTrendGranularity('weekly')
    else setTrendGranularity('monthly')
  }, [selectedStartDate, selectedEndDate])

  const dailyDataTransformed = useMemo(() =>
    analytics.salesByMonth.map(item => ({ date: item.month, sales: item.sales })),
    [analytics.salesByMonth]
  )

  const yearlyTotals = useMemo(() => {
    if (!analytics.comparisonStats) return { revenue: {}, receipts: {}, customers: {} }
    const calcTotal = (data: { [year: string]: number[] }) => {
      const result: { [year: string]: number } = {}
      Object.entries(data).forEach(([year, months]) => {
        result[year] = months.reduce((sum, val) => sum + (val || 0), 0)
      })
      return result
    }
    return {
      revenue: calcTotal(analytics.comparisonStats.revenue || {}),
      receipts: calcTotal(analytics.comparisonStats.receipts || {}),
      customers: calcTotal(analytics.comparisonStats.customers || {}),
    }
  }, [analytics.comparisonStats])

  const segmentGroups = useMemo(() => {
    if (!analytics.customerSegments) return { degerli: null, potansiyel: null, risk: null }

    const segments = analytics.customerSegments
    const getGroupKey = (segName: string): 'degerli' | 'potansiyel' | 'risk' | null => {
      if (!segName) return null
      const lower = segName.toLowerCase()
      if (lower.includes('şampiyon') || lower.includes('sampiyon')) return 'degerli'
      if (lower.includes('sadık müşteri') || lower.includes('sadiklar')) return 'degerli'
      if (lower.includes('yüksek harcama') || lower.includes('yuksek harcama')) return 'degerli'
      if (lower.includes('tekrar kazan') || lower.includes('tekrar kazanilan')) return 'potansiyel'
      if (lower.includes('yeni müşteri') || lower.includes('yeni musteri')) return 'potansiyel'
      if (lower.includes('sadık olmaya') || lower.includes('sadik olmaya')) return 'potansiyel'
      if (lower.includes('ilgi bekleyen')) return 'potansiyel'
      if (lower.includes('risk alt') || lower.includes('risk altindakiler')) return 'risk'
      if (lower.includes('uyuyan')) return 'risk'
      if (lower.includes('kayıp') || lower.includes('kayip')) return 'risk'
      return null
    }

    const groups = {
      degerli: { count: 0, revenue: 0, transactions: 0, avgRevenue: 0, customerPercent: 0, revenuePercent: 0, segmentList: [] as string[] },
      potansiyel: { count: 0, revenue: 0, transactions: 0, avgRevenue: 0, customerPercent: 0, revenuePercent: 0, segmentList: [] as string[] },
      risk: { count: 0, revenue: 0, transactions: 0, avgRevenue: 0, customerPercent: 0, revenuePercent: 0, segmentList: [] as string[] },
    }

    segments.forEach(s => {
      if (!s.segment) return
      const groupKey = getGroupKey(s.segment)
      if (groupKey) {
        const g = groups[groupKey]
        g.count += s.count || 0
        g.revenue += s.revenue || 0
        g.transactions += s.transactions || 0
        g.customerPercent += s.customerPercent || 0
        g.revenuePercent += s.revenuePercent || 0
        if (!g.segmentList.includes(s.segment)) g.segmentList.push(s.segment)
      }
    })

    const result: any = { degerli: null, potansiyel: null, risk: null }
    ;(['degerli', 'potansiyel', 'risk'] as const).forEach(key => {
      const g = groups[key]
      if (g.count > 0 || g.revenue > 0) {
        g.avgRevenue = g.count > 0 ? g.revenue / g.count : 0
        result[key] = { ...g, segments: g.segmentList.join(', ') }
      }
    })
    return result
  }, [analytics.customerSegments])

  return (
    <div className="dashboard-home-content">


      {!initialLoaded ? (
        <DashboardSkeleton />
      ) : (
        <div className="dashboard-sections">
          
          {/* AI Morning Briefing & Insights */}
          <div style={{ marginBottom: 20 }}>
            <MorningBriefing data={analytics} loading={kpisLoading || segmentsLoading} />
            <AIInsightCard 
              contextType="dashboard" 
              contextId={selectedDataSourceId || 'all'} 
              title="Dashboard Özeti ve Insightlar"
              data={analytics}
            />
          </div>

          {/* 1. Trend Chart */}
          <div className="chart-card">
            <Group justify="space-between" mb="md">
              <h3 className="chart-title" style={{ margin: 0 }}>
                <IconChartLine size={22} color="var(--mantine-color-indigo-6)" />
                {trendGranularity === 'daily' ? 'Günlük Ciro Trendi' : trendGranularity === 'weekly' ? 'Haftalık Ciro Trendi' : 'Aylık Ciro Trendi'}
              </h3>
              <SegmentedControl
                size="xs"
                value={trendGranularity}
                onChange={(val: any) => setTrendGranularity(val)}
                data={[
                  { label: 'Günlük', value: 'daily' },
                  { label: 'Haftalık', value: 'weekly' },
                  { label: 'Aylık', value: 'monthly' },
                ]}
              />
            </Group>
            {trendLoading ? (
              <div className="chart-loader">
                <InlineSpinner size={40} thickness={3} color="var(--mantine-color-indigo-6)" />
              </div>
            ) : (
              <div className="chart-body">
                <Suspense fallback={<InlineSpinner size={40} thickness={3} color="var(--mantine-color-indigo-6)" />}>
                  <RevenueChart
                    data={trendGranularity !== 'daily' ? analytics.salesByMonth : []}
                    dailyData={trendGranularity === 'daily' ? dailyDataTransformed : undefined}
                    title={trendGranularity === 'daily' ? 'Günlük Ciro' : trendGranularity === 'weekly' ? 'Haftalık Ciro' : 'Aylık Ciro'}
                    height="100%"
                  />
                </Suspense>
              </div>
            )}
          </div>

          {/* Anormallik Uyarı Şeridi (Gelişmiş) */}
          {anomalies.length > 0 && (
            <div className="anomaly-premium-banner">
              <div className="anomaly-premium-header">
                <Group justify="space-between" w="100%">
                  <Group gap="xs">
                    <div className="anomaly-pulse-icon">
                      <IconAlertTriangle size={20} color="#fff" />
                    </div>
                    <div>
                      <MantineText fw={800} size="sm" c="red.9" style={{ letterSpacing: '0.05em' }}>KRİTİK ANOMALİ TESPİTİ</MantineText>
                      <MantineText size="xs" c="red.7" fw={500}>Sistemde olağan dışı değişimler saptandı</MantineText>
                    </div>
                  </Group>
                  <Button 
                    variant="white" 
                    color="red" 
                    size="compact-xs" 
                    radius="xl"
                    leftSection={<IconBell size={14} />}
                    onClick={() => {
                      // Notification Drawer'ı açmak için bir event veya store tetiklenebilir
                      // Şimdilik sadece yönlendirme/bilgi amaçlı
                      notifications.show({
                        title: 'Bildirim Merkezi',
                        message: 'Tüm detaylar için sağ üstteki bildirim paneline göz atın.',
                        color: 'red'
                      })
                    }}
                  >
                    Detayları Gör
                  </Button>
                </Group>
              </div>
              
              <div className="anomaly-premium-list">
                {anomalies.map((a: any, idx: number) => (
                  <div key={idx} className="anomaly-premium-item">
                    <MantineText size="xs" fw={700} c="gray.6" style={{ textTransform: 'uppercase' }}>{a.metric === 'totalRevenue' ? 'Ciro' : a.metric}</MantineText>
                    <Group gap={5}>
                      <MantineText fw={800} size="lg" c="red.7">%{a.change > 0 ? '+' : ''}{a.change}</MantineText>
                      <Badge size="xs" color={a.severity === 'critical' ? 'red' : 'orange'} variant="filled">
                        {a.severity.toUpperCase()}
                      </Badge>
                    </Group>
                  </div>
                ))}
              </div>

              {anomalyNarrative && (
                <div className="anomaly-premium-narrative">
                  <IconSparkles size={16} color="#dc2626" />
                  <MantineText size="sm" fs="italic" c="gray.7" fw={500}>
                    <span style={{ fontWeight: 700, color: '#dc2626' }}>AI Analizi:</span> {anomalyNarrative}
                  </MantineText>
                </div>
              )}
            </div>
          )}

          {/* 2. Revenue Banner */}
          <div className="revenue-banner" style={{ background: kpisLoading ? '#f9fafb' : undefined }}>
            <div className="revenue-banner-title">Toplam Ciro</div>
            <div className="revenue-banner-value">
              {kpisLoading ? (
                <InlineSpinner size={24} color="var(--mantine-color-indigo-3)" />
              ) : (
                (analytics.totalRevenue || 0).toLocaleString('tr-TR', {
                  style: 'currency',
                  currency: 'TRY',
                  maximumFractionDigits: 0,
                })
              )}
            </div>
          </div>

          {/* 3. Segment Strip */}
          <SegmentStrip segmentGroups={segmentGroups} loading={segmentsLoading} />

          {/* 4. KPI Grid */}
          <div className="kpi-grid">
            {/* Ort. İşlem Sayısı */}
            <div className="kpi-card kpi-card-green">
              <div className="kpi-icon">
                <IconRefreshDot size={22} stroke={1.8} color="#10b981" />
              </div>
              <div className="kpi-content">
                <h3>Ort. İşlem Sayısı</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#10b981" /> : (
                  <>
                    <div className="kpi-value">
                      {analytics.avgTransactionsPerCustomer?.toLocaleString('tr-TR', {
                        minimumFractionDigits: 2, maximumFractionDigits: 2,
                      })}
                    </div>
                    <div className="kpi-label">Müşteri Başına AV</div>
                  </>
                )}
              </div>
            </div>

            {/* Churn Oranı */}
            <div className="kpi-card kpi-card-red">
              <div className="kpi-icon">
                <IconUserMinus size={22} stroke={1.8} color="#ef4444" />
              </div>
              <div className="kpi-content">
                <h3>Churn Oranı</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#ef4444" /> : (
                  <>
                    <div className="kpi-value">%{analytics.churnRate || 0}</div>
                    <div className="kpi-label">Kaybedilen Müşteri</div>
                  </>
                )}
              </div>
            </div>

            {/* Sadakat Ciro Payı */}
            <div className="kpi-card kpi-card-pink">
              <div className="kpi-icon">
                <IconHeartHandshake size={22} stroke={1.8} color="#ec4899" />
              </div>
              <div className="kpi-content">
                <h3>Sadakat Ciro Payı</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#ec4899" /> : (
                  <>
                    <div className="kpi-value">%{analytics.loyaltyShare || 0}</div>
                    <div className="kpi-label">Sadık Müşteri Katkısı</div>
                  </>
                )}
              </div>
            </div>

            {/* Fiş Sayısı */}
            <div className="kpi-card kpi-card-purple">
              <div className="kpi-icon">
                <IconReceipt size={22} stroke={1.8} color="#8b5cf6" />
              </div>
              <div className="kpi-content">
                <h3>Toplam Fiş Sayısı</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#8b5cf6" /> : (
                  <>
                    <div className="kpi-value">
                      {analytics.totalReceipts?.toLocaleString('tr-TR')}
                    </div>
                    <div className="kpi-label">Toplam İşlem Adedi</div>
                  </>
                )}
              </div>
            </div>

            {/* Verimlilik Metrikleri */}
            <div className="kpi-card kpi-card-teal">
              <div className="kpi-icon">
                <IconChartBar size={22} stroke={1.8} color="#0d9488" />
              </div>
              <div className="kpi-content">
                <h3>Verimlilik Metrikleri</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#0d9488" /> : (
                  <div className="kpi-metrics-list">
                    <div className="kpi-metric-row" style={{ flexWrap: 'nowrap', alignItems: 'center' }}>
                      <span className="kpi-label" style={{ margin: 0 }}>Sepet Ortalaması</span>
                      <span className="kpi-value kpi-value--sm" style={{ whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {analytics.averageOrderValue?.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ₺
                      </span>
                    </div>
                    <div className="kpi-metric-row kpi-metric-row--bordered" style={{ flexWrap: 'nowrap', alignItems: 'center' }}>
                      <span className="kpi-label" style={{ margin: 0 }}>Müşteri Başına Ciro</span>
                      <span className="kpi-value kpi-value--sm" style={{ whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {analytics.avgRevenuePerCustomer?.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ₺
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Ortalama CLV */}
            <div className="kpi-card kpi-card-orange">
              <div className="kpi-icon">
                <IconCoin size={22} stroke={1.8} color="#f59e0b" />
              </div>
              <div className="kpi-content">
                <h3>Ortalama CLV</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#f59e0b" /> : (
                  <>
                    <div className="kpi-value" style={{ whiteSpace: 'nowrap' }}>
                      {(analytics.averageCLV || 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}&nbsp;₺
                    </div>
                    <div className="kpi-label">Müşteri Yaşam Boyu Değeri</div>
                  </>
                )}
              </div>
            </div>

            {/* Müşteri Onay Durumu */}
            <div className="kpi-card kpi-card-blue">
              <div className="kpi-icon">
                <IconUsersGroup size={22} stroke={1.8} color="#3b82f6" />
              </div>
              <div className="kpi-content">
                <h3>Müşteri Onay Durumu</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#3b82f6" /> : (
                  <div className="kpi-status-list">
                    <div className="kpi-status-row kpi-status-row--success">
                      <span>Onaylı</span>
                      <span>{analytics.approvedCustomerCount?.toLocaleString('tr-TR')}</span>
                    </div>
                    <div className="kpi-status-row kpi-status-row--danger">
                      <span>Onaylı Olmayan</span>
                      <span>{analytics.unapprovedCustomerCount?.toLocaleString('tr-TR')}</span>
                    </div>
                    <div className="kpi-status-row kpi-status-row--muted">
                      <span>Onay Oranı</span>
                      <span>
                        {analytics.totalRegisteredCustomers
                          ? `%${formatPercent(((analytics.approvedCustomerCount || 0) / analytics.totalRegisteredCustomers) * 100)}`
                          : '%0'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Toplam Müşteri */}
            <div className="kpi-card kpi-card-indigo">
              <div className="kpi-icon">
                <IconUsersGroup size={22} stroke={1.8} color="#4f46e5" />
              </div>
              <div className="kpi-content">
                <h3>Toplam Müşteri Durumu</h3>
                {kpisLoading ? <InlineSpinner size={20} color="#4f46e5" /> : (
                  <div className="kpi-status-list">
                    <div className="kpi-status-row kpi-status-row--primary kpi-status-row--bordered">
                      <span>Toplam Kayıtlı</span>
                      <span>{analytics.totalRegisteredCustomers?.toLocaleString('tr-TR')}</span>
                    </div>
                    <div className="kpi-status-row kpi-status-row--success">
                      <span>Aktif (Alışveriş Yapmış)</span>
                      <span>{(analytics.everPurchasedCount ?? analytics.totalCustomers)?.toLocaleString('tr-TR')}</span>
                    </div>
                    <div className="kpi-status-row kpi-status-row--danger">
                      <span>Pasif (Hiç Alışveriş Yapmamış)</span>
                      <span>{(analytics.neverPurchasedCount ?? ((analytics.totalRegisteredCustomers || 0) - (analytics.totalCustomers || 0)))?.toLocaleString('tr-TR')}</span>
                    </div>
                    <div className="kpi-status-row kpi-status-row--muted">
                      <span>Aktif Oranı</span>
                      <span>
                        {analytics.totalRegisteredCustomers
                          ? `%${formatPercent(((analytics.everPurchasedCount ?? analytics.totalCustomers ?? 0) / analytics.totalRegisteredCustomers) * 100)}`
                          : '%0'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 6. Comparison Charts */}
          <div className="comparison-section">
            {[
              {
                title: 'Aylık Ciro Karşılaştırması',
                subTitle: 'Son 3 Yıl',
                data: analytics.comparisonStats?.revenue || {},
                colors: ['#9ca3af', '#fbbf24', '#4f46e5'],
                valuePrefix: '₺',
                yearlyLabel: 'Yıllık Ciro Toplamı',
                yearlyData: yearlyTotals.revenue,
                yearlyFormat: (v: number) => `₺${v.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}`,
                spinnerColor: '#4f46e5',
              },
              {
                title: 'Aylık İşlem Adedi Karşılaştırması',
                subTitle: 'Son 3 Yıl (Fiş Sayısı)',
                data: analytics.comparisonStats?.receipts || {},
                colors: ['#d1d5db', '#f59e0b', '#10b981'],
                valuePrefix: '',
                yearlyLabel: 'Yıllık İşlem Toplamı',
                yearlyData: yearlyTotals.receipts,
                yearlyFormat: (v: number) => v.toLocaleString('tr-TR'),
                spinnerColor: '#10b981',
              },
              {
                title: 'Aylık Müşteri Sayısı Karşılaştırması',
                subTitle: 'Son 3 Yıl',
                data: analytics.comparisonStats?.customers || {},
                colors: ['#cbd5e1', '#ec4899', '#8b5cf6'],
                valuePrefix: '',
                yearlyLabel: 'Yıllık Müşteri Toplamı',
                yearlyData: yearlyTotals.customers,
                yearlyFormat: (v: number) => v.toLocaleString('tr-TR'),
                spinnerColor: '#8b5cf6',
              },
            ].map((row, rowIdx) => (
              <div key={rowIdx} className="comparison-row">
                {/* Line Chart */}
                <div className="chart-card comparison-chart-card">
                  {comparisonLoading && (
                    <div className="chart-loading-overlay">
                      <InlineSpinner size={30} color={row.spinnerColor} />
                    </div>
                  )}
                  <Suspense fallback={<InlineSpinner size={30} color={row.spinnerColor} />}>
                    <ComparisonChart
                      title={row.title}
                      subTitle={row.subTitle}
                      data={row.data}
                      years={[2024, 2025, 2026]}
                      colors={row.colors}
                      valuePrefix={row.valuePrefix}
                    />
                  </Suspense>
                </div>

                {/* Yearly Totals */}
                <div className="chart-card yearly-totals-card">
                  <h4 className="yearly-totals-title">{row.yearlyLabel}</h4>
                  <div className="yearly-bar-container">
                    {[2024, 2025, 2026].map((year, idx) => {
                      const value = row.yearlyData[year] || 0
                      const maxValue = Math.max(...Object.values(row.yearlyData).map(Number))
                      const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0
                      return (
                        <div key={year} className="yearly-bar-item">
                          <div className="yearly-bar-header">
                            <span style={{ color: row.colors[idx], fontWeight: 600 }}>{year}</span>
                            <span>{row.yearlyFormat(value)}</span>
                          </div>
                          <div className="yearly-bar-track">
                            <div
                              className="yearly-bar-fill"
                              style={{ width: `${percentage}%`, background: row.colors[idx] }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
