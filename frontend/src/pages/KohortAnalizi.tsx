import { useState, useEffect } from 'react'
import { Text, Group, Badge, Loader, Center, Stack, Select, ScrollArea } from '@mantine/core'
import { IconChartBar, IconUsers, IconCalendarStats, IconAlertCircle } from '@tabler/icons-react'
import ReactECharts from 'echarts-for-react'
import { Alert } from '@mantine/core'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/PageLayout.css'

interface KohortAy {
  kohort_ay: string
  kohort_boyutu: number
  retention: Record<number, number>
}

interface KohortData {
  kohortlar: KohortAy[]
  max_ay: number
  toplam_kohort: number
}

function retentionRenk(deger: number): string {
  if (deger === 0) return '#f9fafb'
  if (deger < 10) return '#dcfce7'
  if (deger < 20) return '#bbf7d0'
  if (deger < 30) return '#86efac'
  if (deger < 40) return '#4ade80'
  if (deger < 55) return '#22c55e'
  if (deger < 70) return '#16a34a'
  return '#15803d'
}

function retentionMetnRenk(deger: number): string {
  return deger >= 40 ? '#fff' : '#1f2937'
}

export default function KohortAnalizi() {
  const { selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion } = useDashboardStore()
  const [data, setData] = useState<KohortData | null>(null)
  const [loading, setLoading] = useState(false)
  const [maxAy, setMaxAy] = useState('12')

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedDataSourceId) return
    setLoading(true)
    setError(null)
    apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/kohort-analizi/`, {
      params: {
        max_ay: maxAy,
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined,
        region: selectedRegion || undefined,
      }
    })
      .then(res => setData(res.data))
      .catch(err => {
        console.error('Kohort analizi yüklenemedi:', err)
        notifications.show({
          title: 'Hata',
          message: 'Kohort verileri hesaplanırken bir hata oluştu.',
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
        setError('Veri yükleme hatası.')
      })
      .finally(() => setLoading(false))
  }, [selectedDataSourceId, maxAy, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (data && data.kohortlar.length > 0) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Kohort Analizi', {
        page: 'kohort_analysis',
        data_source_id: selectedDataSourceId,
        max_ay: maxAy,
        total_cohorts: data.toplam_kohort,
        summary: {
           first_month_avg_retention: avgRetention[1] ?? 0,
           sixth_month_avg_retention: avgRetention[6] ?? 0
        }
      });
    }
  }, [data, selectedDataSourceId, maxAy]);

  if (!selectedDataSourceId) {
    return (
      <div className="page-content">
        <Center h={300}>
          <Stack align="center" gap="sm">
            <IconChartBar size={48} stroke={1.5} color="#9ca3af" />
            <Text c="dimmed">Veri kaynağı seçin</Text>
          </Stack>
        </Center>
      </div>
    )
  }

  const kohortlar = data?.kohortlar ?? []
  const maxAyInt = data?.max_ay ?? parseInt(maxAy)

  const ayIndeksler = Array.from({ length: Math.min(maxAyInt + 1, 13) }, (_, i) => i)

  const avgRetention: number[] = ayIndeksler.map(idx => {
    const degerler = kohortlar
      .map(k => k.retention[idx])
      .filter(v => v !== undefined && v !== null)
    return degerler.length > 0 ? Math.round(degerler.reduce((a, b) => a + b, 0) / degerler.length * 10) / 10 : 0
  })

  const avgChartOption = {
    tooltip: { trigger: 'axis', formatter: (p: any[]) => `Ay ${p[0].dataIndex}: Ort. %${p[0].value}` },
    grid: { top: 10, left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: ayIndeksler.map(i => `Ay ${i}`), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => `%${v}` }, max: 100 },
    series: [{
      type: 'line', data: avgRetention, smooth: true,
      lineStyle: { color: '#4f46e5', width: 2.5 },
      itemStyle: { color: '#4f46e5' },
      areaStyle: { color: 'rgba(79,70,229,0.10)' },
    }]
  }

  return (
    <div className="page-content">
      {/* Filter row */}
      <div className="page-filter-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Select
          label="Takip Süresi"
          value={maxAy}
          onChange={v => setMaxAy(v ?? '12')}
          data={[
            { value: '6', label: '6 Ay' },
            { value: '12', label: '12 Ay' },
            { value: '18', label: '18 Ay' },
            { value: '24', label: '24 Ay' },
          ]}
          size="sm"
          style={{ width: 120 }}
        />
        <AISummaryButton 
          contextType="kohort_analizi" 
          contextId={selectedDataSourceId} 
          contextData={{ max_ay: maxAy, cohort_count: data?.toplam_kohort }}
        />
      </div>

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} title="Hata" color="red" mb="md" variant="light">
          {error}
        </Alert>
      )}

      {data && !loading && (
        <div style={{ marginBottom: '20px' }}>
          <AIInsightCard 
            contextType="kohort_analizi" 
            contextId={selectedDataSourceId.toString()} 
            title="Kohort Analiz Yorumu"
            data={data}
          />
        </div>
      )}

      {loading ? (
        <Center h={400}>
          <Stack align="center" gap="sm">
            <Loader size="lg" color="indigo" />
            <Text c="dimmed">Kohort analizi hesaplanıyor...</Text>
          </Stack>
        </Center>
      ) : !data || kohortlar.length === 0 ? (
        <div className="page-empty-state">
          <IconChartBar size={56} stroke={1.5} color="#9ca3af" />
          <Text c="dimmed" size="lg">Kohort verisi bulunamadı</Text>
          <Text c="dimmed" size="sm">musteridetayozet tablosunda ilk alışveriş tarihi gerekli</Text>
        </div>
      ) : (
        <>
          {/* KPI Kartları */}
          <div className="kpi-summary-grid">
            <div className="kpi-gradient-card kpi-gradient-green">
              <div className="kpi-card-label">Toplam Kohort</div>
              <div className="kpi-card-value">{data.toplam_kohort}</div>
              <div className="kpi-card-sub">Farklı alışveriş ayı</div>
              <div className="kpi-card-icon"><IconUsers size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-indigo">
              <div className="kpi-card-label">İlk Ay Retention</div>
              <div className="kpi-card-value">%{avgRetention[1] ?? 0}</div>
              <div className="kpi-card-sub">Ortalama 1. ay geri dönüş</div>
              <div className="kpi-card-icon"><IconChartBar size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-orange">
              <div className="kpi-card-label">6. Ay Retention</div>
              <div className="kpi-card-value">%{avgRetention[6] ?? 0}</div>
              <div className="kpi-card-sub">Ortalama 6. ay geri dönüş</div>
              <div className="kpi-card-icon"><IconCalendarStats size={100} stroke={1.5} /></div>
            </div>
          </div>

          {/* Ortalama Retention Trendi */}
          <div className="section-card">
            <p className="section-card-title">Ortalama Retention Trendi (Tüm Kohortlar)</p>
            <ReactECharts option={avgChartOption} style={{ height: 200 }} />
          </div>

          {/* Kohort Matrisi */}
          <div className="section-card">
            <Group justify="space-between" mb="md">
              <p className="section-card-title" style={{ margin: 0 }}>Kohort Retention Matrisi</p>
              <Group gap="xs">
                {[0, 10, 30, 50, 70].map(v => (
                  <Group key={v} gap={4}>
                    <div style={{ width: 16, height: 16, borderRadius: 3, background: retentionRenk(v), border: '1px solid #e5e7eb' }} />
                    <Text size="xs" c="dimmed">%{v}+</Text>
                  </Group>
                ))}
              </Group>
            </Group>

            <ScrollArea>
              <table style={{ borderCollapse: 'collapse', fontSize: '0.78rem', minWidth: '600px', width: '100%' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '6px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 700, borderBottom: '2px solid #e5e7eb', whiteSpace: 'nowrap', minWidth: '90px' }}>
                      Kohort
                    </th>
                    <th style={{ padding: '6px 8px', textAlign: 'center', color: '#6b7280', fontWeight: 700, borderBottom: '2px solid #e5e7eb', whiteSpace: 'nowrap' }}>
                      Boyut
                    </th>
                    {ayIndeksler.map(idx => (
                      <th key={idx} style={{ padding: '6px 8px', textAlign: 'center', color: '#6b7280', fontWeight: 700, borderBottom: '2px solid #e5e7eb', whiteSpace: 'nowrap' }}>
                        Ay {idx}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {kohortlar.map(k => (
                    <tr key={k.kohort_ay}>
                      <td style={{ padding: '4px 10px', fontWeight: 600, color: '#374151', borderBottom: '1px solid #f3f4f6', whiteSpace: 'nowrap' }}>
                        {k.kohort_ay}
                      </td>
                      <td style={{ padding: '4px 8px', textAlign: 'center', color: '#6b7280', borderBottom: '1px solid #f3f4f6' }}>
                        <Badge size="xs" color="gray" variant="light">{k.kohort_boyutu.toLocaleString('tr-TR')}</Badge>
                      </td>
                      {ayIndeksler.map(idx => {
                        const val = k.retention[idx]
                        const isEmpty = val === undefined || val === null
                        const bg = isEmpty ? '#f3f4f6' : retentionRenk(val)
                        const color = isEmpty ? '#d1d5db' : retentionMetnRenk(val)
                        return (
                          <td key={idx} style={{
                            padding: '4px 6px', textAlign: 'center', borderBottom: '1px solid #f3f4f6',
                            background: bg, color,
                            fontWeight: val >= 20 ? 700 : 400, transition: 'opacity 0.1s',
                            minWidth: '52px'
                          }}>
                            {isEmpty ? '—' : `%${val}`}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                  {/* Ortalama Satırı */}
                  <tr style={{ background: '#f8fafc' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 700, color: '#374151', borderTop: '2px solid #e5e7eb' }}>
                      Ortalama
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center', borderTop: '2px solid #e5e7eb' }}></td>
                    {ayIndeksler.map(idx => {
                      const avg = avgRetention[idx] ?? 0
                      return (
                        <td key={idx} style={{
                          padding: '6px 6px', textAlign: 'center', fontWeight: 700,
                          color: avg >= 30 ? '#16a34a' : avg >= 10 ? '#d97706' : '#dc2626',
                          borderTop: '2px solid #e5e7eb'
                        }}>
                          %{avg}
                        </td>
                      )
                    })}
                  </tr>
                </tbody>
              </table>
            </ScrollArea>

            <Text size="xs" c="dimmed" mt="sm">
              Satır = İlk alışveriş ayı (kohort). Sütun = O aydan sonra kaçıncı aydalar. Değer = Kohorttaki müşterilerin o ayda alışveriş yapma oranı.
            </Text>
          </div>
        </>
      )}
    </div>
  )
}
