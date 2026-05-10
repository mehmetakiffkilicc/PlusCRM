import { useState, useEffect } from 'react'
import { formatPercent } from '../utils/format'
import {
  Text, Group, Badge, Loader, Center, Stack,
  SimpleGrid, Table, ScrollArea, Progress, Alert
} from '@mantine/core'
import { IconHome, IconUsers, IconChartBar, IconAlertCircle } from '@tabler/icons-react'
import ReactECharts from 'echarts-for-react'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import { useNavigate } from 'react-router-dom'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/PageLayout.css'

interface HaneDagilim {
  tip: string
  kolon: string
  musteri_sayisi: number
  ort_skor: number
  yuksek_skor_sayisi: number
}

interface SegmentHane {
  rfm_segment: string
  toplam: number
  baskin_hane: string
  baskin_skor: number
  skorlar: Record<string, number>
}

interface HaneData {
  hane_dagilim: HaneDagilim[]
  segment_hane: SegmentHane[]
  cocuklu_aile_liste: any[]
}

const HANE_RENKLER: Record<string, string> = {
  'Bekar': '#6366f1', 'Çift': '#ec4899', 'Aile': '#10b981',
  'Çocuklu': '#f59e0b', 'Bebek': '#f97316', 'Yaşlı': '#64748b',
  'Evcil Hayvan': '#14b8a6', 'Araba': '#8b5cf6'
}

export default function HaneAnalizi() {
  const { selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion } = useDashboardStore()
  const navigate = useNavigate()
  const [data, setData] = useState<HaneData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedDataSourceId) return
    setLoading(true)
    setError(null)
    apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/hane-analizi/`, {
      params: {
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined,
        region: selectedRegion || undefined,
      }
    })
      .then(res => {
        setData(res.data)
        if (res.data) {
          useChatStore.getState().attachPageContext('Hane Analizi', {
            page: 'hane-analizi',
            data_source_id: selectedDataSourceId,
            categories_count: res.data.hane_dagilim?.length,
            segments_count: res.data.segment_hane?.length
          });
        }
      })
      .catch(err => {
        console.error('Hane analizi yüklenemedi:', err)
        notifications.show({
          title: 'Hata',
          message: 'Hane analizi verileri yüklenirken bir hata oluştu.',
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
        setError('Veri yükleme hatası.')
      })
      .finally(() => setLoading(false))
  }, [selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  if (!selectedDataSourceId) {
    return <div className="page-content"><Center h={400}><Text c="dimmed">Veri kaynağı seçin</Text></Center></div>
  }

  const dagilim = data?.hane_dagilim ?? []
  const segmentler = data?.segment_hane ?? []
  const cocukluListe = data?.cocuklu_aile_liste ?? []

  const radarSegmentler = segmentler.slice(0, 5)
  const haneTipler = ['Bekar', 'Çift', 'Aile', 'Çocuklu', 'Bebek', 'Yaşlı', 'Evcil', 'Araba']

  const radarOption = radarSegmentler.length > 0 ? {
    tooltip: { trigger: 'item' },
    legend: { data: radarSegmentler.map(s => s.rfm_segment), bottom: 0, textStyle: { fontSize: 10 } },
    radar: { indicator: haneTipler.map(t => ({ name: t, max: 1 })), radius: '65%' },
    series: [{
      type: 'radar',
      data: radarSegmentler.map(s => ({
        name: s.rfm_segment,
        value: haneTipler.map(t => {
          const k = t === 'Evcil' ? 'Evcil Hayvan' : t
          return s.skorlar[k] ?? s.skorlar[t.toLowerCase()] ?? 0
        }),
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.1 }
      }))
    }]
  } : null

  const barOption = dagilim.length > 0 ? {
    tooltip: { trigger: 'axis' },
    grid: { top: 10, left: 10, right: 20, bottom: 0, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: dagilim.map(d => d.tip).reverse(), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: dagilim.map(d => d.yuksek_skor_sayisi).reverse(),
      itemStyle: {
        color: (p: any) => HANE_RENKLER[dagilim[dagilim.length - 1 - p.dataIndex]?.tip] ?? '#6366f1',
        borderRadius: [0, 4, 4, 0]
      },
      label: { show: true, position: 'right', fontSize: 11 }
    }]
  } : null

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Hane Tipi ve Yaşam Evresi Analizi</h1>
        <AISummaryButton 
          contextType="hane_analizi" 
          contextId={selectedDataSourceId} 
          contextData={{ categories_count: data?.hane_dagilim?.length }}
        />
      </div>

      {data && !loading && (
        <div style={{ marginBottom: '24px' }}>
          <AIInsightCard
            contextType="hane_analizi"
            contextId={selectedDataSourceId.toString()}
            title="Hane Profili AI Yorumu"
          />
        </div>
      )}
      {loading ? (
        <Center h={400}>
          <Stack align="center" gap="sm">
            <Loader size="lg" color="indigo" />
            <Text c="dimmed">Hane analizi yükleniyor...</Text>
          </Stack>
        </Center>
      ) : error ? (
        <Alert icon={<IconAlertCircle size={16} />} title="Veri Yüklenemedi" color="red" mb="md" variant="light">
          {error}
        </Alert>
      ) : !data ? (
        <div className="page-empty-state">
          <IconHome size={56} stroke={1.5} color="#9ca3af" />
          <Text c="dimmed">Veri bulunamadı</Text>
          <Text size="xs" c="dimmed">musterietiketler tablosunda hane skorları gerekli</Text>
        </div>
      ) : (
        <>
          {/* KPI summary */}
          <div className="kpi-summary-grid">
            <div className="kpi-gradient-card kpi-gradient-indigo">
              <div className="kpi-card-label">Analiz Edilen Hane Tipi</div>
              <div className="kpi-card-value">{dagilim.length}</div>
              <div className="kpi-card-sub">Farklı hane kategorisi</div>
              <div className="kpi-card-icon"><IconHome size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-green">
              <div className="kpi-card-label">Toplam Segment</div>
              <div className="kpi-card-value">{segmentler.length}</div>
              <div className="kpi-card-sub">RFM segmenti</div>
              <div className="kpi-card-icon"><IconUsers size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-amber">
              <div className="kpi-card-label">En Büyük Hane Tipi</div>
              <div className="kpi-card-value" style={{ fontSize: '1.4rem' }}>
                {dagilim.length > 0 ? dagilim.reduce((a, b) => a.yuksek_skor_sayisi > b.yuksek_skor_sayisi ? a : b).tip : '—'}
              </div>
              <div className="kpi-card-sub">
                {dagilim.length > 0 ? dagilim.reduce((a, b) => a.yuksek_skor_sayisi > b.yuksek_skor_sayisi ? a : b).yuksek_skor_sayisi.toLocaleString('tr-TR') + ' müşteri' : ''}
              </div>
              <div className="kpi-card-icon"><IconChartBar size={100} stroke={1.5} /></div>
            </div>
          </div>

          {/* Charts */}
          <SimpleGrid cols={2}>
            <div className="section-card">
              <p className="section-card-title">Hane Tipi Dağılımı (Yüksek Skor ≥0.6)</p>
              {barOption ? (
                <ReactECharts option={barOption} style={{ height: 280 }} />
              ) : (
                <Center h={200}><Text c="dimmed">Veri yok</Text></Center>
              )}
            </div>

            <div className="section-card">
              <p className="section-card-title">Segment Bazlı Hane Profili (Radar)</p>
              {radarOption ? (
                <ReactECharts option={radarOption} style={{ height: 280 }} />
              ) : (
                <Center h={200}><Text c="dimmed">Veri yok</Text></Center>
              )}
            </div>
          </SimpleGrid>

          {/* Hane tipi detay kartları */}
          <SimpleGrid cols={4}>
            {dagilim.map(d => (
              <div key={d.kolon} className="section-card" style={{ borderTop: `3px solid ${HANE_RENKLER[d.tip] ?? '#6366f1'}` }}>
                <Text fw={700} size="sm" style={{ color: HANE_RENKLER[d.tip] ?? '#6366f1' }}>{d.tip}</Text>
                <Text fw={800} size="xl" mt={4}>{d.yuksek_skor_sayisi.toLocaleString('tr-TR')}</Text>
                <Text size="xs" c="dimmed">Yüksek skor (≥0.6)</Text>
                <Group gap={4} mt={6}>
                  <Text size="xs" c="dimmed">Ort. Skor:</Text>
                  <Text size="xs" fw={600} style={{ color: HANE_RENKLER[d.tip] }}>%{formatPercent(d.ort_skor * 100)}</Text>
                </Group>
                <Progress value={d.ort_skor * 100} color={HANE_RENKLER[d.tip] ?? 'indigo'} size="xs" mt={4} />
              </div>
            ))}
          </SimpleGrid>

          {/* Segment bazlı baskın hane tipi tablosu */}
          {segmentler.length > 0 && (
            <div className="section-card-table">
              <div className="section-card-table-header" style={{ background: '#f8fafc' }}>
                <Text fw={700} size="sm">Segment Bazlı Baskın Hane Profili</Text>
              </div>
              <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Segment</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Müşteri</Table.Th>
                    <Table.Th>Baskın Hane Tipi</Table.Th>
                    {['Bekar', 'Çift', 'Aile', 'Çocuklu', 'Bebek', 'Yaşlı'].map(t => (
                      <Table.Th key={t} style={{ textAlign: 'center', fontSize: '0.72rem' }}>{t}</Table.Th>
                    ))}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {segmentler.map((s, i) => (
                    <Table.Tr key={i}>
                      <Table.Td><Text size="sm" fw={600}>{s.rfm_segment}</Text></Table.Td>
                      <Table.Td style={{ textAlign: 'right' }}>{s.toplam.toLocaleString('tr-TR')}</Table.Td>
                      <Table.Td>
                        <Badge size="sm" style={{ background: HANE_RENKLER[s.baskin_hane] + '20', color: HANE_RENKLER[s.baskin_hane] ?? '#6366f1', border: `1px solid ${HANE_RENKLER[s.baskin_hane] ?? '#6366f1'}30` }} variant="outline">
                          {s.baskin_hane}
                        </Badge>
                      </Table.Td>
                      {['Bekar', 'Çift', 'Aile', 'Çocuklu', 'Bebek', 'Yaşlı'].map(t => {
                        const v = s.skorlar[t] ?? 0
                        return (
                          <Table.Td key={t} style={{ textAlign: 'center', color: v >= 0.5 ? (HANE_RENKLER[t] ?? '#6366f1') : '#9ca3af', fontWeight: v >= 0.5 ? 700 : 400, fontSize: '0.75rem' }}>
                            {(v * 100).toFixed(0)}%
                          </Table.Td>
                        )
                      })}
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          )}

          {/* Yüksek değerli çocuklu aile listesi */}
          {cocukluListe.length > 0 && (
            <div className="section-card-table">
              <div className="section-card-table-header" style={{ background: '#fef3c7', borderBottom: '1px solid #fde68a' }}>
                <Text fw={700} size="sm" c="yellow.9">Yüksek Değerli Çocuklu Aileler — Top 30</Text>
                <Text size="xs" c="dimmed">Çocuklu/bebek skoru ≥0.5 olan en yüksek harcamalı müşteriler</Text>
              </div>
              <ScrollArea h={320}>
                <Table striped highlightOnHover withTableBorder fz="sm">
                  <Table.Thead style={{ position: 'sticky', top: 0, background: '#fffbeb', zIndex: 1 }}>
                    <Table.Tr>
                      <Table.Th>Müşteri</Table.Th>
                      <Table.Th>Segment</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Harcama</Table.Th>
                      <Table.Th style={{ textAlign: 'center' }}>Çocuklu</Table.Th>
                      <Table.Th style={{ textAlign: 'center' }}>Bebek</Table.Th>
                      <Table.Th style={{ textAlign: 'center' }}>Aile</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {cocukluListe.map((m: any, i: number) => (
                      <Table.Tr key={i} style={{ cursor: 'pointer' }}
                        onClick={() => navigate('/musteri-portali', { state: { customerId: m.id } })}>
                        <Table.Td><Text size="sm" fw={600} c="indigo.7">{m.ad}</Text></Table.Td>
                        <Table.Td><Badge size="xs" color="gray" variant="light">{m.rfm_segment || '—'}</Badge></Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>₺{Number(m.toplam_harcama || 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}</Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Badge size="xs" color="yellow" variant={Number(m.hane_cocuklu_skoru) >= 0.6 ? 'filled' : 'light'}>
                            {(Number(m.hane_cocuklu_skoru || 0) * 100).toFixed(0)}%
                          </Badge>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Badge size="xs" color="orange" variant={Number(m.hane_bebek_skoru) >= 0.6 ? 'filled' : 'light'}>
                            {(Number(m.hane_bebek_skoru || 0) * 100).toFixed(0)}%
                          </Badge>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Badge size="xs" color="green" variant={Number(m.hane_aile_skoru) >= 0.6 ? 'filled' : 'light'}>
                            {(Number(m.hane_aile_skoru || 0) * 100).toFixed(0)}%
                          </Badge>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            </div>
          )}
        </>
      )}
    </div>
  )
}
