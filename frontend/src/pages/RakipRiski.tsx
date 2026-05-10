import { useState, useEffect } from 'react'
import { formatPercent } from '../utils/format'
import {
  Text, Group, Badge, Loader, Center, Stack,
  Table, ScrollArea, Progress, RingProgress, Button, Alert
} from '@mantine/core'
import { IconAlertTriangle, IconShield, IconUsers, IconAlertCircle } from '@tabler/icons-react'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import { useNavigate } from 'react-router-dom'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/PageLayout.css'

interface RiskMusteri {
  id: number
  ad: string
  rfm_segment: string
  toplam_harcama: number
  terk_edilen_kategori: number
  harcama_degisim_3ay: number
  ziyaret_degisim_3ay: number
  rakip_riski_skoru: number
}

interface RakipData {
  risk_listesi: RiskMusteri[]
  dagilim: {
    yuksek: number
    orta: number
    dusuk: number
    toplam: number
  }
}

function riskRenk(skor: number): string {
  if (skor >= 60) return '#dc2626'
  if (skor >= 30) return '#d97706'
  return '#6b7280'
}

function riskEtiketi(skor: number): string {
  if (skor >= 60) return 'Yüksek'
  if (skor >= 30) return 'Orta'
  return 'Düşük'
}

function riskRenkMantine(skor: number): string {
  if (skor >= 60) return 'red'
  if (skor >= 30) return 'orange'
  return 'gray'
}

const FILTER_OPTIONS = [
  { value: 'all', label: 'Tümü' },
  { value: 'yuksek', label: 'Yüksek Risk' },
  { value: 'orta', label: 'Orta Risk' },
] as const

export default function RakipRiski() {
  const { selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion } = useDashboardStore()
  const navigate = useNavigate()
  const [data, setData] = useState<RakipData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'yuksek' | 'orta'>('all')

  useEffect(() => {
    if (!selectedDataSourceId) return
    setLoading(true)
    setError(null)
    apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/rakip-riski/`, {
      params: {
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined,
        region: selectedRegion || undefined,
      }
    })
      .then(res => {
        setData(res.data)
        if (res.data) {
          useChatStore.getState().attachPageContext('Rakip Riski Analizi', {
            page: 'rakip-riski',
            data_source_id: selectedDataSourceId,
            risk_distribution: res.data.dagilim,
            high_risk_count: res.data.dagilim?.yuksek,
            total_customers: res.data.dagilim?.toplam
          });
        }
      })
      .catch(err => {
        console.error('Rakip riski yüklenemedi:', err)
        notifications.show({
          title: 'Hata',
          message: 'Rakip riski verileri yüklenirken bir hata oluştu.',
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

  const dagilim = data?.dagilim
  const liste = (data?.risk_listesi ?? []).filter(m => {
    if (filter === 'yuksek') return m.rakip_riski_skoru >= 60
    if (filter === 'orta') return m.rakip_riski_skoru >= 30 && m.rakip_riski_skoru < 60
    return true
  })
  const toplam = dagilim?.toplam ?? 0

  const filterCount = (f: typeof filter) => {
    if (f === 'all') return toplam
    if (f === 'yuksek') return dagilim?.yuksek ?? 0
    return dagilim?.orta ?? 0
  }

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Rakip Riski Analizi</h1>
        <AISummaryButton 
          contextType="rakip_riski" 
          contextId={selectedDataSourceId} 
          contextData={{ high_risk_count: data?.dagilim?.yuksek }}
        />
      </div>

      {data && !loading && (
        <div style={{ marginBottom: '24px' }}>
          <AIInsightCard
            contextType="rakip_riski"
            contextId={selectedDataSourceId.toString()}
            title="Rakip Analitik Yorumu"
          />
        </div>
      )}
      {loading ? (
        <Center h={400}>
          <Stack align="center" gap="sm">
            <Loader size="lg" color="indigo" />
            <Text c="dimmed">Risk analizi hesaplanıyor...</Text>
          </Stack>
        </Center>
      ) : error ? (
        <Alert icon={<IconAlertCircle size={16} />} title="Veri Yüklenemedi" color="red" mb="md" variant="light">
          {error}
        </Alert>
      ) : !data ? (
        <div className="page-empty-state">
          <IconAlertTriangle size={56} stroke={1.5} color="#9ca3af" />
          <Text c="dimmed">Veri bulunamadı</Text>
        </div>
      ) : (
        <>
          {/* KPI */}
          <div className="kpi-summary-grid">
            <div className="kpi-gradient-card kpi-gradient-red">
              <div className="kpi-card-label">Yüksek Risk</div>
              <div className="kpi-card-value">{(dagilim?.yuksek ?? 0).toLocaleString('tr-TR')}</div>
              <div className="kpi-card-sub">Risk skoru ≥ 60</div>
              <div className="kpi-card-icon"><IconAlertTriangle size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-orange">
              <div className="kpi-card-label">Orta Risk</div>
              <div className="kpi-card-value">{(dagilim?.orta ?? 0).toLocaleString('tr-TR')}</div>
              <div className="kpi-card-sub">Risk skoru 30–60</div>
              <div className="kpi-card-icon"><IconAlertTriangle size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-slate">
              <div className="kpi-card-label">Düşük Risk</div>
              <div className="kpi-card-value">{dagilim?.dusuk ?? 0}</div>
              <div className="kpi-card-sub">Risk skoru &lt; 30</div>
              <div className="kpi-card-icon"><IconShield size={100} stroke={1.5} /></div>
            </div>
            <div className="kpi-gradient-card kpi-gradient-indigo">
              <div className="kpi-card-label">Toplam Risk Altında</div>
              <div className="kpi-card-value">{toplam.toLocaleString('tr-TR')}</div>
              <div className="kpi-card-sub">Tüm risk seviyelerinde</div>
              <div className="kpi-card-icon"><IconUsers size={100} stroke={1.5} /></div>
            </div>
          </div>

          {/* Risk Dağılımı */}
          <div className="section-card">
            <p className="section-card-title">Risk Dağılımı</p>
            <Group gap="xl" align="center">
              <RingProgress
                size={160}
                thickness={20}
                sections={[
                  { value: toplam > 0 ? Math.round((dagilim?.yuksek ?? 0) / toplam * 100) : 0, color: '#dc2626', tooltip: `Yüksek: ${dagilim?.yuksek}` },
                  { value: toplam > 0 ? Math.round((dagilim?.orta ?? 0) / toplam * 100) : 0, color: '#d97706', tooltip: `Orta: ${dagilim?.orta}` },
                  { value: toplam > 0 ? Math.round((dagilim?.dusuk ?? 0) / toplam * 100) : 0, color: '#e5e7eb', tooltip: `Düşük: ${dagilim?.dusuk}` },
                ]}
                label={<Text size="xs" ta="center" fw={700}>Risk<br />Dağılımı</Text>}
              />
              <Stack gap="md" flex={1}>
                {[
                  { label: 'Yüksek Risk (≥60)', value: dagilim?.yuksek ?? 0, color: '#dc2626', mantineColor: 'red' },
                  { label: 'Orta Risk (30–60)', value: dagilim?.orta ?? 0, color: '#d97706', mantineColor: 'orange' },
                  { label: 'Düşük Risk (<30)', value: dagilim?.dusuk ?? 0, color: '#e5e7eb', mantineColor: 'gray' },
                ].map(item => (
                  <div key={item.label}>
                    <Group justify="space-between" mb={4}>
                      <Group gap="xs">
                        <div style={{ width: 12, height: 12, borderRadius: 3, background: item.color }} />
                        <Text size="sm">{item.label}</Text>
                      </Group>
                      <Text size="sm" fw={700}>{item.value.toLocaleString('tr-TR')}</Text>
                    </Group>
                    <Progress value={toplam > 0 ? item.value / toplam * 100 : 0} color={item.mantineColor} size="sm" />
                  </div>
                ))}
              </Stack>
            </Group>
          </div>

          {/* Filtre butonları */}
          <Group gap="xs">
            {FILTER_OPTIONS.map(opt => (
              <Button
                key={opt.value}
                size="sm"
                variant={filter === opt.value ? 'filled' : 'light'}
                color="indigo"
                onClick={() => setFilter(opt.value)}
              >
                {opt.label} ({filterCount(opt.value)})
              </Button>
            ))}
          </Group>

          {/* Müşteri listesi */}
          <div className="section-card-table">
            <ScrollArea h={450}>
              <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                <Table.Thead style={{ position: 'sticky', top: 0, background: '#f8fafc', zIndex: 1 }}>
                  <Table.Tr>
                    <Table.Th>Müşteri</Table.Th>
                    <Table.Th>Segment</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>Harcama</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Terk Edilen Kat.</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Harcama Δ</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Risk Skoru</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {liste.map((m, i) => (
                    <Table.Tr key={i} style={{ cursor: 'pointer' }}
                      onClick={() => navigate('/musteri-portali', { state: { customerId: m.id } })}>
                      <Table.Td>
                        <Text size="sm" fw={600} c="indigo.7">{m.ad}</Text>
                        <Text size="xs" c="dimmed">#{m.id}</Text>
                      </Table.Td>
                      <Table.Td><Badge size="xs" color="gray" variant="light">{m.rfm_segment || '—'}</Badge></Table.Td>
                      <Table.Td style={{ textAlign: 'right' }}>₺{Number(m.toplam_harcama || 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}</Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        {Number(m.terk_edilen_kategori) > 0 ? (
                          <Badge size="xs" color="red" variant="light">{m.terk_edilen_kategori} kat.</Badge>
                        ) : <Text size="xs" c="dimmed">—</Text>}
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center', fontWeight: 600, color: Number(m.harcama_degisim_3ay) >= 0 ? '#16a34a' : '#dc2626' }}>
                        {Number(m.harcama_degisim_3ay) > 0 ? '+' : ''}%{formatPercent(Number(m.harcama_degisim_3ay || 0))}
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Group justify="center" gap={6}>
                          <div style={{ width: 34, height: 34, borderRadius: '50%', background: riskRenk(m.rakip_riski_skoru) + '20', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Text size="xs" fw={800} style={{ color: riskRenk(m.rakip_riski_skoru) }}>{m.rakip_riski_skoru}</Text>
                          </div>
                          <Badge size="xs" color={riskRenkMantine(m.rakip_riski_skoru)} variant="light">{riskEtiketi(m.rakip_riski_skoru)}</Badge>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {liste.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>Bu filtrede sonuç yok</Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </div>
        </>
      )}
    </div>
  )
}
