import { useState, useEffect } from 'react'
import { formatPercent } from '../utils/format'
import {
  Text, Group, Badge, Loader, Center, Stack,
  Table, ScrollArea, Alert
} from '@mantine/core'
import { 
  IconTrendingUp, IconTrendingDown, IconMinus, IconCoin, 
  IconUsers, IconAlertTriangle, IconAlertCircle 
} from '@tabler/icons-react'
import ReactECharts from 'echarts-for-react'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import { useNavigate } from 'react-router-dom'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/PageLayout.css'

interface SegmentAnaliz {
  rfm_segment: string
  musteri_sayisi: number
  ort_indirim_oran: number
  ort_indirim_yuzde: number
  ort_harcama_degisim_3ay: number
  ort_ziyaret_degisim_3ay: number
  ort_harcama_degisim_6ay: number
  stokcu_sayisi: number
  fiyat_hassas_sayisi: number
}

interface EnflasyonData {
  segment_analiz: SegmentAnaliz[]
  stokcu_liste: any[]
  ozet: {
    toplam_musteri: number
    stokcu_sayisi: number
    fiyat_hassas_sayisi: number
    genel_indirim_oran: number
    genel_harcama_degisim: number
  }
}

export default function EnflasyonProfil() {
  const { selectedDataSourceId } = useDashboardStore()
  const navigate = useNavigate()
  const [data, setData] = useState<EnflasyonData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedDataSourceId) return
    setLoading(true)
    setError(null)
    apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/enflasyon-dayaniklilik/`)
      .then(res => {
        setData(res.data)
        // AI Bağlamını Güncelle
        if (res.data) {
          useChatStore.getState().attachPageContext('Enflasyon Analizi', {
            page: 'enflasyon-profil',
            data_source_id: selectedDataSourceId,
            summary: res.data.ozet,
            segments_count: res.data.segment_analiz?.length,
            stokcu_count: res.data.ozet?.stokcu_sayisi
          });
        }
      })
      .catch(err => {
        console.error('Enflasyon profili yüklenemedi:', err)
        notifications.show({
          title: 'Hata',
          message: 'Enflasyon dayanıklılık verileri yüklenirken bir hata oluştu.',
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
        setError('Veri yükleme hatası.')
      })
      .finally(() => setLoading(false))
  }, [selectedDataSourceId])

  if (!selectedDataSourceId) {
    return <div className="page-content"><Center h={400}><Text c="dimmed">Veri kaynağı seçin</Text></Center></div>
  }

  const ozet = data?.ozet
  const segmentler = data?.segment_analiz ?? []
  const stokcu = data?.stokcu_liste ?? []

  const harcamaDegisimOption = segmentler.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['3 Ay Harcama Δ', '3 Ay Ziyaret Δ'], bottom: 0 },
    grid: { top: 10, left: 10, right: 20, bottom: 40, containLabel: true },
    xAxis: { type: 'category', data: segmentler.map(s => s.rfm_segment.length > 12 ? s.rfm_segment.slice(0, 12) + '…' : s.rfm_segment), axisLabel: { rotate: 20, fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => `%${v}` } },
    series: [
      {
        name: '3 Ay Harcama Δ', type: 'bar', barMaxWidth: 30,
        data: segmentler.map(s => Number(s.ort_harcama_degisim_3ay ?? 0).toFixed(1)),
        itemStyle: { color: (p: any) => Number(segmentler[p.dataIndex].ort_harcama_degisim_3ay) >= 0 ? '#16a34a' : '#dc2626', borderRadius: [3, 3, 0, 0] }
      },
      {
        name: '3 Ay Ziyaret Δ', type: 'line', smooth: true,
        data: segmentler.map(s => Number(s.ort_ziyaret_degisim_3ay ?? 0).toFixed(1)),
        lineStyle: { color: '#4f46e5' }, itemStyle: { color: '#4f46e5' }
      }
    ]
  } : null

  const genel_harcama = Number(ozet?.genel_harcama_degisim ?? 0)

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Enflasyon Dayanıklılık ve Stokçu Analizi</h1>
        <AISummaryButton 
          contextType="enflasyon_analizi" 
          contextId={selectedDataSourceId} 
          contextData={{ total_customers: data?.ozet?.toplam_musteri }}
        />
      </div>

      {data && !loading && (
        <div style={{ marginBottom: '24px' }}>
          <AIInsightCard
            contextType="enflasyon_analizi"
            contextId={selectedDataSourceId.toString()}
            title="Enflasyon Davranış Analizi AI Yorumu"
          />
        </div>
      )}
      {loading ? (
        <Center h={400}>
          <Stack align="center" gap="sm">
            <Loader size="lg" color="indigo" />
            <Text c="dimmed">Analiz yükleniyor...</Text>
          </Stack>
        </Center>
      ) : error ? (
        <Alert icon={<IconAlertCircle size={16} />} title="Veri Yüklenemedi" color="red" mb="md" variant="light">
          {error}
        </Alert>
      ) : !data ? (
        <div className="page-empty-state">
          <IconCoin size={56} stroke={1.5} color="#9ca3af" />
          <Text c="dimmed">Veri bulunamadı</Text>
          <Text size="xs" c="dimmed">musterifiyatfeatures ve musteridonem_karsilastirma tabloları gerekli</Text>
        </div>
      ) : (
        <>
          {/* KPI */}
          <div className="kpi-summary-grid">
            <div className="kpi-gradient-card kpi-gradient-indigo">
              <div className="kpi-card-label">Analiz Edilen Müşteri</div>
              <div className="kpi-card-value">{Number(ozet?.toplam_musteri ?? 0).toLocaleString('tr-TR')}</div>
              <div className="kpi-card-icon"><IconUsers size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-amber">
              <div className="kpi-card-label">Enflasyon Stokçusu</div>
              <div className="kpi-card-value">{(ozet?.stokcu_sayisi ?? 0).toLocaleString('tr-TR')}</div>
              <div className="kpi-card-sub">
                %{ozet?.toplam_musteri ? Math.round(Number(ozet.stokcu_sayisi) / Number(ozet.toplam_musteri) * 100) : 0} oran
              </div>
              <div className="kpi-card-icon"><IconCoin size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-red">
              <div className="kpi-card-label">Fiyat Hassas</div>
              <div className="kpi-card-value">{Number(ozet?.fiyat_hassas_sayisi ?? 0).toLocaleString('tr-TR')}</div>
              <div className="kpi-card-sub">
                %{ozet?.toplam_musteri ? Math.round(Number(ozet.fiyat_hassas_sayisi) / Number(ozet.toplam_musteri) * 100) : 0} oran
              </div>
              <div className="kpi-card-icon"><IconAlertTriangle size={100} stroke={1.5} /></div>
            </div>
            <div className={`kpi-gradient-card ${genel_harcama >= 0 ? 'kpi-gradient-green' : 'kpi-gradient-slate'}`}>
              <div className="kpi-card-label">Genel Ort. Harcama Δ</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {genel_harcama >= 0
                  ? <IconTrendingUp size={28} color="white" style={{ opacity: 0.9 }} />
                  : <IconTrendingDown size={28} color="white" style={{ opacity: 0.9 }} />}
                <div className="kpi-card-value">%{formatPercent(genel_harcama)}</div>
              </div>
              <div className="kpi-card-sub">Son 3 ay</div>
            </div>
          </div>

          {/* Segment bazlı harcama değişimi */}
          {harcamaDegisimOption && (
            <div className="section-card">
              <p className="section-card-title">Segment Bazlı Harcama & Ziyaret Değişimi (Son 3 Ay)</p>
              <ReactECharts option={harcamaDegisimOption} style={{ height: 280 }} />
            </div>
          )}

          {/* Segment tablosu */}
          {segmentler.length > 0 && (
            <div className="section-card-table">
              <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                <Table.Thead style={{ background: '#f8fafc' }}>
                  <Table.Tr>
                    <Table.Th>Segment</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Müşteri</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Ort. İndirim %</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Harcama Δ 3ay</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Ziyaret Δ 3ay</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Stokçu</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Fiyat Hassas</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {segmentler.map((s, i) => {
                    const hDegisim = Number(s.ort_harcama_degisim_3ay ?? 0)
                    const zDegisim = Number(s.ort_ziyaret_degisim_3ay ?? 0)
                    return (
                      <Table.Tr key={i}>
                        <Table.Td><Text size="sm" fw={600}>{s.rfm_segment}</Text></Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>{s.musteri_sayisi.toLocaleString('tr-TR')}</Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>%{formatPercent(Number(s.ort_indirim_oran ?? 0))}</Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Group justify="center" gap={4}>
                            {hDegisim > 2 ? <IconTrendingUp size={14} color="#16a34a" /> : hDegisim < -2 ? <IconTrendingDown size={14} color="#dc2626" /> : <IconMinus size={14} color="#6b7280" />}
                            <Text size="sm" fw={600} c={hDegisim > 2 ? 'green.7' : hDegisim < -2 ? 'red.7' : 'dimmed'}>%{formatPercent(hDegisim)}</Text>
                          </Group>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Group justify="center" gap={4}>
                            {zDegisim > 2 ? <IconTrendingUp size={14} color="#16a34a" /> : zDegisim < -2 ? <IconTrendingDown size={14} color="#dc2626" /> : <IconMinus size={14} color="#6b7280" />}
                            <Text size="sm" fw={600} c={zDegisim > 2 ? 'green.7' : zDegisim < -2 ? 'red.7' : 'dimmed'}>%{formatPercent(zDegisim)}</Text>
                          </Group>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Badge size="xs" color="yellow" variant="light">{s.stokcu_sayisi}</Badge>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Badge size="xs" color="red" variant="light">{s.fiyat_hassas_sayisi}</Badge>
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </div>
          )}

          {/* Enflasyon stokçusu müşteri listesi */}
          {stokcu.length > 0 && (
            <div className="section-card-table">
              <div className="section-card-table-header" style={{ background: '#fef9c3', borderBottom: '1px solid #fde68a' }}>
                <Text fw={700} size="sm" c="yellow.9">Enflasyon Stokçusu Müşteriler — En Yüksek Harcama Artışı</Text>
              </div>
              <ScrollArea h={300}>
                <Table striped highlightOnHover withTableBorder fz="sm">
                  <Table.Thead style={{ position: 'sticky', top: 0, background: '#fffbeb', zIndex: 1 }}>
                    <Table.Tr>
                      <Table.Th>Müşteri</Table.Th>
                      <Table.Th>Segment</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Harcama</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Harcama Δ 3ay</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Ziyaret Δ 3ay</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {stokcu.map((m: any, i: number) => (
                      <Table.Tr key={i} style={{ cursor: 'pointer' }}
                        onClick={() => navigate('/musteri-portali', { state: { customerId: m.id } })}>
                        <Table.Td><Text size="sm" fw={600} c="indigo.7">{m.ad}</Text></Table.Td>
                        <Table.Td><Badge size="xs" color="gray" variant="light">{m.rfm_segment || '—'}</Badge></Table.Td>
                        <Table.Td style={{ textAlign: 'right' }}>₺{Number(m.toplam_harcama || 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}</Table.Td>
                        <Table.Td style={{ textAlign: 'right', fontWeight: 600, color: Number(m.harcama_degisim_3ay) >= 0 ? '#16a34a' : '#dc2626' }}>
                          {Number(m.harcama_degisim_3ay) > 0 ? '+' : ''}%{formatPercent(Number(m.harcama_degisim_3ay || 0))}
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'right', fontWeight: 600, color: Number(m.ziyaret_degisim_3ay) >= 0 ? '#16a34a' : '#dc2626' }}>
                          {Number(m.ziyaret_degisim_3ay) > 0 ? '+' : ''}%{formatPercent(Number(m.ziyaret_degisim_3ay || 0))}
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
