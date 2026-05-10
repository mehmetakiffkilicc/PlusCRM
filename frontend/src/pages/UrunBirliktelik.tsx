import { useState, useEffect } from 'react'
import {
  Text, Group, Badge, Loader, Center, Stack,
  TextInput, Select, Table, ScrollArea, Tabs,
  RingProgress, Tooltip, Alert
} from '@mantine/core'
import { IconSearch, IconLink, IconChartBar, IconCategory, IconAlertCircle } from '@tabler/icons-react'
import ReactECharts from 'echarts-for-react'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { useChatStore } from '../stores/chatStore'
import { notifications } from '@mantine/notifications'
import '../styles/PageLayout.css'

interface Birliktelik {
  urun1_id: number
  urun1_ad: string
  urun1_marka: string
  urun2_id: number
  urun2_ad: string
  urun2_marka: string
  ortak_fis_sayisi: number
  confidence: number
  lift: number
}

interface KategoriBirliktelik {
  kat1: string
  kat2: string
  kural_sayisi: number
  ort_lift: number
  toplam_fis: number
}

interface BirliktelikData {
  birliktelikler: Birliktelik[]
  toplam: number
  kategori_birliktelik: KategoriBirliktelik[]
}

export default function UrunBirliktelik() {
  const { selectedDataSourceId, selectedCustomerType, selectedApprovalStatus, selectedRegion } = useDashboardStore()
  const [data, setData] = useState<BirliktelikData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [minLift, setMinLift] = useState('1.0')
   const [sortBy, setSortBy] = useState('fis_sayisi')

  useEffect(() => {
    if (!selectedDataSourceId) return
    setLoading(true)
    setError(null)
    apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/urun-birliktelik/`, {
      params: {
        min_lift: minLift,
        sort_by: sortBy,
        limit: 200,
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined,
        region: selectedRegion || undefined,
      }
    })
      .then(res => setData(res.data))
      .catch(err => {
        console.error('Ürün birliktelik yüklenemedi:', err)
        notifications.show({
          title: 'Hata',
          message: 'Birliktelik analizi yüklenirken bir hata oluştu.',
          color: 'red',
          icon: <IconAlertCircle size={16} />
        })
        setError('Hata oluştu.')
      })
      .finally(() => setLoading(false))
  }, [selectedDataSourceId, minLift, sortBy, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (data && data.birliktelikler.length > 0) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Ürün Birliktelik Analizi', {
        page: 'product_association',
        data_source_id: selectedDataSourceId,
        min_lift: minLift,
        sort_by: sortBy,
        total_rules: data.toplam,
        top_associations: data.birliktelikler.slice(0, 5).map(b => `${b.urun1_ad} + ${b.urun2_ad}`)
      });
    }
  }, [data, selectedDataSourceId, minLift]);

  const filtrelenmis = (data?.birliktelikler ?? []).filter(b =>
    !search ||
    b.urun1_ad.toLowerCase().includes(search.toLowerCase()) ||
    b.urun2_ad.toLowerCase().includes(search.toLowerCase()) ||
    b.urun1_marka.toLowerCase().includes(search.toLowerCase()) ||
    b.urun2_marka.toLowerCase().includes(search.toLowerCase())
  )

  const katData = data?.kategori_birliktelik ?? []
  const katlar = Array.from(new Set(katData.flatMap(k => [k.kat1, k.kat2]))).sort()

  const katMatrisOption = katData.length > 0 ? {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.data.kat1} → ${p.data.kat2}<br/>Kural: ${p.data.kural_sayisi} · Lift: ${Number(p.data.ort_lift).toFixed(2)}`
    },
    grid: { top: 20, left: 140, right: 20, bottom: 80 },
    xAxis: { type: 'category', data: katlar, axisLabel: { rotate: 35, fontSize: 10 } },
    yAxis: { type: 'category', data: katlar, axisLabel: { fontSize: 10 } },
    series: [{
      type: 'heatmap',
      data: katData.map(k => ({
        value: [katlar.indexOf(k.kat2), katlar.indexOf(k.kat1), Number(k.ort_lift).toFixed(2)],
        kat1: k.kat1, kat2: k.kat2, kural_sayisi: k.kural_sayisi, ort_lift: k.ort_lift
      })),
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } }
    }],
    visualMap: {
      min: 1, max: Math.max(...katData.map(k => Number(k.ort_lift)), 5),
      calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
      inRange: { color: ['#dbeafe', '#1d4ed8'] }
    }
  } : null

  if (!selectedDataSourceId) {
    return (
      <div className="page-content">
        <Center h={400}>
          <Stack align="center" gap="sm">
            <IconLink size={48} stroke={1.5} color="#9ca3af" />
            <Text c="dimmed">Veri kaynağı seçin</Text>
          </Stack>
        </Center>
      </div>
    )
  }

  return (
    <div className="page-content">
      {/* Filter row */}
      <div className="page-filter-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Group>
          <Select
            label="Min. Lift"
            value={minLift}
            onChange={v => setMinLift(v ?? '1.0')}
            data={[
              { value: '1.0', label: 'Lift ≥ 1.0' },
              { value: '1.5', label: 'Lift ≥ 1.5' },
              { value: '2.0', label: 'Lift ≥ 2.0' },
              { value: '3.0', label: 'Lift ≥ 3.0' },
            ]}
            size="sm" style={{ width: 130 }}
          />
           <Select
             label="Sırala"
             value={sortBy}
             onChange={v => setSortBy(v ?? 'fis_sayisi')}
             data={[
               { value: 'fis_sayisi', label: 'Ortak Fiş (Fiş Sıralı)' },
               { value: 'lift', label: 'Lift' },
               { value: 'confidence', label: 'Confidence' },
             ]}
             size="sm" style={{ width: 180 }}
           />
        </Group>
        <AISummaryButton 
          contextType="market_basket" 
          contextId={selectedDataSourceId} 
          contextData={{ min_lift: minLift, item_count: data?.toplam }}
        />
      </div>

      {data && !loading && (
        <div style={{ marginBottom: '20px' }}>
          <AIInsightCard
            contextType="market_basket"
            contextId={selectedDataSourceId.toString()}
            title="Sepet Analizi Yorumu"
            data={data}
          />
        </div>
      )}

      {loading ? (
        <Center h={300}>
          <Stack align="center" gap="sm">
            <Loader size="lg" color="indigo" />
            <Text c="dimmed">Birliktelik kuralları yükleniyor...</Text>
          </Stack>
        </Center>
      ) : error ? (
        <Alert icon={<IconAlertCircle size={16} />} title="Veri Yüklenemedi" color="red" mb="md" variant="light">
          {error}
        </Alert>
      ) : !data ? (
        <div className="page-empty-state">
          <IconLink size={56} stroke={1.5} color="#9ca3af" />
          <Text c="dimmed">Birliktelik verisi bulunamadı</Text>
        </div>
      ) : (
        <Tabs defaultValue="kurallar">
          <Tabs.List mb="md">
            <Tabs.Tab value="kurallar" leftSection={<IconLink size={16} />}>
              Ürün Kuralları
              <Badge size="xs" ml={6} color="indigo" variant="light">{(data?.toplam ?? 0).toLocaleString('tr-TR')}</Badge>
            </Tabs.Tab>
            <Tabs.Tab value="kategoriler" leftSection={<IconCategory size={16} />}>
              Kategori İlişkileri
              <Badge size="xs" ml={6} color="indigo" variant="light">{katData.length}</Badge>
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="kurallar">
            <Stack gap="md">
              {/* KPI cards */}
              <div className="kpi-summary-grid">
                <div className="kpi-gradient-card kpi-gradient-indigo">
                  <div className="kpi-card-label">Toplam Kural</div>
                  <div className="kpi-card-value">{(data?.toplam ?? 0).toLocaleString('tr-TR')}</div>
                  <div className="kpi-card-sub">Lift ≥ {minLift}</div>
                  <div className="kpi-card-icon"><IconLink size={100} stroke={1.5} /></div>
                </div>
                <div className="kpi-gradient-card kpi-gradient-green">
                  <div className="kpi-card-label">En Yüksek Lift</div>
                  <div className="kpi-card-value">
                    {filtrelenmis.length > 0 ? Number(filtrelenmis[0].lift).toFixed(2) : '—'}
                  </div>
                  <div className="kpi-card-sub">Güçlü birliktelik</div>
                  <div className="kpi-card-icon"><IconChartBar size={100} stroke={1.5} /></div>
                </div>
                <div className="kpi-gradient-card kpi-gradient-orange">
                  <div className="kpi-card-label">Görüntülenen</div>
                  <div className="kpi-card-value">{filtrelenmis.length.toLocaleString('tr-TR')}</div>
                  <div className="kpi-card-sub">Filtreli sonuç</div>
                  <div className="kpi-card-icon"><IconCategory size={100} stroke={1.5} /></div>
                </div>
              </div>

              {/* Arama */}
              <TextInput
                leftSection={<IconSearch size={16} />}
                placeholder="Ürün adı veya marka ara..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />

              {/* Tablo */}
              <div className="section-card-table">
                <ScrollArea h={500}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                    <Table.Thead style={{ position: 'sticky', top: 0, background: '#f8fafc', zIndex: 1 }}>
                      <Table.Tr>
                        <Table.Th>Ürün 1</Table.Th>
                        <Table.Th>Ürün 2</Table.Th>
                        <Table.Th style={{ textAlign: 'center' }}>Ortak Fiş</Table.Th>
                        <Table.Th style={{ textAlign: 'center' }}>Confidence</Table.Th>
                        <Table.Th style={{ textAlign: 'center' }}>Lift</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {filtrelenmis.slice(0, 100).map((b, i) => (
                        <Table.Tr key={i}>
                          <Table.Td>
                            <Text size="sm" fw={500}>{b.urun1_ad}</Text>
                            {b.urun1_marka && <Text size="xs" c="dimmed">{b.urun1_marka}</Text>}
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" fw={500}>{b.urun2_ad}</Text>
                            {b.urun2_marka && <Text size="xs" c="dimmed">{b.urun2_marka}</Text>}
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'center' }}>
                            <Badge size="sm" color="gray" variant="light">{Number(b.ortak_fis_sayisi).toLocaleString('tr-TR')}</Badge>
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'center' }}>
                            <Tooltip label={`Ürün 1 alındığında %${(Number(b.confidence) * 100).toFixed(1)} ihtimalle Ürün 2 de alınır`}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                                <RingProgress
                                  size={28} thickness={3}
                                  sections={[{ value: Number(b.confidence) * 100, color: '#4f46e5' }]}
                                />
                                <Text size="xs" fw={600} c="indigo.7">%{(Number(b.confidence) * 100).toFixed(0)}</Text>
                              </div>
                            </Tooltip>
                          </Table.Td>
                          <Table.Td style={{ textAlign: 'center' }}>
                            <Badge
                              size="sm"
                              color={Number(b.lift) >= 3 ? 'green' : Number(b.lift) >= 1.5 ? 'yellow' : 'gray'}
                              variant={Number(b.lift) >= 2 ? 'filled' : 'light'}
                            >
                              {Number(b.lift).toFixed(2)}×
                            </Badge>
                          </Table.Td>
                        </Table.Tr>
                      ))}
                      {filtrelenmis.length === 0 && (
                        <Table.Tr>
                          <Table.Td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
                            Sonuç bulunamadı
                          </Table.Td>
                        </Table.Tr>
                      )}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
                {filtrelenmis.length > 100 && (
                  <Text size="xs" c="dimmed" p="sm" ta="center">{filtrelenmis.length - 100} daha fazla sonuç — filtreyi daraltın</Text>
                )}
              </div>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="kategoriler">
            <Stack gap="md">
              {katData.length === 0 ? (
                <Center h={300}>
                  <Text c="dimmed">Kategori birliktelik verisi bulunamadı</Text>
                </Center>
              ) : (
                <>
                  {katMatrisOption && (
                    <div className="section-card">
                      <p className="section-card-title">Kategori İlişki Haritası (Lift Yoğunluğu)</p>
                      <ReactECharts option={katMatrisOption} style={{ height: 420 }} />
                    </div>
                  )}

                  <div className="section-card-table">
                    <Table striped highlightOnHover withTableBorder withColumnBorders fz="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Kategori 1</Table.Th>
                          <Table.Th>Kategori 2</Table.Th>
                          <Table.Th style={{ textAlign: 'center' }}>Kural Sayısı</Table.Th>
                          <Table.Th style={{ textAlign: 'center' }}>Ort. Lift</Table.Th>
                          <Table.Th style={{ textAlign: 'center' }}>Toplam Fiş</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {katData.map((k, i) => (
                          <Table.Tr key={i}>
                            <Table.Td><Badge color="violet" variant="light" size="sm">{k.kat1}</Badge></Table.Td>
                            <Table.Td><Badge color="indigo" variant="light" size="sm">{k.kat2}</Badge></Table.Td>
                            <Table.Td style={{ textAlign: 'center' }}>{Number(k.kural_sayisi).toLocaleString('tr-TR')}</Table.Td>
                            <Table.Td style={{ textAlign: 'center' }}>
                              <Badge size="sm" color={Number(k.ort_lift) >= 2 ? 'green' : 'yellow'} variant="light">
                                {Number(k.ort_lift).toFixed(2)}×
                              </Badge>
                            </Table.Td>
                            <Table.Td style={{ textAlign: 'center' }}>{Number(k.toplam_fis).toLocaleString('tr-TR')}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </div>
                </>
              )}
            </Stack>
          </Tabs.Panel>
        </Tabs>
      )}
    </div>
  )
}
