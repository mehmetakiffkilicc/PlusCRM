import { useState, useEffect } from 'react'
import { axisFormatter } from '../utils/format'
import {
  Text, Group, Badge, Loader, Center, Stack,
  SimpleGrid, Progress, ScrollArea, Table, Tabs, Alert
} from '@mantine/core'
import { IconDiamond, IconUsers, IconChartBar, IconAlertCircle } from '@tabler/icons-react'
import ReactECharts from 'echarts-for-react'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/PageLayout.css'

interface MarkaProfil {
  marka: string
  marka_id: number
  musteri_sayisi: number
  toplam_harcama: number
  ort_harcama: number
  sampiyonlar: number
  sadik: number
  risk: number
}

interface SadakatSkor {
  marka: string
  toplam_musteri: number
  sadece_bu_marka: number
}

interface SadakatData {
  marka_profiller: MarkaProfil[]
  sadakat_skorlari: SadakatSkor[]
  top_markalar: any[]
}

const MARKA_RENKLER = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', '#f97316', '#ef4444', '#06b6d4', '#84cc16']

export default function MarkaSadakati() {
  const {
    selectedDataSourceId,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedRegion,
  } = useDashboardStore()
  const [data, setData] = useState<SadakatData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedDataSourceId) return
    setLoading(true)
    setError(null)
    apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/marka-sadakati/`, {
      params: {
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined,
        region: selectedRegion || undefined,
      }
    })
      .then(res => setData(res.data))
      .catch(err => {
        console.error('Marka sadakati yüklenemedi:', err)
        notifications.show({
          title: 'Hata',
          message: 'Marka sadakati verileri yüklenirken bir hata oluştu.',
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
        setError('Veri yükleme hatası.')
      })
      .finally(() => setLoading(false))
  }, [selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (data && data.marka_profiller.length > 0) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Marka Sadakati', {
        page: 'marka_sadakati',
        data_source_id: selectedDataSourceId,
        brand_count: data.marka_profiller.length,
        top_brand: data.marka_profiller[0]?.marka,
        total_customers: data.marka_profiller.reduce((acc, curr) => acc + curr.musteri_sayisi, 0)
      });
    }
  }, [data, selectedDataSourceId]);

  if (!selectedDataSourceId) {
    return (
      <div className="page-content">
        <Center h={400}>
          <Stack align="center" gap="sm">
            <IconDiamond size={48} stroke={1.5} color="#9ca3af" />
            <Text c="dimmed">Veri kaynağı seçin</Text>
          </Stack>
        </Center>
      </div>
    )
  }

  const profiller = data?.marka_profiller ?? []
  const sadakatlar = data?.sadakat_skorlari ?? []

  const segmentPieOption = profiller[0] ? {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, fontSize: 11 },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { value: profiller[0].sampiyonlar, name: 'Şampiyonlar', itemStyle: { color: '#16a34a' } },
        { value: profiller[0].sadik, name: 'Sadık', itemStyle: { color: '#4f46e5' } },
        { value: profiller[0].risk, name: 'Risk', itemStyle: { color: '#dc2626' } },
        {
          value: profiller[0].musteri_sayisi - profiller[0].sampiyonlar - profiller[0].sadik - profiller[0].risk,
          name: 'Diğer', itemStyle: { color: '#9ca3af' }
        },
      ].filter(d => d.value > 0),
      label: { fontSize: 11 }
    }]
  } : null

  const sadakatBarOption = sadakatlar.length > 0 ? {
    tooltip: { trigger: 'axis', formatter: (p: any[]) => `${p[0].axisValue}<br/>Sadakat Skoru: %${p[0].value}` },
    grid: { top: 10, left: 10, right: 20, bottom: 0, containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: (v: number) => `%${v}` }, max: 100 },
    yAxis: { type: 'category', data: sadakatlar.map(s => s.marka).reverse(), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: sadakatlar.map(s =>
        s.toplam_musteri > 0 ? Math.round(s.sadece_bu_marka / s.toplam_musteri * 100) : 0
      ).reverse(),
      itemStyle: { color: '#6366f1', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', formatter: (p: any) => `%${p.value}`, fontSize: 11 },
    }]
  } : null

  const harcamaBarOption = profiller.length > 0 ? {
    tooltip: { trigger: 'axis', formatter: (p: any[]) => `${p[0].axisValue}: ₺${Number(p[0].value).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}` },
    grid: { top: 10, left: 10, right: 60, bottom: 0, containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: axisFormatter } },
    yAxis: { type: 'category', data: profiller.slice(0, 10).map(m => m.marka).reverse(), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: profiller.slice(0, 10).map(m => m.toplam_harcama).reverse(),
      itemStyle: {
        color: (p: any) => MARKA_RENKLER[profiller.slice(0, 10).length - 1 - p.dataIndex] ?? '#6366f1',
        borderRadius: [0, 4, 4, 0]
      },
      label: {
        show: true, position: 'right',
        formatter: (p: any) => axisFormatter(p.value) + '₺',
        fontSize: 10
      },
    }]
  } : null

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: '#1f2937' }}>Marka Sadakati ve Penetrasyon</h1>
        <AISummaryButton 
          contextType="marka_sadakati" 
          contextId={selectedDataSourceId} 
          contextData={{ brand_count: profiller.length }}
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
            contextType="marka_sadakati" 
            contextId={selectedDataSourceId.toString()} 
            title="Marka Sadakati AI Yorumu"
            data={data}
          />
        </div>
      )}

      {loading ? (
        <Center h={400}>
          <Stack align="center" gap="sm">
            <Loader size="lg" color="indigo" />
            <Text c="dimmed">Marka analizi yükleniyor...</Text>
          </Stack>
        </Center>
      ) : !data || profiller.length === 0 ? (
        <div className="page-empty-state">
          <IconDiamond size={56} stroke={1.5} color="#9ca3af" />
          <Text c="dimmed" size="lg">Marka verisi bulunamadı</Text>
          <Text size="xs" c="dimmed">musterimarka_dagilimi tablosu gerekli</Text>
        </div>
      ) : (
        <Tabs defaultValue="profil">
          <Tabs.List mb="md">
            <Tabs.Tab value="profil" leftSection={<IconChartBar size={16} />}>Marka Profilleri</Tabs.Tab>
            <Tabs.Tab value="sadakat" leftSection={<IconDiamond size={16} />}>Sadakat Skoru</Tabs.Tab>
            <Tabs.Tab value="segmentler" leftSection={<IconUsers size={16} />}>Segment Dağılımı</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="profil">
            <Stack gap="md">
              {/* KPI */}
              <div className="kpi-summary-grid">
                <div className="kpi-gradient-card kpi-gradient-indigo">
                  <div className="kpi-card-label">Analiz Edilen Marka</div>
                  <div className="kpi-card-value">{profiller.length}</div>
                  <div className="kpi-card-icon"><IconDiamond size={100} stroke={1.5} /></div>
                </div>
                <div className="kpi-gradient-card kpi-gradient-green">
                  <div className="kpi-card-label">En Büyük Marka</div>
                  <div className="kpi-card-value" style={{ fontSize: '1.4rem' }}>{profiller[0]?.marka ?? '—'}</div>
                  <div className="kpi-card-sub">{profiller[0]?.musteri_sayisi?.toLocaleString('tr-TR')} müşteri</div>
                  <div className="kpi-card-icon"><IconUsers size={100} stroke={1.5} /></div>
                </div>
                <div className="kpi-gradient-card kpi-gradient-amber">
                  <div className="kpi-card-label">En Yüksek Ort. Harcama</div>
                  {(() => {
                    const best = [...profiller].sort((a, b) => b.ort_harcama - a.ort_harcama)[0]
                    return (
                      <>
                        <div className="kpi-card-value" style={{ fontSize: '1.4rem' }}>{best?.marka ?? '—'}</div>
                        <div className="kpi-card-sub">₺{Number(best?.ort_harcama ?? 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}/müşteri</div>
                      </>
                    )
                  })()}
                  <div className="kpi-card-icon"><IconChartBar size={100} stroke={1.5} /></div>
                </div>
              </div>

              {/* Harcama bar */}
              <div className="section-card">
                <p className="section-card-title">Top 10 Marka — Toplam Müşteri Harcaması</p>
                {harcamaBarOption && <ReactECharts option={harcamaBarOption} style={{ height: 300 }} />}
              </div>

              {/* Tablo */}
              <div className="section-card-table">
                <ScrollArea h={400}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                    <Table.Thead style={{ position: 'sticky', top: 0, background: '#f8fafc', zIndex: 1 }}>
                      <Table.Tr>
                        <Table.Th>Marka</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Müşteri</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Toplam Harcama</Table.Th>
                        <Table.Th style={{ textAlign: 'right' }}>Ort. Harcama</Table.Th>
                        <Table.Th style={{ textAlign: 'center' }}>Şampiyonlar</Table.Th>
                        <Table.Th style={{ textAlign: 'center' }}>Sadık</Table.Th>
                        <Table.Th style={{ textAlign: 'center' }}>Risk</Table.Th>
                        <Table.Th>Sağlık</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {profiller.map((m, i) => {
                        const saglikli = m.sampiyonlar + m.sadik
                        const saglikOran = m.musteri_sayisi > 0 ? Math.round(saglikli / m.musteri_sayisi * 100) : 0
                        return (
                          <Table.Tr key={m.marka || i}>
                            <Table.Td>
                              <Group gap="xs">
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: MARKA_RENKLER[i % MARKA_RENKLER.length] }} />
                                <Text size="sm" fw={600}>{m.marka}</Text>
                              </Group>
                            </Table.Td>
                            <Table.Td style={{ textAlign: 'right' }}>{m.musteri_sayisi.toLocaleString('tr-TR')}</Table.Td>
                            <Table.Td style={{ textAlign: 'right', fontWeight: 600 }}>₺{Number(m.toplam_harcama).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}</Table.Td>
                            <Table.Td style={{ textAlign: 'right' }}>₺{Number(m.ort_harcama).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}</Table.Td>
                            <Table.Td style={{ textAlign: 'center' }}><Badge size="xs" color="green" variant="light">{m.sampiyonlar}</Badge></Table.Td>
                            <Table.Td style={{ textAlign: 'center' }}><Badge size="xs" color="indigo" variant="light">{m.sadik}</Badge></Table.Td>
                            <Table.Td style={{ textAlign: 'center' }}><Badge size="xs" color="red" variant="light">{m.risk}</Badge></Table.Td>
                            <Table.Td style={{ minWidth: 100 }}>
                              <Group gap="xs">
                                <Progress value={saglikOran} color={saglikOran > 50 ? 'green' : saglikOran > 25 ? 'yellow' : 'red'} style={{ flex: 1 }} size="sm" />
                                <Text size="xs" c="dimmed">%{saglikOran}</Text>
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        )
                      })}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
              </div>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="sadakat">
            <Stack gap="md">
              <div className="section-card">
                <p className="section-card-title">Marka Sadakat Skoru</p>
                <Text size="xs" c="dimmed" mb="md">Sadece bu markadan alışveriş yapan müşterilerin toplam müşteriye oranı. Yüksek = tek markaya bağlılık.</Text>
                {sadakatBarOption ? (
                  <ReactECharts option={sadakatBarOption} style={{ height: 400 }} />
                ) : (
                  <Center h={200}><Text c="dimmed">Sadakat verisi bulunamadı</Text></Center>
                )}
              </div>

              <div className="section-card-table">
                <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Marka</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Toplam Müşteri</Table.Th>
                      <Table.Th style={{ textAlign: 'right' }}>Sadece Bu Marka</Table.Th>
                      <Table.Th>Sadakat Skoru</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {sadakatlar.map((s, i) => {
                      const skor = s.toplam_musteri > 0 ? Math.round(s.sadece_bu_marka / s.toplam_musteri * 100) : 0
                      return (
                        <Table.Tr key={i}>
                          <Table.Td><Text size="sm" fw={600}>{s.marka}</Text></Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>{s.toplam_musteri.toLocaleString('tr-TR')}</Table.Td>
                          <Table.Td style={{ textAlign: 'right' }}>{s.sadece_bu_marka.toLocaleString('tr-TR')}</Table.Td>
                          <Table.Td>
                            <Group gap="xs">
                              <Progress value={skor} color={skor > 50 ? 'indigo' : skor > 25 ? 'yellow' : 'gray'} style={{ flex: 1 }} size="sm" />
                              <Badge size="xs" color={skor > 50 ? 'indigo' : skor > 25 ? 'yellow' : 'gray'} variant="light">%{skor}</Badge>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      )
                    })}
                  </Table.Tbody>
                </Table>
              </div>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="segmentler">
            <SimpleGrid cols={2}>
              {profiller.slice(0, 6).map((m, i) => {
                const total = m.musteri_sayisi || 1
                const renk = MARKA_RENKLER[i % MARKA_RENKLER.length]
                const diger = total - m.sampiyonlar - m.sadik - m.risk
                return (
                  <div key={m.marka || i} className="section-card">
                    <Group justify="space-between" mb="sm">
                      <Text fw={700} size="sm" style={{ color: renk }}>{m.marka}</Text>
                      <Badge size="xs" color="gray" variant="light">{total.toLocaleString('tr-TR')} müşteri</Badge>
                    </Group>
                    <Stack gap={6}>
                      {[
                        { label: 'Şampiyonlar', value: m.sampiyonlar, color: '#16a34a' },
                        { label: 'Sadık & Potansiyel', value: m.sadik, color: '#4f46e5' },
                        { label: 'Risk Altında', value: m.risk, color: '#dc2626' },
                        { label: 'Diğer', value: diger > 0 ? diger : 0, color: '#9ca3af' },
                      ].map(seg => (
                        <div key={seg.label}>
                          <Group justify="space-between" mb={2}>
                            <Text size="xs" c="dimmed">{seg.label}</Text>
                            <Text size="xs" fw={600} style={{ color: seg.color }}>
                              {seg.value.toLocaleString('tr-TR')} (%{Math.round(seg.value / total * 100)})
                            </Text>
                          </Group>
                          <Progress value={Math.round(seg.value / total * 100)} color={seg.color.startsWith('#') ? undefined : seg.color} style={{ '--progress-color': seg.color } as any} size="sm" />
                        </div>
                      ))}
                    </Stack>
                  </div>
                )
              })}
            </SimpleGrid>
          </Tabs.Panel>
        </Tabs>
      )}
    </div>
  )
}
