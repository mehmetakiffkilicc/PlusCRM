import { useState, useEffect, ReactNode } from 'react'
import { formatPercent } from '../utils/format'
import apiClient from '../api/client'
import FilterPanel, { FilterState } from '../components/FilterPanel'
import LoadingOverlay from '../components/LoadingOverlay'
import useDashboardStore from '../stores/dashboardStore'
import useUIStore from '../stores/uiStore'
import InlineSpinner from '../components/InlineSpinner'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import {
  IconTrophy, IconStar, IconHeart, IconDiamond, IconRefresh,
  IconUserPlus, IconTarget, IconEye, IconAlertTriangle,
  IconFolder, IconAlertCircle, IconClock, IconRepeat,
  IconCoin, IconMoon, IconHeartBroken, IconChartBar, IconUsers
} from '@tabler/icons-react'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { notifications } from '@mantine/notifications'
import { useChatStore } from '../stores/chatStore'
import '../styles/DashboardHome.css'

interface RFMSegment {
  name: string
  count: number
  avg_r: number
  avg_f: number
  avg_m: number
  color: string
  description?: string
  action?: string
}

interface TopCustomer {
  customer_id: string
  name?: string
  segment?: string
  r_score?: number
  f_score?: number
  m_score?: number
  recency?: number
  frequency?: number
  monetary?: number
}

interface RFMData {
  segments: RFMSegment[]
  distribution: {
    recency: { range: string; count: number }[]
    frequency: { range: string; count: number }[]
    monetary: { range: string; count: number }[]
  }
  topCustomers: TopCustomer[]
  source?: string
  segment_count?: number
  totalCustomers?: number
}

const emptyData: RFMData = {
  segments: [],
  distribution: { recency: [], frequency: [], monetary: [] },
  topCustomers: []
}

// Fiyat formatlama
const formatPrice = (value: number) => {
  return Math.round(value).toLocaleString('tr-TR')
}

// Segment ikonlari (Prefixli ve Turkce karakterli versiyonlar)
const segmentIconMap: Record<string, ReactNode> = {
  '01-) Şampiyonlar': <IconTrophy size={24} stroke={1.8} />,
  '02-) Potansiyel Şampiyonlar': <IconStar size={24} stroke={1.8} />,
  '03-) Sadık Müşteriler': <IconHeart size={24} stroke={1.8} />,
  '06-) Tekrar Kazanılanlar': <IconRefresh size={24} stroke={1.8} />,
  '07-) Yüksek Harcama Yapanlar': <IconDiamond size={24} stroke={1.8} />,
  '05-) Yeni Müşteriler': <IconUserPlus size={24} stroke={1.8} />,
  '04-) Sadık Olmaya Adaylar': <IconTarget size={24} stroke={1.8} />,
  '08-) İlgi Bekleyenler': <IconEye size={24} stroke={1.8} />,
  '09-) Risk Altındakiler': <IconAlertTriangle size={24} stroke={1.8} />,
  '10-) Uyuyanlar': <IconMoon size={24} stroke={1.8} />,
  '11-) Kayıp Müşteriler': <IconHeartBroken size={24} stroke={1.8} />,
  // Eski versiyonlar icin fallback
  'Sampiyonlar': <IconTrophy size={24} stroke={1.8} />,
  'Potansiyel Sampiyonlar': <IconStar size={24} stroke={1.8} />,
  'Sadiklar': <IconHeart size={24} stroke={1.8} />,
  'Kayip Musteriler': <IconHeartBroken size={24} stroke={1.8} />
}
const getSegmentIcon = (name: string, size = 24): ReactNode => segmentIconMap[name] || <IconChartBar size={size} stroke={1.8} />

export default function RFMAnalysis() {
  const {
    selectedDataSourceId,
    selectedYear,
    selectedMonth,
    selectedStartDate,
    selectedEndDate,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedRegion,
    availableYears,
    setSelectedYear,
    setSelectedMonth,
    setDateRange
  } = useDashboardStore()

  const [initialLoading, setInitialLoading] = useState(true)
  const [filterLoading, setFilterLoading] = useState(false)
  const [rfmData, setRfmData] = useState<RFMData>(emptyData)
  const [selectedSegment, setSelectedSegment] = useState<RFMSegment | null>(null)

  // Ilk yukleme veya Data Source degistiginde
  useEffect(() => {
    if (selectedDataSourceId) {
      loadData(true, {
          year: selectedYear,
          month: selectedMonth,
          startDate: selectedStartDate,
          endDate: selectedEndDate
      })
    }
  }, [selectedDataSourceId])

  // Filtre degistiginde
  useEffect(() => {
    if (selectedDataSourceId && !initialLoading) {
        loadData(false, {
          year: selectedYear,
          month: selectedMonth,
          startDate: selectedStartDate,
          endDate: selectedEndDate
      })
    }
  }, [selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  const loadData = async (isInitial: boolean, currentFilters: FilterState) => {
    if (!selectedDataSourceId) {
      setInitialLoading(false)
      return
    }

    if (isInitial) {
      setInitialLoading(true)
    } else {
      setFilterLoading(true)
    }

    try {
      const params: Record<string, any> = {}
      if (currentFilters.year) params.year = currentFilters.year.toString()
      if (currentFilters.month) params.month = currentFilters.month.toString()
      if (currentFilters.startDate) params.start_date = currentFilters.startDate
      if (currentFilters.endDate) params.end_date = currentFilters.endDate
      if (selectedCustomerType) params.customer_type = selectedCustomerType
      if (selectedApprovalStatus) params.approval_status = selectedApprovalStatus
      if (selectedRegion) params.region = selectedRegion

      const data = await apiClient.getRFMAnalysis(selectedDataSourceId, params)
      setRfmData(data || emptyData)
    } catch (err: any) {
      // Don't log network errors if already known to be offline
      if (!err.message?.includes('Network Error')) {
        console.error(err)
        notifications.show({
          title: 'Hata',
          message: 'RFM verileri yüklenirken bir hata oluştu.',
          color: 'red'
        })
      }
      setRfmData(emptyData)
    } finally {
      setInitialLoading(false)
      setFilterLoading(false)
    }
  }

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (hasData) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('RFM Analizi', {
        page: 'rfm_analysis',
        data_source_id: selectedDataSourceId,
        total_customers: totalCustomers,
        segments: rfmData.segments.map(s => ({ name: s.name, count: s.count })),
        distribution: rfmData.distribution
      });
    }
  }, [rfmData, selectedDataSourceId]);

  const maxRecency = Math.max(...(rfmData.distribution.recency?.map(d => d.count) || [1]), 1)
  const maxFrequency = Math.max(...(rfmData.distribution.frequency?.map(d => d.count) || [1]), 1)
  const maxMonetary = Math.max(...(rfmData.distribution.monetary?.map(d => d.count) || [1]), 1)

  // totalCustomers: API'den gelen değer (tüm kayıtlı müşteriler), yoksa segment toplamı
  const totalCustomers = rfmData.totalCustomers ?? rfmData.segments.reduce((sum, seg) => sum + seg.count, 0)

  if (!selectedDataSourceId) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ marginBottom: '16px' }}><IconChartBar size={48} stroke={1.5} color="#6366f1" /></div>
        <div style={{ color: '#6b7280', fontSize: '1.1rem' }}>Lutfen bir veri kaynagi secin</div>
      </div>
    )
  }

  const hasData = rfmData.segments && rfmData.segments.length > 0

  return (
    <div style={{ padding: '24px' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>RFM Segmentasyon Analizi</h1>
        {hasData && (
          <AISummaryButton 
            contextType="rfm_analysis" 
            contextId={selectedDataSourceId?.toString()} 
          />
        )}
      </div>

      <LoadingOverlay loading={initialLoading || filterLoading}>
      {!hasData ? (
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '60px',
          textAlign: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
        }}>
          <div style={{ marginBottom: '16px' }}><IconChartBar size={56} stroke={1.3} color="#9ca3af" /></div>
          <h2 style={{ color: '#374151', marginBottom: '8px' }}>Veri Bulunamadi</h2>
          <p style={{ color: '#6b7280' }}>
            RFM analizi icin musteri verisi gereklidir. Veri kaynaginizda musteri ID sutunu oldugundan emin olun.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '24px' }}>

          <AIInsightCard 
            contextType="rfm_analysis" 
            contextId={selectedDataSourceId?.toString()} 
            title="RFM Dağılımı ve Göze Çarpan İçgörüler"
            data={rfmData}
          />

          {/* Ozet Kartlari */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
            <KpiCard
              {...KPI_COLORS.indigo}
              label="Toplam Aktif Müşteri"
              value={totalCustomers.toLocaleString('tr-TR')}
              icon={<IconUsers size={110} stroke={1.5} />}
            />
            <KpiCard
              {...KPI_COLORS.green}
              label="Segment Sayısı"
              value={String(rfmData.segments.length)}
              icon={<IconFolder size={110} stroke={1.5} />}
            />
            <KpiCard
              {...KPI_COLORS.amber}
              label="Şampiyonlar"
              value={(rfmData.segments.find(s => s.name.includes('Şampiyonlar') || s.name.includes('Sampiyonlar'))?.count || 0).toLocaleString('tr-TR')}
              icon={<IconTrophy size={110} stroke={1.5} />}
            />
            <KpiCard
              {...KPI_COLORS.red}
              label="Risk Altında"
              value={(
                (rfmData.segments.find(s => s.name.includes('Risk Altındakiler') || s.name.includes('Risk Altindakiler'))?.count || 0) +
                (rfmData.segments.find(s => s.name.includes('Kayıp Müşteriler') || s.name.includes('Kayip Musteriler'))?.count || 0)
              ).toLocaleString('tr-TR')}
              icon={<IconAlertCircle size={110} stroke={1.5} />}
            />
          </div>

          {/* RFM Segmentleri - 11 Segment Grid */}
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ marginBottom: '24px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <IconChartBar size={22} color="#4f46e5" />
              Musteri Segmentleri ({rfmData.segments.length} Segment)
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
              {[...rfmData.segments].sort((a, b) => {
                const numA = parseInt(a.name.match(/^(\d+)/)?.[1] || '99')
                const numB = parseInt(b.name.match(/^(\d+)/)?.[1] || '99')
                return numA - numB
              }).map((seg) => (
                <div
                  key={seg.name}
                  onClick={() => setSelectedSegment(selectedSegment?.name === seg.name ? null : seg)}
                  style={{
                    padding: '20px',
                    borderRadius: '12px',
                    background: `${seg.color}10`,
                    border: `2px solid ${selectedSegment?.name === seg.name ? seg.color : seg.color + '40'}`,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    transform: selectedSegment?.name === seg.name ? 'scale(1.02)' : 'scale(1)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <span style={{ display: 'flex' }}>{getSegmentIcon(seg.name)}</span>
                    <span style={{
                      fontSize: '0.75rem',
                      padding: '2px 8px',
                      background: seg.color,
                      color: 'white',
                      borderRadius: '10px',
                      fontWeight: 600
                    }}>
                      %{formatPercent((seg.count / totalCustomers) * 100)}
                    </span>
                  </div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '4px', color: seg.color }}>
                    {seg.count.toLocaleString('tr-TR')}
                  </div>
                  <div style={{ fontWeight: 600, color: '#374151', marginBottom: '12px', fontSize: '0.95rem' }}>
                    {seg.name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', display: 'grid', gap: '4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>R Skoru:</span>
                      <span style={{ fontWeight: 600, color: getRScoreColor(seg.avg_r) }}>{seg.avg_r != null ? formatPercent(seg.avg_r) : '-'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>F Skoru:</span>
                      <span style={{ fontWeight: 600, color: getFScoreColor(seg.avg_f) }}>{seg.avg_f != null ? formatPercent(seg.avg_f) : '-'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>M Skoru:</span>
                      <span style={{ fontWeight: 600, color: getMScoreColor(seg.avg_m) }}>{seg.avg_m != null ? formatPercent(seg.avg_m) : '-'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Secili Segment Detayi */}
          {selectedSegment && (
            <div style={{
              background: `linear-gradient(135deg, ${selectedSegment.color}15 0%, ${selectedSegment.color}05 100%)`,
              borderRadius: '16px',
              padding: '24px',
              border: `2px solid ${selectedSegment.color}40`,
              boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <span style={{ display: 'flex' }}>{getSegmentIcon(selectedSegment.name, 32)}</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: selectedSegment.color }}>
                    {selectedSegment.name}
                  </h3>
                  <p style={{ margin: 0, color: '#6b7280', fontSize: '0.875rem' }}>
                    {selectedSegment.count.toLocaleString('tr-TR')} müşteri (%{formatPercent((selectedSegment.count / totalCustomers) * 100)})
                  </p>
                </div>
              </div>

              {selectedSegment.description && (
                <div style={{ marginBottom: '16px', padding: '12px', background: 'white', borderRadius: '8px' }}>
                  <div style={{ fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Tanim:</div>
                  <div style={{ color: '#6b7280' }}>{selectedSegment.description}</div>
                </div>
              )}

              {selectedSegment.action && (
                <div style={{ padding: '12px', background: selectedSegment.color + '20', borderRadius: '8px', border: `1px solid ${selectedSegment.color}40` }}>
                  <div style={{ fontWeight: 600, marginBottom: '4px', color: selectedSegment.color }}>Onerilen Aksiyon:</div>
                  <div style={{ color: '#374151' }}>{selectedSegment.action}</div>
                </div>
              )}
            </div>
          )}

          {/* RFM Dagilim Grafikleri */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
            {/* Recency */}
            <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
              <h3 style={{ marginBottom: '20px', fontSize: '1.05rem', fontWeight: 600, color: '#1f2937' }}>
                <IconClock size={18} stroke={1.8} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} /> Son Alisveris (Recency)
              </h3>
              {rfmData.distribution.recency?.map((item, idx) => (
                <div key={idx} style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{item.range}</span>
                    <span style={{ fontWeight: 600 }}>{item.count.toLocaleString('tr-TR')}</span>
                  </div>
                  <div style={{ height: '10px', background: '#f3f4f6', borderRadius: '5px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(item.count / maxRecency) * 100}%`,
                      background: getRecencyBarColor(idx),
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)'
                    }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Frequency */}
            <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
              <h3 style={{ marginBottom: '20px', fontSize: '1.05rem', fontWeight: 600, color: '#1f2937' }}>
                <IconRepeat size={18} stroke={1.8} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} /> Alisveris Sikligi (Frequency)
              </h3>
              {rfmData.distribution.frequency?.map((item, idx) => (
                <div key={idx} style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{item.range}</span>
                    <span style={{ fontWeight: 600 }}>{item.count.toLocaleString('tr-TR')}</span>
                  </div>
                  <div style={{ height: '10px', background: '#f3f4f6', borderRadius: '5px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(item.count / maxFrequency) * 100}%`,
                      background: getFrequencyBarColor(idx),
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)'
                    }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Monetary */}
            <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
              <h3 style={{ marginBottom: '20px', fontSize: '1.05rem', fontWeight: 600, color: '#1f2937' }}>
                <IconCoin size={18} stroke={1.8} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} /> Aylık Ortalama Harcama (Monetary)
              </h3>
              {rfmData.distribution.monetary?.map((item, idx) => (
                <div key={idx} style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{item.range}</span>
                    <span style={{ fontWeight: 600 }}>{item.count.toLocaleString('tr-TR')}</span>
                  </div>
                  <div style={{ height: '10px', background: '#f3f4f6', borderRadius: '5px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(item.count / maxMonetary) * 100}%`,
                      background: getMonetaryBarColor(idx),
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)'
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* En Degerli Musteriler (Sampiyonlar) */}
          {rfmData.topCustomers && rfmData.topCustomers.length > 0 && (
            <div style={{ 
              background: 'white', 
              borderRadius: '16px', 
              padding: '24px', 
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' 
            }}>
              <h2 style={{ marginBottom: '20px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937' }}>
                <IconTrophy size={20} stroke={1.8} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} /> Sampiyon Musteriler
              </h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '600px' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #f3f4f6' }}>
                      <th style={{ padding: '12px', textAlign: 'left', fontWeight: 600 }}>Musteri</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>Segment</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>R Skoru</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>F Skoru</th>
                      <th style={{ padding: '12px', textAlign: 'center', fontWeight: 600 }}>M Skoru</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rfmData.topCustomers.slice(0, 10).map((c, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '12px' }}>
                          <div style={{ fontWeight: 600 }}>{c.name || c.customer_id}</div>
                          {c.name && <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>#{c.customer_id}</div>}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: '#10b98120',
                            color: '#10b981',
                            fontWeight: 600,
                            fontSize: '0.8rem'
                          }}>
                            {c.segment || 'Sampiyonlar'}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: getRScoreColor(c.r_score || 5) + '20',
                            color: getRScoreColor(c.r_score || 5),
                            fontWeight: 600
                          }}>
                            {c.r_score || 5}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: getFScoreColor(c.f_score || 5) + '20',
                            color: getFScoreColor(c.f_score || 5),
                            fontWeight: 600
                          }}>
                            {c.f_score || 5}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: getMScoreColor(c.m_score || 5) + '20',
                            color: getMScoreColor(c.m_score || 5),
                            fontWeight: 600
                          }}>
                            {c.m_score || 5}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}



        </div>
      )}
      </LoadingOverlay>
    </div>
  )
}

// Skor renk fonksiyonlari
function getRScoreColor(score: number): string {
  if (score >= 5) return '#10b981'
  if (score >= 4) return '#22c55e'
  if (score >= 3) return '#f59e0b'
  if (score >= 2) return '#ef4444'
  return '#6b7280'
}

function getFScoreColor(score: number): string {
  if (score >= 5) return '#10b981'
  if (score >= 4) return '#3b82f6'
  if (score >= 3) return '#8b5cf6'
  if (score >= 2) return '#f59e0b'
  return '#6b7280'
}

function getMScoreColor(score: number): string {
  if (score >= 5) return '#10b981'
  if (score >= 4) return '#a855f7'
  if (score >= 3) return '#3b82f6'
  if (score >= 2) return '#f59e0b'
  return '#6b7280'
}

// Dagilim bar renkleri
function getRecencyBarColor(idx: number): string {
  const colors = ['#10b981', '#22c55e', '#f59e0b', '#ef4444', '#6b7280']
  return colors[idx] || '#6366f1'
}

function getFrequencyBarColor(idx: number): string {
  const colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#6b7280']
  return colors[idx] || '#10b981'
}

function getMonetaryBarColor(idx: number): string {
  const colors = ['#10b981', '#a855f7', '#3b82f6', '#f59e0b', '#6b7280']
  return colors[idx] || '#f59e0b'
}
