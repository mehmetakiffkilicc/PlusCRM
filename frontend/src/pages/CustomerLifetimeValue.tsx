import { useState, useEffect, useCallback } from 'react'
import {
  IconChartBar, IconUsers, IconStar,
  IconArrowUpRight, IconShoppingCart, IconRefresh,
  IconTarget, IconCash, IconChartPie, IconAlertCircle
} from '@tabler/icons-react'
import { Alert, Group, Text, Button } from '@mantine/core'
import apiClient, { CLVCustomerDetail } from '../api/client'
import FilterPanel, { FilterState } from '../components/FilterPanel'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import LoadingOverlay from '../components/LoadingOverlay'
import Modal from '../components/Modal'
import useDashboardStore from '../stores/dashboardStore'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/DashboardHome.css'

interface CLVFactor {
  factor: string
  weight: number
  color: string
}

interface CLVData {
  summary: {
    averageCLV: number
    totalCLV: number
    customerCount: number
    avgLifespan: number
    topCLV: number
    avgOrderValue?: number
    avgOrderCount?: number
  }
  clvSegments: { segment: string; customers: number; avgCLV: number; totalValue: number; color: string }[]
  clvFactors?: CLVFactor[]
}

const emptyData: CLVData = {
  summary: { averageCLV: 0, totalCLV: 0, customerCount: 0, avgLifespan: 0, topCLV: 0 },
  clvSegments: [],
  clvFactors: []
}

const defaultFactors: CLVFactor[] = [
  { factor: 'Ortalama Sipariş Değeri', weight: 35, color: '#6366f1' },
  { factor: 'Alışveriş Sıklığı', weight: 30, color: '#10b981' },
  { factor: 'Müşteri Ömrü', weight: 20, color: '#f59e0b' },
  { factor: 'Sadakat', weight: 15, color: '#ec4899' }
]

export default function CustomerLifetimeValue() {
  const {
    selectedDataSourceId,
    dataSources,
    selectedYear,
    selectedMonth,
    selectedStartDate,
    selectedEndDate,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedRegion,
    setSelectedDataSourceId
  } = useDashboardStore()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<CLVData>(emptyData)

  // Modal State
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null)
  const [segmentCustomers, setSegmentCustomers] = useState<CLVCustomerDetail[]>([])
  const [modalLoading, setModalLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [sortField, setSortField] = useState('totalValue')
  const [sortOrder, setSortOrder] = useState('desc')
  const pageSize = 20

  const fetchData = useCallback(async () => {
    if (!selectedDataSourceId) return
    
    setLoading(true)
    setError(null)
    try {
      const filters = {
        year: selectedYear?.toString(),
        month: selectedMonth?.toString(),
        start_date: selectedStartDate || undefined,
        end_date: selectedEndDate || undefined,
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined,
        region: selectedRegion || undefined
      }

      const result = await apiClient.getCLVAnalysis(selectedDataSourceId, filters)
      setData(result || emptyData)
    } catch (err) {
      console.error('[CLV] Error:', err)
      notifications.show({
        title: 'Hata',
        message: 'CLV verileri yüklenirken bir hata oluştu.',
        color: 'red',
        icon: <IconAlertCircle size={16} />
      })
      setError('Veri yükleme hatası.')
      setData(emptyData)
    } finally {
      setLoading(false)
    }
  }, [selectedDataSourceId, selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  useEffect(() => {
    if (selectedDataSourceId) {
      fetchData()
    } else if (dataSources.length > 0) {
      setSelectedDataSourceId(dataSources[0].id.toString())
    }
  }, [selectedDataSourceId, fetchData, dataSources, setSelectedDataSourceId])

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (data && data.summary.customerCount > 0) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('CLV Analizi', {
        page: 'clv_analysis',
        data_source_id: selectedDataSourceId,
        summary: data.summary,
        segments: data.clvSegments.map(s => ({ name: s.segment, count: s.customers, avg: s.avgCLV }))
      });
    }
  }, [data, selectedDataSourceId]);

  const getFilters = () => ({
    year: selectedYear?.toString(),
    month: selectedMonth?.toString(),
    start_date: selectedStartDate || undefined,
    end_date: selectedEndDate || undefined,
    customer_type: selectedCustomerType || undefined,
    approval_status: selectedApprovalStatus || undefined,
    region: selectedRegion || undefined,
    sort_by: sortField,
    order: sortOrder
  })

  // Drill-down Logic
  const handleSegmentClick = (segment: string) => {
    setSelectedSegment(segment)
    setModalOpen(true)
    setSegmentCustomers([])
    setPage(1)
    setHasMore(true)
    setSortField('totalValue')
    setSortOrder('desc')
    fetchSegmentDetails(segment, 1, 'totalValue', 'desc')
  }

  const handleSort = (field: string) => {
    const newOrder = sortField === field && sortOrder === 'desc' ? 'asc' : 'desc'
    setSortField(field)
    setSortOrder(newOrder)
    setPage(1)
    setSegmentCustomers([])
    setHasMore(true)
    if (selectedSegment) {
      fetchSegmentDetails(selectedSegment, 1, field, newOrder)
    }
  }

  const fetchSegmentDetails = async (segment: string, pageNum: number, fld?: string, ord?: string) => {
    if (!selectedDataSourceId) return
    setModalLoading(true)
    try {
      const filters = {
        ...getFilters(),
        sort_by: fld || sortField,
        order: ord || sortOrder
      }
      const result = await apiClient.getCLVSegmentDetails(
        selectedDataSourceId, 
        segment, 
        pageNum, 
        pageSize,
        filters
      )
      
      if (pageNum === 1) {
        setSegmentCustomers(result.customers)
      } else {
        setSegmentCustomers(prev => [...prev, ...result.customers])
      }
      
      setHasMore(result.customers.length === pageSize)
    } catch (err) {
      console.error('[CLV] Details Error:', err)
    } finally {
      setModalLoading(false)
    }
  }

  const loadMoreCustomers = () => {
    if (!selectedSegment || modalLoading || !hasMore) return
    const nextPage = page + 1
    setPage(nextPage)
    fetchSegmentDetails(selectedSegment, nextPage)
  }

  const hasData = data.summary.customerCount > 0

  if (!selectedDataSourceId) return <div className="products-page"><div className="empty-state">Veri kaynağı seçin</div></div>

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Müşteri Yaşam boyu Değeri (CLV)</h1>
        <AISummaryButton 
          contextType="clv_analizi" 
          contextId={selectedDataSourceId} 
          contextData={{ summary: data.summary }}
        />
      </div>

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} title="Hata" color="red" mb="lg" variant="light">
          {error}
        </Alert>
      )}

      {hasData && !loading && (
        <div style={{ marginBottom: '24px' }}>
          <AIInsightCard 
            contextType="clv_analizi" 
            contextId={selectedDataSourceId.toString()} 
            title="CLV Stratejik Yorumu"
            data={data}
          />
        </div>
      )}

      <LoadingOverlay loading={loading}>
        {!hasData && !loading ? (
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '60px',
            textAlign: 'center',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
          }}>
            <div style={{ marginBottom: '16px', color: '#9ca3af' }}>
              <IconChartBar size={64} stroke={1.3} />
            </div>
            <h2 style={{ color: '#374151', marginBottom: '8px' }}>Veri Bulunamadı</h2>
            <p style={{ color: '#6b7280' }}>
              CLV analizi için müşteri ve satış verisi gereklidir.
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '24px' }}>
            {/* Özet Kartlar */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
              <KpiCard {...KPI_COLORS.indigo} label="Ortalama CLV"   value={`₺${Math.round(data.summary.averageCLV).toLocaleString('tr-TR')}`}                      sub="Müşteri başına ort. değer"    icon={<IconChartBar size={80} stroke={1.2} />} />
              <KpiCard {...KPI_COLORS.green}  label="Toplam CLV"    value={`₺${(data.summary.totalCLV / 1000000).toFixed(2).replace('.', ',')}M`}                   sub="Filtre dahilindeki toplam"   icon={<IconCash size={80} stroke={1.2} />} />
              <KpiCard {...KPI_COLORS.amber}  label="Müşteri Sayısı" value={data.summary.customerCount.toLocaleString('tr-TR')}                                       sub="Hesaplamaya dahil müşteri"   icon={<IconUsers size={80} stroke={1.2} />} />
              <KpiCard {...KPI_COLORS.pink}   label="En Yüksek CLV" value={`₺${Math.round(data.summary.topCLV).toLocaleString('tr-TR')}`}                           sub="En kârlı tek müşteri değeri" icon={<IconStar size={80} stroke={1.2} />} />
            </div>

            {/* Orta Panel (Grafikler/Faktörler) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
              <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 style={{ marginBottom: '20px', fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <IconChartPie size={24} stroke={2} color="#6366f1" />
                  İstatistikler
                </h2>
                <div style={{ display: 'grid', gap: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: '#f9fafb', borderRadius: '12px' }}>
                    <div>
                      <div style={{ color: '#6b7280', fontSize: '0.875rem' }}>Müşteri Başına Değer</div>
                      <div style={{ fontWeight: 700, fontSize: '1.5rem', color: '#10b981' }}>₺{Math.round(data.summary.totalCLV / (data.summary.customerCount || 1)).toLocaleString('tr-TR')}</div>
                    </div>
                    <div style={{ color: '#10b981', opacity: 0.3 }}>
                      <IconUsers size={40} stroke={1.5} />
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: '#f9fafb', borderRadius: '12px' }}>
                    <div>
                      <div style={{ color: '#6b7280', fontSize: '0.875rem' }}>Ortalama Sipariş</div>
                      <div style={{ fontWeight: 700, fontSize: '1.5rem', color: '#6366f1' }}>₺{Math.round(data.summary.avgOrderValue || 0).toLocaleString('tr-TR')}</div>
                    </div>
                    <div style={{ color: '#6366f1', opacity: 0.3 }}>
                      <IconShoppingCart size={40} stroke={1.5} />
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: '#f9fafb', borderRadius: '12px' }}>
                    <div>
                      <div style={{ color: '#6b7280', fontSize: '0.875rem' }}>Sipariş Sıklığı</div>
                      <div style={{ fontWeight: 700, fontSize: '1.5rem', color: '#f59e0b' }}>{data.summary.avgOrderCount || 0} Kez</div>
                    </div>
                    <div style={{ color: '#f59e0b', opacity: 0.3 }}>
                      <IconRefresh size={40} stroke={1.5} />
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
                <h2 style={{ marginBottom: '24px', fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <IconArrowUpRight size={24} stroke={2} color="#f59e0b" />
                  CLV Faktörleri
                </h2>
                <div style={{ display: 'grid', gap: '20px' }}>
                  {(data.clvFactors || defaultFactors).map((item, idx) => (
                    <div key={idx} style={{ padding: '16px 20px', background: '#ffffff', borderRadius: '12px', border: '1px solid #f3f4f6' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#1f2937' }}>{item.factor}</span>
                        <span style={{ color: item.color, fontWeight: 700, fontSize: '1.1rem', background: `${item.color}15`, padding: '4px 12px', borderRadius: '20px' }}>%{item.weight}</span>
                      </div>
                      <div style={{ height: '10px', background: '#f3f4f6', borderRadius: '5px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${item.weight}%`, background: item.color, transition: 'width 0.8s ease' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Segmentler - Tiklanabilir */}
            <div style={{ background: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <IconTarget size={24} stroke={2} color="#ec4899" />
                  Değer Segmentleri
                </h2>
                <span style={{ fontSize: '0.85rem', color: '#9ca3af' }}>Detay için segmentlere tıklayın</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
                {data.clvSegments.map((seg, idx) => (
                  <div 
                    key={idx} 
                    onClick={() => handleSegmentClick(seg.segment)}
                    style={{
                      padding: '20px',
                      borderRadius: '12px',
                      background: `${seg.color}15`,
                      border: `2px solid ${seg.color}40`,
                      textAlign: 'center',
                      cursor: 'pointer',
                      transition: 'transform 0.2s, box-shadow 0.2s'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-2px)'
                      e.currentTarget.style.boxShadow = '0 6px 12px rgba(0,0,0,0.08)'
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'translateY(0)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: seg.color }}>{seg.customers.toLocaleString('tr-TR')}</div>
                    <div style={{ fontWeight: 600, marginBottom: '8px' }}>{seg.segment}</div>
                    <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>Ort: ₺{Math.round(seg.avgCLV).toLocaleString('tr-TR')}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </LoadingOverlay>

      {/* DRILL DOWN MODAL */}
      <Modal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        title={`${selectedSegment} Segmenti Müşteri Listesi`}
        width="1100px"
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '600px' }}>
          <div style={{ overflowY: 'auto', flex: 1, paddingRight: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'white', zIndex: 1, boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                <tr>
                  <th 
                    onClick={() => handleSort('name')}
                    style={{ textAlign: 'left', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    Müşteri {sortField === 'name' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                  <th 
                    onClick={() => handleSort('totalValue')}
                    style={{ textAlign: 'right', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    Toplam Alışveriş {sortField === 'totalValue' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                  <th
                    onClick={() => handleSort('orderCount')}
                    style={{ textAlign: 'center', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    Alışveriş Sayısı {sortField === 'orderCount' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                  <th
                    onClick={() => handleSort('frequency')}
                    style={{ textAlign: 'center', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    Sıklık {sortField === 'frequency' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                  <th
                    onClick={() => handleSort('firstPurchaseDate')}
                    style={{ textAlign: 'right', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    İlk Tarih {sortField === 'firstPurchaseDate' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                  <th
                    onClick={() => handleSort('lastPurchaseDate')}
                    style={{ textAlign: 'right', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    Son Tarih {sortField === 'lastPurchaseDate' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                  <th
                    onClick={() => handleSort('lifespanDays')}
                    style={{ textAlign: 'right', padding: '12px', color: '#6b7280', borderBottom: '2px solid #e5e7eb', cursor: 'pointer' }}
                  >
                    Müşteri Ömrü {sortField === 'lifespanDays' ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                </tr>
              </thead>
              <tbody>
                {segmentCustomers.map((cust, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontWeight: 600, color: '#111827' }}>{cust.name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>ID: {cust.id}</div>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right', fontWeight: 600, color: '#6366f1' }}>
                      ₺{cust.totalValue.toLocaleString('tr-TR')}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center', color: '#4b5563' }}>{cust.orderCount}</td>
                    <td style={{ padding: '12px', textAlign: 'center', color: '#4b5563' }}>{cust.frequency} Gün</td>
                    <td style={{ padding: '12px', textAlign: 'right', color: '#4b5563' }}>{cust.firstPurchaseDate}</td>
                    <td style={{ padding: '12px', textAlign: 'right', color: '#4b5563' }}>{cust.lastPurchaseDate}</td>
                    <td style={{ padding: '12px', textAlign: 'right', color: '#4b5563' }}>{cust.lifespanDays} Gün</td>
                  </tr>
                ))}
                
                {segmentCustomers.length === 0 && !modalLoading && (
                  <tr><td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>Kayıt bulunamadı.</td></tr>
                )}
              </tbody>
            </table>
            
            {modalLoading && (
              <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>Yükleniyor...</div>
            )}
          </div>

          {hasMore && !modalLoading && (
            <button 
              onClick={loadMoreCustomers}
              style={{
                marginTop: '16px',
                width: '100%',
                padding: '12px',
                backgroundColor: '#f3f4f6',
                border: 'none',
                borderRadius: '8px',
                color: '#4b5563',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
              onMouseOver={e => e.currentTarget.style.backgroundColor = '#e5e7eb'}
              onMouseOut={e => e.currentTarget.style.backgroundColor = '#f3f4f6'}
            >
              Daha Fazla Yükle
            </button>
          )}
        </div>
      </Modal>
    </div>
  )
}
