import { useState, useEffect } from 'react'
import { formatPercent } from '../utils/format'
import {
  IconUsers, IconUserCheck, IconAlertTriangle, IconUserX,
  IconChartBar, IconInfoCircle, IconTrendingUp, IconHeart
} from '@tabler/icons-react'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { notifications } from '@mantine/notifications'
import apiClient from '../api/client'
import FilterPanel, { FilterState } from '../components/FilterPanel'
import LoadingOverlay from '../components/LoadingOverlay'
import useDashboardStore from '../stores/dashboardStore'
import { useChatStore } from '../stores/chatStore'
import '../styles/DashboardHome.css'

interface ChurnData {
  summary: {
    totalCustomers: number
    activeCustomers: number
    churnedCustomers: number
    churnRate: number
    atRiskCustomers: number
    totalChurnCount?: number
  }
  churnByMonth: { month: string; churned: number; rate: number }[]
  riskFactors: { factor: string; count: number; percentage: number }[]
  atRiskCustomers: { id: string; name: string; lastPurchase: string; riskScore: number; totalSpent: number }[]
}

const emptyData: ChurnData = {
  summary: { totalCustomers: 0, activeCustomers: 0, churnedCustomers: 0, churnRate: 0, atRiskCustomers: 0 },
  churnByMonth: [],
  riskFactors: [],
  atRiskCustomers: []
}

export default function ChurnAnalysis() {
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
  const [error, setError] = useState<string | null>(null)
  const [churnData, setChurnData] = useState<ChurnData>(emptyData)

  // İlk yükleme veya Data Source değişimi
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

  // Filtre değiştiğinde (yıl/ay store'dan değişirse tetikle)
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

      const data = await apiClient.getChurnAnalysis(selectedDataSourceId, params)
      setChurnData(data || emptyData)
    } catch (err: any) {
      setChurnData(emptyData)
      notifications.show({
        title: 'Hata',
        message: 'Churn verileri yüklenirken bir hata oluştu.',
        color: 'red'
      })
    } finally {
      setInitialLoading(false)
      setFilterLoading(false)
    }
  }

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (hasData) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Churn Analizi', {
        page: 'churn_analysis',
        data_source_id: selectedDataSourceId,
        summary_data: {
          churn_rate: summary.churnRate,
          total_customers: summary.totalCustomers,
          at_risk: summary.atRiskCustomers,
          active: summary.activeCustomers
        },
        risk_factors: churnData.riskFactors.slice(0, 3)
      });
    }
  }, [churnData, selectedDataSourceId]);

  if (!selectedDataSourceId) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ marginBottom: '16px' }}><IconChartBar size={48} stroke={1.5} color="#6366f1" /></div>
        <div style={{ color: '#6b7280', fontSize: '1.1rem' }}>Lütfen bir veri kaynağı seçin</div>
      </div>
    )
  }

  const { summary } = churnData
  const hasData = summary && summary.totalCustomers > 0

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Müşteri Terk (Churn) Analizi</h1>
        <AISummaryButton 
          contextType="churn_analysis" 
          contextId={selectedDataSourceId} 
          contextData={{ churn_rate: summary.churnRate }}
        />
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
          <h2 style={{ color: '#374151', marginBottom: '8px' }}>Veri Bulunamadı</h2>
          <p style={{ color: '#6b7280' }}>
            Churn analizi için müşteri verisi gereklidir. Veri kaynağınızda müşteri ID sütunu olduğundan emin olun.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '24px' }}>

          <AIInsightCard 
            contextType="churn_analysis" 
            contextId={selectedDataSourceId?.toString()} 
            title="Churn (Kayıp) Analizi ve Risk Değerlendirmesi"
            data={churnData}
          />

          {/* Özet Kartlar */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
            <KpiCard
              {...KPI_COLORS.indigo}
              label="Toplam Müşteri"
              value={summary.totalCustomers.toLocaleString('tr-TR')}
              icon={<IconUsers size={110} stroke={1.5} />}
            />
            <KpiCard
              {...KPI_COLORS.green}
              label="Aktif Müşteri"
              value={summary.activeCustomers.toLocaleString('tr-TR')}
              sub={`%${summary.totalCustomers > 0 ? formatPercent((summary.activeCustomers / summary.totalCustomers) * 100) : 0} aktif oran`}
              icon={<IconUserCheck size={110} stroke={1.5} />}
            />
            <KpiCard
              {...KPI_COLORS.amber}
              label="Risk Altında"
              value={summary.atRiskCustomers.toLocaleString('tr-TR')}
              sub={`%${summary.totalCustomers > 0 ? formatPercent((summary.atRiskCustomers / summary.totalCustomers) * 100) : 0} risk oranı`}
              icon={<IconAlertTriangle size={110} stroke={1.5} />}
            />
            <KpiCard
              {...KPI_COLORS.red}
              label="Churn Oranı"
              value={summary.churnedCustomers.toLocaleString('tr-TR')}
              sub={`%${summary.churnRate} churn oranı`}
              icon={<IconUserX size={110} stroke={1.5} />}
            />
          </div>

          {/* Churn Dağılımı */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
            {/* Müşteri Durumu */}
            <div style={{
              background: 'white',
              borderRadius: '16px',
              padding: '24px',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
            }}>
              <h2 style={{ marginBottom: '24px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <IconChartBar size={22} color="#10b981" />
                Müşteri Durum Dağılımı
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>Aktif</span>
                    <span style={{ fontWeight: 600 }}>{summary.activeCustomers}</span>
                  </div>
                  <div style={{ height: '12px', background: '#f3f4f6', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(summary.activeCustomers / summary.totalCustomers) * 100}%`,
                      background: '#10b981',
                      transition: 'width 0.5s'
                    }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ color: '#f59e0b', fontWeight: 600 }}>Risk Altında</span>
                    <span style={{ fontWeight: 600 }}>{summary.atRiskCustomers}</span>
                  </div>
                  <div style={{ height: '12px', background: '#f3f4f6', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(summary.atRiskCustomers / summary.totalCustomers) * 100}%`,
                      background: '#f59e0b',
                      transition: 'width 0.5s'
                    }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ color: '#ef4444', fontWeight: 600 }}>Churn</span>
                    <span style={{ fontWeight: 600 }}>{summary.churnedCustomers}</span>
                  </div>
                  <div style={{ height: '12px', background: '#f3f4f6', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(summary.churnedCustomers / summary.totalCustomers) * 100}%`,
                      background: '#ef4444',
                      transition: 'width 0.5s'
                    }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Özet İstatistikler - Premium Görünüm */}
            <div style={{
              background: 'white',
              borderRadius: '16px',
              padding: '24px',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
            }}>
              <h2 style={{ marginBottom: '24px', fontSize: '1.15rem', fontWeight: 600, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <IconTrendingUp size={22} color="#ef4444" />
                Churn Metrikleri
              </h2>
              <div style={{ display: 'grid', gap: '20px' }}>
                {/* Aktif Oran */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ padding: '6px', background: '#10b98120', borderRadius: '8px', color: '#10b981' }}>
                        <IconUserCheck size={18} stroke={2} />
                      </div>
                      <span style={{ fontWeight: 600, color: '#374151', fontSize: '0.9rem' }}>Aktif Oran</span>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '1rem', color: '#10b981' }}>
                      %{summary.totalCustomers > 0 ? formatPercent((summary.activeCustomers / summary.totalCustomers) * 100) : 0}
                    </span>
                  </div>
                  <div style={{ height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${summary.totalCustomers > 0 ? ((summary.activeCustomers / summary.totalCustomers) * 100) : 0}%`, background: 'linear-gradient(90deg, #34d399, #10b981)', borderRadius: '4px' }} />
                  </div>
                </div>

                {/* Risk Oranı */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ padding: '6px', background: '#f59e0b20', borderRadius: '8px', color: '#f59e0b' }}>
                        <IconAlertTriangle size={18} stroke={2} />
                      </div>
                      <span style={{ fontWeight: 600, color: '#374151', fontSize: '0.9rem' }}>Risk Oranı</span>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '1rem', color: '#f59e0b' }}>
                      %{summary.totalCustomers > 0 ? formatPercent((summary.atRiskCustomers / summary.totalCustomers) * 100) : 0}
                    </span>
                  </div>
                  <div style={{ height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${summary.totalCustomers > 0 ? ((summary.atRiskCustomers / summary.totalCustomers) * 100) : 0}%`, background: 'linear-gradient(90deg, #fbbf24, #f59e0b)', borderRadius: '4px' }} />
                  </div>
                </div>

                {/* Churn Oranı */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ padding: '6px', background: '#ef444420', borderRadius: '8px', color: '#ef4444' }}>
                        <IconUserX size={18} stroke={2} />
                      </div>
                      <span style={{ fontWeight: 600, color: '#374151', fontSize: '0.9rem' }}>Churn Oranı</span>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '1rem', color: '#ef4444' }}>
                      %{summary.churnRate}
                    </span>
                  </div>
                  <div style={{ height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${summary.churnRate}%`, background: 'linear-gradient(90deg, #f87171, #ef4444)', borderRadius: '4px' }} />
                  </div>
                </div>

                {/* Elde Tutma Oranı */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ padding: '6px', background: '#6366f120', borderRadius: '8px', color: '#6366f1' }}>
                        <IconHeart size={18} stroke={2} />
                      </div>
                      <span style={{ fontWeight: 600, color: '#374151', fontSize: '0.9rem' }}>Elde Tutma Oranı</span>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '1rem', color: '#6366f1' }}>
                       %{formatPercent(100 - summary.churnRate)}
                    </span>
                  </div>
                  <div style={{ height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${100 - summary.churnRate}%`, background: 'linear-gradient(90deg, #818cf8, #6366f1)', borderRadius: '4px' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bilgilendirme */}
          <div style={{
            background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
            borderRadius: '16px',
            padding: '24px',
            border: '1px solid #bae6fd'
          }}>
            <h3 style={{ color: '#0369a1', marginBottom: '12px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <IconInfoCircle size={20} stroke={2} /> Churn Tanımları
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', fontSize: '0.9rem', color: '#0c4a6e' }}>
              <div><strong>Aktif:</strong> Son 30 günde alışveriş yapan müşteriler</div>
              <div><strong>Risk Altında:</strong> 31-120 gün arası alışveriş yapmayan müşteriler</div>
              <div><strong>Churn (Kayıp):</strong> 120 günden fazla alışveriş yapmayan müşteriler</div>
            </div>
          </div>
        </div>
      )}
      </LoadingOverlay>
    </div>
  )
}
