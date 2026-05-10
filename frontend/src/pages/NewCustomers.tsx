import { useState, useEffect } from 'react'
import { formatPercent } from '../utils/format'
import FilterPanel, { FilterState } from '../components/FilterPanel'
import apiClient from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'
import useDashboardStore from '../stores/dashboardStore'
import { IconAlertCircle } from '@tabler/icons-react'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/DashboardHome.css'

export default function NewCustomers() {
  const { 
      selectedDataSourceId, 
      selectedYear, 
      selectedMonth, 
      selectedStartDate, 
      selectedEndDate,
      selectedCategories,
      selectedBrands,
      selectedCustomerType,
      selectedApprovalStatus,
      selectedRegion,
      availableYears,
      setSelectedYear,
      setSelectedMonth,
      setDateRange
  } = useDashboardStore()

  const [initialLoading, setInitialLoading] = useState(false)
  const [filterLoading, setFilterLoading] = useState(false)
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string>('')
  const [isFirstLoad, setIsFirstLoad] = useState(true)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  useEffect(() => {
    if (selectedDataSourceId) {
      fetchData({
          year: selectedYear,
          month: selectedMonth,
          startDate: selectedStartDate,
          endDate: selectedEndDate
      }, true)
    }
  }, [selectedDataSourceId])

  useEffect(() => {
    if (selectedDataSourceId && !isFirstLoad) {
        fetchData({
            year: selectedYear,
            month: selectedMonth,
            startDate: selectedStartDate,
            endDate: selectedEndDate,
            categories: selectedCategories,
            brands: selectedBrands,
            customerType: selectedCustomerType,
            approvalStatus: selectedApprovalStatus,
            region: selectedRegion
        }, false)
    }
  }, [selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedCategories, selectedBrands, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  const fetchData = async (nextFilters: FilterState, treatAsInitial: boolean) => {
    try {
      if (treatAsInitial || (!data && isFirstLoad)) {
        setInitialLoading(true)
      } else {
        setFilterLoading(true)
      }
      setError('')
      
      const params = new URLSearchParams()
      if (nextFilters.year) params.append('year', nextFilters.year.toString())
      if (nextFilters.month) params.append('month', nextFilters.month.toString())
      if (nextFilters.startDate) params.append('start_date', nextFilters.startDate)
      if (nextFilters.endDate) params.append('end_date', nextFilters.endDate)
      
      if (selectedCategories && selectedCategories.length > 0) {
        params.append('categories', selectedCategories.join(','))
      }
      if (selectedBrands && selectedBrands.length > 0) {
        params.append('brands', selectedBrands.join(','))
      }
      if (selectedCustomerType) params.append('customer_type', selectedCustomerType)
      if (selectedApprovalStatus) params.append('approval_status', selectedApprovalStatus)
      if (selectedRegion) params.append('region', selectedRegion)
      
      const queryString = params.toString()
      const url = `/veri-kaynaklari/${selectedDataSourceId}/yeni-musteriler/${queryString ? '?' + queryString : ''}`
      
      const response = await apiClient.get(url)
      setData(response.data)
    } catch (err: any) {
        setData(null)
        const errorMsg = err?.response?.data?.error || err?.message || 'Yeni müşteri verileri alınamadı'
        setError(errorMsg)
        notifications.show({
          title: 'Hata',
          message: errorMsg,
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
    } finally {
      setInitialLoading(false)
      setFilterLoading(false)
      setIsFirstLoad(false)
    }
  }

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (data && data.summary) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Yeni Müşteriler', {
        page: 'new_customers',
        data_source_id: selectedDataSourceId,
        summary: data.summary,
        total_new: data.summary.totalNewCustomers,
        growth: data.summary.growthRate
      });
    }
  }, [data, selectedDataSourceId]);

  // Full page error block removed for better UX consistency

  if (!selectedDataSourceId) return <div style={{ padding: '24px', textAlign: 'center' }}>Veri kaynağı seçiniz.</div>

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Yeni Müşteri Analizi</h1>
        <AISummaryButton 
          contextType="yeni_musteriler" 
          contextId={selectedDataSourceId} 
          contextData={{ new_customers: data?.summary?.totalNewCustomers }}
        />
      </div>

      {data && !initialLoading && (
        <div style={{ marginBottom: '24px' }}>
          <AIInsightCard 
            contextType="yeni_musteriler" 
            contextId={selectedDataSourceId.toString()} 
            title="Yeni Müşteri Kazanım Analizi"
            data={data}
          />
        </div>
      )}

      <LoadingOverlay loading={initialLoading || filterLoading}>
        {!data ? (
          <div style={{ height: 240 }} />
        ) : (
          <div style={{ display: 'grid', gap: '24px' }}>
            {/* Özet Kartlar */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
              <KpiCard {...KPI_COLORS.indigo} label="Dönem Toplam Yeni Müşteri" value={data.summary.totalNewCustomers?.toLocaleString('tr-TR') || '0'} />
              <KpiCard {...KPI_COLORS.green} label="Bu Ayki Yeni Müşteri" value={data.summary.newCustomersThisMonth?.toLocaleString('tr-TR') || '0'} />
              <KpiCard {...KPI_COLORS.blue} label="Büyüme Oranı" value={`${(data.summary.growthRate ?? 0) > 0 ? '+' : ''}%${data.summary.growthRate ?? 0}`} />
              <KpiCard {...KPI_COLORS.amber} label="Ort. İlk Sipariş" value={`₺${(data.summary.avgFirstOrder ?? 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}`} />
              <KpiCard {...KPI_COLORS.pink} label="Elde Tutma Oranı" value={`%${data.summary.retentionRate}`} />
            </div>

        {/* Aylık Trend */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ marginBottom: '20px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937' }}>
            Aylık Yeni Müşteri Trendi (Son 12 Ay)
          </h2>
          <div style={{ 
            display: 'flex', 
            gap: '12px', 
            alignItems: 'flex-end', 
            height: '240px', 
            padding: '20px 10px',
            position: 'relative'
          }}>
            {data.monthlyTrend?.slice(-12).map((item: any, idx: number, arr: any[]) => {
              const maxCount = Math.max(...arr.map((t: any) => t.count || 0), 1);
              const actualIdx = data.monthlyTrend.indexOf(item);
              const prevItem = data.monthlyTrend[actualIdx - 1];
              const growth = prevItem && prevItem.count > 0 
                ? ((item.count - prevItem.count) / prevItem.count) * 100 
                : 0;
              const isHovered = hoveredIdx === idx;

              return (
                <div 
                  key={idx} 
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                >
                  {/* Tooltip */}
                  {isHovered && (
                    <div style={{
                      position: 'absolute',
                      bottom: `${(item.count / maxCount) * 160 + 50}px`,
                      background: '#1f2937',
                      color: 'white',
                      padding: '12px 16px',
                      borderRadius: '12px',
                      fontSize: '0.875rem',
                      zIndex: 100,
                      boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                      whiteSpace: 'nowrap',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      alignItems: 'center'
                    }}>
                      <div style={{ fontWeight: 600, opacity: 0.9 }}>{item.month}</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{item.count.toLocaleString()} <span style={{fontSize: '0.75rem', fontWeight: 400, opacity: 0.8}}>Müşteri</span></div>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '4px',
                        color: growth >= 0 ? '#34d399' : '#f87171',
                        fontWeight: 600
                      }}>
                        {growth >= 0 ? '↑' : '↓'} %{formatPercent(Math.abs(growth))}
                        <span style={{ fontSize: '0.7rem', opacity: 0.8, color: 'white' }}> vs geçen ay</span>
                      </div>
                      {/* Tooltip Arrow */}
                      <div style={{
                        position: 'absolute',
                        bottom: '-6px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        width: 0,
                        height: 0,
                        borderLeft: '6px solid transparent',
                        borderRight: '6px solid transparent',
                        borderTop: '6px solid #1f2937'
                      }} />
                    </div>
                  )}

                  <div style={{
                    width: '32px',
                    background: isHovered ? '#ea580c' : '#fdba74',
                    borderRadius: '6px',
                    height: `${(item.count / maxCount) * 160}px`,
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    cursor: 'pointer',
                    boxShadow: isHovered ? '0 8px 20px rgba(234, 88, 12, 0.3)' : 'none',
                    border: isHovered ? '2px solid white' : 'none'
                  }} />
                      <div style={{ 
                        marginTop: '12px', 
                        fontSize: '0.75rem', 
                        fontWeight: 600, 
                        color: isHovered ? '#1f2937' : '#6b7280',
                        textTransform: 'uppercase'
                      }}>
                        {new Date(item.month).toLocaleDateString('tr-TR', { month: 'short', year: '2-digit' })}
                      </div>
                    </div>
                  );
                })}
              </div>
        </div>

        {/* Kazanım Kanalları */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ marginBottom: '20px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937' }}>
            {data?.acquisitionSource === 'segment' ? 'Yeni Müşteri Segment Dağılımı' : 
             data?.acquisitionSource === 'store' ? 'Mağaza Bazlı Müşteri Dağılımı' : 'Müşteri Kazanım Kanalları'}
          </h2>
          <div style={{ display: 'grid', gap: '16px', maxHeight: '600px', overflowY: 'auto', paddingRight: '8px' }}>
            {data?.acquisitionChannels.map((channel: any, idx: number) => (
              <div
                key={idx}
                style={{
                  padding: '20px',
                  borderRadius: '12px',
                  background: '#f9fafb',
                  border: '1px solid #e5e7eb'
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 150px 150px', gap: '20px', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '1.05rem', marginBottom: '4px' }}>
                      {channel.channel}
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      %{channel.percentage} pay
                    </div>
                  </div>

                  <div>
                    <div style={{
                      height: '12px',
                      background: '#e5e7eb',
                      borderRadius: '6px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${channel.percentage}%`,
                        background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
                        transition: 'width 0.3s'
                      }} />
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '4px' }}>
                      {channel.count} müşteri
                    </div>
                  </div>

                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      Ort. İlk Sepet
                    </div>
                    <div style={{ fontWeight: 600, color: '#10b981' }}>
                      ₺{channel.avg_first_order.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
                    </div>
                  </div>

                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      Toplam Ciro
                    </div>
                    <div style={{ fontWeight: 600, color: '#6366f1' }}>
                       ₺{channel.total_revenue.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Son Katılan Müşteriler */}
        {data?.recentCustomers && data.recentCustomers.length > 0 && (
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ marginBottom: '20px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937' }}>
              Son Katılan Müşteriler
            </h2>
            <div style={{ display: 'grid', gap: '12px' }}>
              {data.recentCustomers.map((customer: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    padding: '16px 20px',
                    borderRadius: '12px',
                    background: '#f9fafb',
                    border: '1px solid #e5e7eb',
                    display: 'grid',
                    gridTemplateColumns: '120px 150px 150px 120px 1fr',
                    gap: '16px',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      Müşteri ID
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#111827' }}>
                      {customer.id}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      Katılma Tarihi
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                      {customer.joinDate}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      İlk Sipariş
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#10b981' }}>
                      ₺{customer.firstOrder.toLocaleString()}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      Durum
                    </div>
                    <span style={{
                      display: 'inline-block',
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '0.875rem',
                      fontWeight: 600,
                      background: customer.status === 'Aktif' ? '#d1fae5' : '#dbeafe',
                      color: customer.status === 'Aktif' ? '#065f46' : '#1e40af'
                    }}>
                      {customer.status}
                    </span>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '4px' }}>
                      Segment
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#6366f1' }}>
                      {customer.segment}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
          </div>
        )}
      </LoadingOverlay>
    </div>
  )
}
