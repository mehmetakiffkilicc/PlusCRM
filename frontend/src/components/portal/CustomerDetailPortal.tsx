import { useState, useEffect, useMemo, useCallback } from 'react'
import {
    Modal, Group, Title, Badge, Stack, Skeleton, SimpleGrid, Tabs,
    ThemeIcon, Text, Center, Button, ScrollArea, Paper, Table, Grid,
    ActionIcon, Loader, UnstyledButton, Avatar, TextInput, Select,
    Timeline, Divider
} from '@mantine/core'
import {
    IconUser, IconAlertCircle, IconChartBar, IconHistory, IconClock,
    IconAffiliate, IconBulb, IconCalendar, IconChartLine, IconChartPie,
    IconCoin, IconReceipt, IconTag, IconX, IconChevronRight,
    IconPackage, IconReceiptOff, IconTimeline, IconSparkles
} from '@tabler/icons-react'
import ReactECharts from 'echarts-for-react'
import apiClient from '../../api/client'
import { AISummaryButton } from '../ai/AISummaryButton'
import { AIInsightCard } from '../ai/AIInsightCard'
import { AINBAWidget } from '../ai/AINBAWidget'
import { CustomerNarrativeSection } from '../ai/CustomerNarrativeSection'
import ProductPortal from '../ProductPortal'
import { useDisclosure } from '@mantine/hooks'

interface CustomerDetailPortalProps {
    opened: boolean;
    onClose: () => void;
    customerId: number | null;
    activeDataSourceId: string | null;
    initialStartDate?: string;
    initialEndDate?: string;
}

const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    try {
        return new Date(dateStr).toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        })
    } catch (e) {
        return dateStr
    }
}

const HighlightCard = ({ title, value, icon, color = 'blue', subtext }: { title: string, value: string, icon: React.ReactNode, color?: string, subtext?: string }) => (
    <Paper withBorder p="xs" radius="md" bg="gray.0">
        <Group gap="xs" mb={4} wrap="nowrap">
            <ThemeIcon size="sm" variant="light" color={color} radius="md">
                {icon}
            </ThemeIcon>
            <Text size="xs" fw={700} color="dimmed" truncate>{title.toUpperCase()}</Text>
        </Group>
        <Text fw={700} size="md" truncate>{value}</Text>
        {subtext && <Text size="10px" color="dimmed" truncate>{subtext}</Text>}
    </Paper>
)

export const CustomerDetailPortal = ({
    opened,
    onClose,
    customerId,
    activeDataSourceId,
    initialStartDate,
    initialEndDate
}: CustomerDetailPortalProps) => {
    // --- State Management ---
    const [detail, setDetail] = useState<any>(null)
    const [detailLoading, setDetailLoading] = useState(false)
    const [activeTab, setActiveTab] = useState<string>('overview')

    // Filtrelemede kullanılan tarihler
    const [filterStartDate, setFilterStartDate] = useState<string>(initialStartDate || '')
    const [filterEndDate, setFilterEndDate] = useState<string>(initialEndDate || '')

    // Prop'tan gelen tarih değişikliklerini izle
    useEffect(() => {
        if (initialStartDate !== undefined) setFilterStartDate(initialStartDate)
        if (initialEndDate !== undefined) setFilterEndDate(initialEndDate)
    }, [initialStartDate, initialEndDate])

    // Fis Listesi (History) State
    const [fisListesi, setFisListesi] = useState<any[]>([])
    const [fisListesiLoading, setFisListesiLoading] = useState(false)
    const [fisListesiPage, setFisListesiPage] = useState(1)
    const [fisListesiHasMore, setFisListesiHasMore] = useState(true)
    const [fisListesiTotal, setFisListesiTotal] = useState(0)
    const [historyOpened, { open: openHistory, close: closeHistory }] = useDisclosure(false)

    // Urun Analizi State
    const [urunAnalizi, setUrunAnalizi] = useState<any>(null)
    const [urunAnaliziLoading, setUrunAnaliziLoading] = useState(false)

    // Zaman Cizelgesi State
    const [zamanCizelgesi, setZamanCizelgesi] = useState<any>(null)
    const [zamanCizelgesiLoading, setZamanCizelgesiLoading] = useState(false)

    // Notlar State
    const [notlar, setNotlar] = useState<any[]>([])
    const [notlarLoading, setNotlarLoading] = useState(false)
    const [yeniNot, setYeniNot] = useState('')
    const [yeniNotOnem, setYeniNotOnem] = useState('normal')
    const [notEkleniyor, setNotEkleniyor] = useState(false)

    // Sepet Detay State
    const [selectedBasket, setSelectedBasket] = useState<any>(null)
    const [basketModalOpened, { open: openBasketModal, close: closeBasketModal }] = useDisclosure(false)
    const [basketItems, setBasketItems] = useState<any[]>([])
    const [basketItemsLoading, setBasketItemsLoading] = useState(false)

    // Marka/Kategori Detay State
    const [selectedBrand, setSelectedBrand] = useState<any>(null)
    const [brandModalOpened, { open: openBrandModal, close: closeBrandModal }] = useDisclosure(false)
    const [selectedCategory, setSelectedCategory] = useState<any>(null)
    const [categoryModalOpened, { open: openCategoryModal, close: closeCategoryModal }] = useDisclosure(false)

    // Product Portal State
    const [productPortalOpened, setProductPortalOpened] = useState(false)
    const [ppProductId, setPpProductId] = useState<number | null>(null)
    const [ppProductName, setPpProductName] = useState('')

    // --- Data Fetching ---
    const fetchDetail = useCallback(() => {
        if (!customerId || !activeDataSourceId) return
        setDetailLoading(true)
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/`, {
            params: {
                start_date: filterStartDate || undefined,
                end_date: filterEndDate || undefined
            }
        })
            .then(res => setDetail(res.data))
            .catch(() => setDetail(null))
            .finally(() => setDetailLoading(false))
    }, [customerId, activeDataSourceId, filterStartDate, filterEndDate])

    useEffect(() => {
        if (opened && customerId && activeDataSourceId) {
            // Modal ilk açıldığında global DashboardStore'dan veya son 90 günden tarihleri al
            // (Store'a erişim için bir hook veya context gerekebilir, şimdilik statik/boş bırakıp manual girişe izin veriyoruz)
            fetchDetail()
            
            // Reset sub-data when customer changes
            setFisListesi([])
            setUrunAnalizi(null)
            setZamanCizelgesi(null)
            setNotlar([])
            setActiveTab('overview')
        }
    }, [opened, customerId, activeDataSourceId]) // fetchDetail dependency listesine dahil edilmedi çünkü manual tetiklenecek

    const fetchFisListesi = useCallback((page: number) => {
        if (!activeDataSourceId || !customerId) return
        setFisListesiLoading(true)
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/`, {
            params: { mode: 'fis_listesi', page, page_size: 50 }
        }).then(res => {
            const newFisler = res.data.fis_listesi || []
            setFisListesi(prev => page === 1 ? newFisler : [...prev, ...newFisler])
            setFisListesiHasMore(res.data.has_more)
            if (res.data.total_fis >= 0) setFisListesiTotal(res.data.total_fis)
        }).catch(() => {}).finally(() => setFisListesiLoading(false))
    }, [activeDataSourceId, customerId])

    const fetchUrunAnalizi = useCallback(() => {
        if (!customerId || !activeDataSourceId) return
        setUrunAnaliziLoading(true)
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/`, {
            params: { mode: 'urun_analizi' }
        }).then(res => setUrunAnalizi(res.data))
        .catch(() => {}).finally(() => setUrunAnaliziLoading(false))
    }, [activeDataSourceId, customerId])

    const fetchZamanCizelgesi = useCallback(() => {
        if (!customerId || !activeDataSourceId) return
        setZamanCizelgesiLoading(true)
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/zaman-cizelgesi/`)
            .then(res => setZamanCizelgesi(res.data))
            .catch(() => {})
            .finally(() => setZamanCizelgesiLoading(false))
    }, [activeDataSourceId, customerId])

    const fetchNotlar = useCallback(() => {
        if (!customerId || !activeDataSourceId) return
        setNotlarLoading(true)
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/notlar/`)
            .then(res => setNotlar(res.data.notlar ?? []))
            .catch(() => {})
            .finally(() => setNotlarLoading(false))
    }, [activeDataSourceId, customerId])

    const ekleNot = useCallback(() => {
        if (!customerId || !activeDataSourceId || !yeniNot.trim()) return
        setNotEkleniyor(true)
        apiClient.post(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/notlar/`, {
            icerik: yeniNot.trim(),
            onem: yeniNotOnem,
        })
            .then(() => { setYeniNot(''); fetchNotlar() })
            .catch(() => {})
            .finally(() => setNotEkleniyor(false))
    }, [activeDataSourceId, customerId, yeniNot, yeniNotOnem, fetchNotlar])

    const silNot = useCallback((notId: number) => {
        if (!customerId || !activeDataSourceId) return
        apiClient.delete(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/notlar/${notId}/`)
            .then(() => setNotlar(prev => prev.filter(n => n.id !== notId)))
            .catch(() => {})
    }, [activeDataSourceId, customerId])

    const handleFisListesiLoadMore = () => {
        if (fisListesiLoading || !fisListesiHasMore) return
        const next = fisListesiPage + 1
        setFisListesiPage(next)
        fetchFisListesi(next)
    }

    const openProductPortal = (id: number, name: string) => {
        setPpProductId(id)
        setPpProductName(name)
        setProductPortalOpened(true)
    }

    const goToHistory = () => {
        if (fisListesi.length === 0 && !fisListesiLoading) {
            setFisListesiPage(1)
            setFisListesiHasMore(true)
            fetchFisListesi(1)
        }
        setActiveTab('history')
    }

    // --- Chart Options ---
    const categoryChartOption = useMemo(() => {
        const cats = Array.isArray(detail?.fav_categories) ? detail.fav_categories : []
        if (cats.length === 0) return {}
        return {
            tooltip: { trigger: 'item', formatter: '{b}: ₺{c} ({d}%)' },
            series: [{
                type: 'pie',
                radius: ['50%', '80%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
                label: { show: false },
                data: cats.map((c: any) => ({ name: c.name, value: c.revenue }))
            }]
        }
    }, [detail])

    const dayDistOption = useMemo(() => {
        if (!Array.isArray(detail?.day_distribution)) return {}
        const dayOrder = [
            { num: 1, name: 'Pazartesi' }, { num: 2, name: 'Salı' }, { num: 3, name: 'Çarşamba' },
            { num: 4, name: 'Perşembe' }, { num: 5, name: 'Cuma' }, { num: 6, name: 'Cumartesi' }, { num: 0, name: 'Pazar' }
        ]
        const fullDays = dayOrder.map(d => {
            const found = detail.day_distribution?.find((item: any) => item.day_num === d.num)
            return { day: d.name, count: found?.count || 0, spend: found?.total_spend || 0 }
        })
        return {
            tooltip: {
                trigger: 'axis',
                formatter: (params: any) => `<b>${params[0].name}</b><br/>Ziyaret: ${params[0].value}<br/>Harcama: ₺${params[1]?.value?.toLocaleString() || 0}`
            },
            legend: { data: ['Ziyaret', 'Harcama'], bottom: 0 },
            grid: { top: 15, bottom: 45, left: 45, right: 45 },
            xAxis: { type: 'category', data: fullDays.map(d => d.day) },
            yAxis: [
                { type: 'value', name: '', position: 'left' },
                { type: 'value', name: '', position: 'right', axisLabel: { formatter: '₺{value}' } }
            ],
            series: [
                { name: 'Ziyaret', type: 'bar', data: fullDays.map(d => d.count), itemStyle: { color: '#228be6' } },
                { name: 'Harcama', type: 'line', yAxisIndex: 1, data: fullDays.map(d => d.spend), itemStyle: { color: '#40c057' } }
            ]
        }
    }, [detail])

    const spendingTrendOption = useMemo(() => {
        const trend = Array.isArray(detail?.spending_trend) ? detail.spending_trend : []
        if (trend.length === 0) return {}
        return {
            tooltip: {
                trigger: 'axis',
                formatter: (params: any) => {
                    const date = params[0].axisValue
                    const spend = params[0].value?.toLocaleString() || '0'
                    const visits = params[1]?.value || 0
                    return `Hafta: ${date}<br/>Harcama: ₺${spend}<br/>Ziyaret: ${visits}`
                }
            },
            legend: { data: ['Harcama', 'Ziyaret'], bottom: 0 },
            grid: { top: 20, bottom: 40, left: 50, right: 50 },
            xAxis: {
                type: 'category',
                data: trend.map((d: any) => d.week_start?.slice(5) || d.week)
            },
            yAxis: [
                { type: 'value', name: 'Harcama', position: 'left', axisLabel: { formatter: '₺{value}' } },
                { type: 'value', name: 'Ziyaret', position: 'right', minInterval: 1 }
            ],
            series: [
                { name: 'Harcama', type: 'line', data: trend.map((d: any) => d.total_spend), smooth: true, itemStyle: { color: '#228be6' } },
                { name: 'Ziyaret', type: 'bar', yAxisIndex: 1, data: trend.map((d: any) => d.visit_count), itemStyle: { color: '#fab005', opacity: 0.7 } }
            ]
        }
    }, [detail])

    return (
        <>
            <Modal
                opened={opened}
                onClose={onClose}
                size="85%"
                radius="md"
                zIndex={300}
                title={
                    <Group justify="space-between" w="100%" pr="xl">
                        <Group>
                            <IconUser color="#228be6" />
                            <Title order={4}>Müşteri Analiz Portalı</Title>
                            {detail && <AISummaryButton contextType="customer_profile" contextId={detail.info.id?.toString()} />}
                        </Group>
                        <Group gap="xs">
                            <Group gap={5}>
                                <TextInput 
                                    type="date" 
                                    size="xs" 
                                    label="Başlangıç"
                                    value={filterStartDate} 
                                    onChange={(e) => setFilterStartDate(e.target.value)}
                                    styles={{ label: { fontSize: 10 } }}
                                />
                                <TextInput 
                                    type="date" 
                                    size="xs" 
                                    label="Bitiş"
                                    value={filterEndDate} 
                                    onChange={(e) => setFilterEndDate(e.target.value)}
                                    styles={{ label: { fontSize: 10 } }}
                                />
                                <Button size="xs" variant="light" mt={20} onClick={fetchDetail} loading={detailLoading}>Uygula</Button>
                            </Group>
                            <Divider orientation="vertical" />
                            {detail && (
                                <Group gap="xs">
                                    <Badge variant="dot" color={detail.kpis.activity_status === 'Cok Aktif' ? 'green' : 'blue'}>{detail.kpis.activity_status}</Badge>
                                    <Badge variant="light" color={detail.kpis.trend === 'Yukseliyor' ? 'green' : 'gray'}>Trend: {detail.kpis.trend}</Badge>
                                </Group>
                            )}
                        </Group>
                    </Group>
                }
            >
                {detailLoading ? (
                    <Stack gap="lg" p="md">
                        <Skeleton height={120} radius="md" />
                        <SimpleGrid cols={4}>{Array.from({length:4}).map((_,i)=><Skeleton key={i} height={80} radius="md"/>)}</SimpleGrid>
                        <Skeleton height={260} radius="md" />
                        <SimpleGrid cols={2}>{Array.from({length:2}).map((_,i)=><Skeleton key={i} height={200} radius="md"/>)}</SimpleGrid>
                    </Stack>
                ) : !detail ? (
                    <Center h={400}>
                        <Stack align="center" gap="md">
                            <ThemeIcon size={60} color="red" variant="light" radius="xl">
                                <IconAlertCircle size={30} />
                            </ThemeIcon>
                            <Text fw={500}>Müşteri bilgileri yüklenemedi</Text>
                            <Text size="sm" c="dimmed">Lütfen sayfayı yenileyip tekrar deneyin</Text>
                            <Button variant="light" onClick={onClose}>Kapat</Button>
                        </Stack>
                    </Center>
                ) : (
                    <Tabs value={activeTab} onChange={(val: string | null) => {
                        if (!val) return
                        setActiveTab(val)
                        if (val === 'history' && fisListesi.length === 0 && !fisListesiLoading) {
                            setFisListesiPage(1)
                            setFisListesiHasMore(true)
                            fetchFisListesi(1)
                        }
                        if ((val === 'urun_analizi' || val === 'kampanya') && !urunAnalizi && !urunAnaliziLoading) {
                            fetchUrunAnalizi()
                        }
                        if (val === 'yolculuk' && !zamanCizelgesi && !zamanCizelgesiLoading) {
                            fetchZamanCizelgesi()
                        }
                        if (val === 'notlar' && notlar.length === 0 && !notlarLoading) {
                            fetchNotlar()
                        }
                    }}>
                        <Tabs.List>
                            <Tabs.Tab value="overview" leftSection={<IconUser size={18} color="#228be6" />}>Genel Bakış</Tabs.Tab>
                            <Tabs.Tab value="analysis" leftSection={<IconChartBar size={18} color="#40c057" />}>Detaylı Analiz</Tabs.Tab>
                            <Tabs.Tab value="history" leftSection={<IconHistory size={18} color="#fab005" />}>Alışveriş Geçmişi</Tabs.Tab>
                            <Tabs.Tab value="urun_analizi" leftSection={<IconPackage size={18} color="#6366f1" />}>Ürün Tercihleri</Tabs.Tab>
                            <Tabs.Tab value="yolculuk" leftSection={<IconClock size={18} color="#748ffc" />}>Zaman Tüneli</Tabs.Tab>
                            <Tabs.Tab value="notlar" leftSection={<IconBulb size={18} color="#f06595" />}>Notlar & CRM</Tabs.Tab>
                        </Tabs.List>

                        {/* --- Overview Panel --- */}
                        <Tabs.Panel value="overview" pt="lg">
                            <Grid gutter="md">
                                {/* Müşteri Profil Kartı */}
                                <Grid.Col span={12}>
                                    <Paper withBorder p="md" radius="md" bg="var(--mantine-color-blue-light)">
                                        <Group justify="space-between" align="center">
                                            <Group gap="lg">
                                                <Avatar size={80} radius="xl" color="blue" src={null}>{detail.info.ad?.charAt(0) || '?'}</Avatar>
                                                <Stack gap={2}>
                                                    <Group gap="xs">
                                                        <Title order={3}>{detail?.info?.ad || 'İsimsiz Müşteri'}</Title>
                                                        <Badge color={detail?.info?.tip === 'Kurumsal' ? 'indigo' : 'blue'} size="lg">{detail?.info?.tip || 'Bireysel'}</Badge>
                                                    </Group>
                                                    <Text color="dimmed" size="sm">Müşteri No: {detail?.info?.id} • {detail?.info?.telefon || 'Telefon Bilgisi Yok'}</Text>
                                                    <Group gap="xs" mt={4}>
                                                        <Badge color="blue" variant="filled" size="lg">{detail?.info?.rfm_segment}</Badge>
                                                        {(detail?.tags || []).slice(0, 3).map((tag: string) => (
                                                            <Badge key={tag} color="gray" variant="outline" size="sm">{tag}</Badge>
                                                        ))}
                                                    </Group>
                                                </Stack>
                                            </Group>
                                            <AINBAWidget customerId={detail.info.id.toString()} customerData={detail} dataSourceId={activeDataSourceId || ''} />
                                        </Group>
                                    </Paper>
                                </Grid.Col>

                                {/* Ciro Kartları - Dönemsel */}
                                <Grid.Col span={12}>
                                    <Text size="sm" fw={700} color="dimmed" mb="xs">DÖNEMSEL CİRO</Text>
                                    <SimpleGrid cols={{ base: 2, md: 4 }} spacing="sm">
                                        <HighlightCard 
                                            title="Aylık Ciro" 
                                            value={`₺${Math.round(detail.kpis.spend_30d || 0).toLocaleString()}`} 
                                            icon={<IconCoin size={14} />} 
                                            color="blue"
                                            subtext="Son 30 Gün"
                                        />
                                        <HighlightCard 
                                            title="3 Aylık Ciro" 
                                            value={`₺${Math.round(detail.kpis.spend_90d || 0).toLocaleString()}`} 
                                            icon={<IconCoin size={14} />} 
                                            color="teal"
                                            subtext="Son 90 Gün"
                                        />
                                        <HighlightCard 
                                            title="Yıllık Ciro" 
                                            value={`₺${Math.round(detail.kpis.spend_365d || 0).toLocaleString()}`} 
                                            icon={<IconCoin size={14} />} 
                                            color="green"
                                            subtext="Son 365 Gün"
                                        />
                                        <HighlightCard 
                                            title="Toplam Ciro" 
                                            value={`₺${Math.round(detail.kpis.total_spend || 0).toLocaleString()}`} 
                                            icon={<IconCoin size={14} />} 
                                            color="violet"
                                            subtext="Tüm Dönemler"
                                        />
                                    </SimpleGrid>
                                </Grid.Col>

                                {/* Alışveriş Metrikleri */}
                                <Grid.Col span={12}>
                                    <Text size="sm" fw={700} color="dimmed" mb="xs">ALIŞVERİŞ METRİKLERİ</Text>
                                    <SimpleGrid cols={{ base: 2, md: 4 }} spacing="sm">
                                        <HighlightCard 
                                            title="Alışveriş Sayısı" 
                                            value={`${detail.kpis.total_visits || 0}`} 
                                            icon={<IconReceipt size={14} />} 
                                            color="orange"
                                            subtext="Toplam Ziyaret"
                                        />
                                        <HighlightCard 
                                            title="Ort. Sepet" 
                                            value={`₺${Math.round(detail.kpis.avg_basket || 0).toLocaleString()}`} 
                                            icon={<IconReceipt size={14} />} 
                                            color="yellow"
                                            subtext="Ortalama Harcama"
                                        />
                                        <HighlightCard 
                                            title="Son Alışveriş" 
                                            value={formatDate(detail.kpis.last_shopping_date)} 
                                            icon={<IconCalendar size={14} />} 
                                            color="blue"
                                            subtext="Son Mağaza Ziyareti"
                                        />
                                        <HighlightCard 
                                            title="Alışveriş Sıklığı" 
                                            value={detail.kpis.avg_visit_interval > 0 ? `${Math.round(detail.kpis.avg_visit_interval)} gün` : 'Yeni Müşteri'} 
                                            icon={<IconTimeline size={14} />} 
                                            color="violet"
                                            subtext="Ort. Ziyaret Aralığı"
                                        />
                                    </SimpleGrid>
                                </Grid.Col>

                                {/* Tercihler & Davranış */}
                                <Grid.Col span={{ base: 12, md: 6 }}>
                                    <Paper withBorder p="md" radius="md">
                                        <Text size="sm" fw={700} color="dimmed" mb="md">TERCİH EDİLEN KATEGORİLER</Text>
                                        {Array.isArray(detail?.fav_categories) && detail.fav_categories.length > 0 ? (
                                            <Stack gap="xs">
                                                {detail.fav_categories.slice(0, 5).map((cat: any, idx: number) => (
                                                    <Group key={cat.id || idx} justify="space-between">
                                                        <Group gap="xs">
                                                            <ThemeIcon size="sm" variant="light" color="blue" radius="md">
                                                                <IconTag size={12} />
                                                            </ThemeIcon>
                                                            <Text size="sm" fw={600}>{cat.name}</Text>
                                                        </Group>
                                                        <Group gap="xs">
                                                            <Text size="xs" color="dimmed">₺{Math.round(cat.revenue || 0).toLocaleString()}</Text>
                                                            <Badge variant="light" size="xs" color="blue">{idx === 0 ? 'En Çok' : ''}</Badge>
                                                        </Group>
                                                    </Group>
                                                ))}
                                            </Stack>
                                        ) : (
                                            <Center h={80}><Text size="sm" c="dimmed">Kategori verisi bulunamadı</Text></Center>
                                        )}
                                    </Paper>
                                </Grid.Col>

                                <Grid.Col span={{ base: 12, md: 6 }}>
                                    <Paper withBorder p="md" radius="md">
                                        <Text size="sm" fw={700} color="dimmed" mb="md">MAĞAZA TERCİHLERİ</Text>
                                        <Paper withBorder p="xs" radius="md" bg="gray.0" mb="xs">
                                            <Group gap="xs">
                                                <IconAffiliate size={16} color="var(--mantine-color-indigo-6)" />
                                                <Text size="xs" fw={700}>EN SADIK MAĞAZA:</Text>
                                                <Text size="sm" fw={600}>{detail.kpis.fav_store || 'Çoklu Mağaza'}</Text>
                                            </Group>
                                        </Paper>
                                        {detail.kpis.preferred_day && detail.kpis.preferred_day !== '-' && (
                                            <Paper withBorder p="xs" radius="md" bg="gray.0">
                                                <Group gap="xs">
                                                    <IconCalendar size={16} color="var(--mantine-color-teal-6)" />
                                                    <Text size="xs" fw={700}>TERCİH EDİLEN GÜN:</Text>
                                                    <Text size="sm" fw={600}>{detail.kpis.preferred_day}</Text>
                                                </Group>
                                            </Paper>
                                        )}
                                    </Paper>
                                </Grid.Col>

                                {/* Kampanya Duyarlılığı & Aksiyonlar */}
                                <Grid.Col span={12}>
                                    <Paper withBorder p="md" radius="md">
                                        <Group justify="space-between" mb="xs">
                                            <Text size="sm" fw={700} color="dimmed">KAMPANYA DUYARLILIĞI & MÜŞTERİ TİPİ</Text>
                                        </Group>
                                        <SimpleGrid cols={{ base: 2, md: 4 }} spacing="sm">
                                            <Paper withBorder p="sm" radius="md" bg="gray.0">
                                                <Group gap="xs" mb={4}>
                                                    <IconSparkles size={14} color="var(--mantine-color-pink-6)" />
                                                    <Text size="xs" fw={700}>DUYARLILIK</Text>
                                                </Group>
                                                <Text size="md" fw={700} color={detail.labels?.kanal?.kampanya_duyarli ? 'pink' : 'gray'}>
                                                    {detail.labels?.kanal?.kampanya_duyarli ? 'Yüksek' : (detail.fiyat_ozeti?.hassasiyet_seviye === 'Yüksek' ? 'Fiyat Hassas' : 'Standart')}
                                                </Text>
                                                <Text size="xs" color="dimmed">Pazarlama Tepkisi</Text>
                                            </Paper>
                                            <Paper withBorder p="sm" radius="md" bg="gray.0">
                                                <Group gap="xs" mb={4}>
                                                    <IconUser size={14} color="var(--mantine-color-blue-6)" />
                                                    <Text size="xs" fw={700}>MÜŞTERİ TİPİ</Text>
                                                </Group>
                                                <Text size="md" fw={700}>{detail?.info?.tip || 'Bireysel'}</Text>
                                                <Text size="xs" color="dimmed">Müşteri Sınıfı</Text>
                                            </Paper>
                                            <Paper withBorder p="sm" radius="md" bg="gray.0">
                                                <Group gap="xs" mb={4}>
                                                    <IconChartLine size={14} color="var(--mantine-color-green-6)" />
                                                    <Text size="xs" fw={700}>TREND</Text>
                                                </Group>
                                                <Text size="md" fw={700} color={detail.kpis.trend === 'Yukseliyor' ? 'green' : detail.kpis.trend === 'Dusuyor' ? 'red' : 'gray'}>
                                                    {detail.kpis.trend || 'Stabil'}
                                                </Text>
                                                <Text size="xs" color="dimmed">Alışveriş Yönü</Text>
                                            </Paper>
                                            <Paper withBorder p="sm" radius="md" bg="gray.0">
                                                <Group gap="xs" mb={4}>
                                                    <IconBulb size={14} color="var(--mantine-color-yellow-6)" />
                                                    <Text size="xs" fw={700}>AKSİYON</Text>
                                                </Group>
                                                <Text size="sm" fw={600}>
                                                    {detail.labels?.kanal?.kampanya_duyarli ? 'Kampanya gönder' : 
                                                     detail.kpis.trend === 'Dusuyor' ? 'İletişime geç' :
                                                     detail.kpis.trend === 'Yukseliyor' ? 'Sadakat programı' :
                                                     'Standart takip'}
                                                </Text>
                                                <Text size="xs" color="dimmed">Önerilen Aksiyon</Text>
                                            </Paper>
                                        </SimpleGrid>
                                    </Paper>
                                </Grid.Col>

                                {/* CLV & Trend */}
                                <Grid.Col span={{ base: 12, md: 3 }}>
                                    <Paper withBorder p="md" radius="md" h="100%">
                                        <Text size="xs" fw={700} color="dimmed" mb="md">YAŞAM BOYU DEĞER (CLV)</Text>
                                        <Stack gap="xl">
                                            <div>
                                                <Text size="28px" fw={800} color="blue">₺{Math.round(detail.kpis.total_spend || 0).toLocaleString()}</Text>
                                                <Text size="xs" color="dimmed">Toplam Harcama</Text>
                                            </div>
                                            <SimpleGrid cols={2}>
                                                <div>
                                                    <Text fw={700}>{detail.kpis.total_visits || 0}</Text>
                                                    <Text size="10px" color="dimmed">Ziyaret</Text>
                                                </div>
                                                <div>
                                                    <Text fw={700}>₺{Math.round(detail.kpis.avg_basket || 0).toLocaleString()}</Text>
                                                    <Text size="10px" color="dimmed">Ort. Sepet</Text>
                                                </div>
                                            </SimpleGrid>
                                        </Stack>
                                    </Paper>
                                </Grid.Col>

                                <Grid.Col span={{ base: 12, md: 9 }}>
                                    <Paper withBorder p="md" radius="md" h="100%">
                                        <Group justify="space-between" mb="xs">
                                            <Text size="xs" fw={700} color="dimmed">HARCAMA VE ZİYARET TRENDİ</Text>
                                            <Button variant="subtle" size="compact-xs" rightSection={<IconChevronRight size={14} />} onClick={goToHistory}>Arşive Git</Button>
                                        </Group>
                                        {Array.isArray(detail.spending_trend) && detail.spending_trend.length > 0 ? (
                                            <ReactECharts
                                                option={spendingTrendOption}
                                                style={{ height: 200 }}
                                                onEvents={{ 'click': (params: any) => {
                                                    const trendItem = detail.spending_trend[params.dataIndex]
                                                    if (trendItem) { fetchFisListesi(1); openHistory(); }
                                                }}}
                                            />
                                        ) : (
                                            <Center h={200}>
                                                <Stack align="center" gap="xs">
                                                    <Text size="sm" c="dimmed">Son 90 günde harcama verisi bulunamadı</Text>
                                                    <Text size="xs" c="dimmed">Alışveriş geçmişi için ilgili sekmeyi inceleyin</Text>
                                                </Stack>
                                            </Center>
                                        )}
                                    </Paper>
                                </Grid.Col>

                                {/* AI & Gün Davranış */}
                                <Grid.Col span={{ base: 12, md: 6 }}>
                                    <AIInsightCard
                                        key={`ai-profil-${detail.info.id}`}
                                        contextType="customer"
                                        contextId={detail.info.id.toString()}
                                        dataSourceId={activeDataSourceId || ''}
                                        title="AI Profil Özeti"
                                    />
                                </Grid.Col>

                                <Grid.Col span={{ base: 12, md: 6 }}>
                                    <Paper withBorder p="md" radius="md">
                                        <Text size="xs" fw={700} color="dimmed" mb="md">GÜN BAZLI DAVRANIŞ</Text>
                                        <ReactECharts option={dayDistOption} style={{ height: 200 }} />
                                    </Paper>
                                </Grid.Col>
                            </Grid>
                        </Tabs.Panel>

                        {/* --- Analysis Panel --- */}
                        <Tabs.Panel value="analysis" pt="lg">
                           <Grid gutter="md">
                                <Grid.Col span={{ base: 12, md: 4 }}>
                                    <Paper withBorder p="md" radius="md">
                                        <Text size="xs" fw={700} color="dimmed" mb="md">KATEGORİ DAĞILIMI</Text>
                                        {Array.isArray(detail?.fav_categories) && detail.fav_categories.length > 0 ? (
                                            <ReactECharts
                                                option={categoryChartOption}
                                                style={{ height: 300 }}
                                                onEvents={{ 'click': (params: any) => {
                                                    const cat = detail.fav_categories?.find((c: any) => c.name === params.name)
                                                    if (cat) { setSelectedCategory(cat); openCategoryModal(); }
                                                }}}
                                            />
                                        ) : (
                                            <Center h={300}>
                                                <Stack align="center" gap="xs">
                                                    <IconChartPie size={36} color="#9ca3af" stroke={1.5} />
                                                    <Text size="sm" c="dimmed">Kategori verisi bulunamadı</Text>
                                                </Stack>
                                            </Center>
                                        )}
                                    </Paper>
                                </Grid.Col>
                                <Grid.Col span={{ base: 12, md: 8 }}>
                                    <Paper withBorder p="md" radius="md" h="100%">
                                        <Text size="xs" fw={700} color="dimmed" mb="md">EN ÇOK TERCİH EDİLEN MARKALAR</Text>
                                        {(detail?.fav_brands || []).length > 0 ? (
                                            <Table striped withTableBorder>
                                                <Table.Thead>
                                                    <Table.Tr>
                                                        <Table.Th>Marka</Table.Th>
                                                        <Table.Th ta="right">Harcama</Table.Th>
                                                        <Table.Th ta="right">Miktar</Table.Th>
                                                        <Table.Th ta="right"></Table.Th>
                                                    </Table.Tr>
                                                </Table.Thead>
                                                <Table.Tbody>
                                                    {(detail.fav_brands).slice(0, 10).map((b: any) => (
                                                        <Table.Tr key={b?.name || Math.random()}>
                                                            <Table.Td fw={600}>{b?.name || 'Bilinmiyor'}</Table.Td>
                                                            <Table.Td ta="right">₺{Math.round(b?.revenue || 0).toLocaleString()}</Table.Td>
                                                            <Table.Td ta="right">{Math.round(b?.qty || 0).toLocaleString()} Adet</Table.Td>
                                                            <Table.Td ta="right">
                                                                <ActionIcon variant="subtle" color="blue" onClick={() => { setSelectedBrand(b); openBrandModal(); }}>
                                                                     <IconChartBar size={16} />
                                                                </ActionIcon>
                                                            </Table.Td>
                                                        </Table.Tr>
                                                    ))}
                                                </Table.Tbody>
                                            </Table>
                                        ) : (
                                            <Center h={200}>
                                                <Stack align="center" gap="xs">
                                                    <IconTag size={36} color="#9ca3af" stroke={1.5} />
                                                    <Text size="sm" c="dimmed">Henüz marka verisi bulunmamaktadır</Text>
                                                </Stack>
                                            </Center>
                                        )}
                                    </Paper>
                                </Grid.Col>
                           </Grid>
                        </Tabs.Panel>

                        {/* --- History Panel --- */}
                        <Tabs.Panel value="history" pt="lg">
                            <Stack gap="md">
                                {fisListesiLoading && fisListesi.length === 0 && <Center my="md"><Loader size="md" /></Center>}
                                {!fisListesiLoading && fisListesi.length === 0 ? (
                                    <Center h={300}>
                                        <Stack align="center" gap="xs">
                                            <IconReceiptOff size={48} color="#9ca3af" stroke={1.5} />
                                            <Text size="sm" c="dimmed">Bu müşteriye ait alışveriş kaydı bulunamadı</Text>
                                        </Stack>
                                    </Center>
                                ) : (
                                    <>
                                        <Table striped withTableBorder stickyHeader>
                                            <Table.Thead>
                                                <Table.Tr>
                                                    <Table.Th>Tarih</Table.Th>
                                                    <Table.Th>Fiş No</Table.Th>
                                                    <Table.Th>Mağaza</Table.Th>
                                                    <Table.Th ta="right">Miktar</Table.Th>
                                                    <Table.Th ta="right">Toplam</Table.Th>
                                                    <Table.Th></Table.Th>
                                                </Table.Tr>
                                            </Table.Thead>
                                            <Table.Tbody>
                                                {fisListesi.map((fis) => (
                                                    <Table.Tr key={fis.fis_no}>
                                                        <Table.Td>{fis.tarih}</Table.Td>
                                                        <Table.Td fw={600}>{fis.fis_no}</Table.Td>
                                                        <Table.Td>{fis.magaza_ad}</Table.Td>
                                                        <Table.Td ta="right">{fis.kalem_sayisi}</Table.Td>
                                                        <Table.Td ta="right" fw={700}>₺{fis.toplam_tutar.toLocaleString()}</Table.Td>
                                                        <Table.Td>
                                                            <Button variant="light" size="compact-xs" onClick={() => {
                                                                setSelectedBasket(fis);
                                                                setBasketItems([]);
                                                                setBasketItemsLoading(true);
                                                                apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/${customerId}/`, {
                                                                    params: { fis_no: fis.fis_no }
                                                                }).then(res => setBasketItems(res.data.history || []))
                                                                .finally(() => setBasketItemsLoading(false));
                                                                openBasketModal();
                                                            }}>Detay</Button>
                                                        </Table.Td>
                                                    </Table.Tr>
                                                ))}
                                            </Table.Tbody>
                                        </Table>
                                        {fisListesiHasMore && (
                                            <Button variant="subtle" fullWidth onClick={handleFisListesiLoadMore} loading={fisListesiLoading}>Daha Fazla...</Button>
                                        )}
                                    </>
                                )}
                            </Stack>
                        </Tabs.Panel>

                        {/* --- Product Analysis Panel --- */}
                        <Tabs.Panel value="urun_analizi" pt="lg">
                            {urunAnaliziLoading ? <Center><Loader /></Center> : urunAnalizi && (
                                <Grid gutter="md">
                                    {/* Hane etiketi vurgu kartları — bebek/çocuk skoru yüksekse öne çıkar */}
                                    {urunAnalizi.hane_vurgular?.map((vurgu: any) => (
                                        <Grid.Col key={vurgu.etiket} span={12}>
                                            <Paper withBorder p="md" radius="md" style={{ borderColor: vurgu.etiket === 'bebek' ? '#f97316' : '#6366f1', borderWidth: 2 }}>
                                                <Group mb="sm" justify="space-between">
                                                    <Group gap="xs">
                                                        <Text size="sm" fw={700}>{vurgu.label}</Text>
                                                        <Badge color={vurgu.etiket === 'bebek' ? 'orange' : 'indigo'} variant="light">
                                                            Hane Skoru: %{Math.round(vurgu.skor * 100)}
                                                        </Badge>
                                                    </Group>
                                                    <Text size="xs" c="dimmed">Bu kategorideki tekrar alımlar</Text>
                                                </Group>
                                                <Stack gap="xs">
                                                    {vurgu.urunler.map((p: any, i: number) => (
                                                        <Group key={i} justify="space-between">
                                                            <UnstyledButton onClick={() => openProductPortal(p.urun_id, p.urun_ad)}>
                                                                <Text size="sm" color="blue" fw={600}>{p.urun_ad}</Text>
                                                            </UnstyledButton>
                                                            <Group gap="xs">
                                                                <Badge variant="light" color="gray">{p.fis_count} Fiş</Badge>
                                                                <Badge variant="light">{Math.round(p.total_qty || 0)} Adet</Badge>
                                                            </Group>
                                                        </Group>
                                                    ))}
                                                </Stack>
                                            </Paper>
                                        </Grid.Col>
                                    ))}
                                    <Grid.Col span={{ base: 12, md: 6 }}>
                                        <Paper withBorder p="md" radius="md">
                                            <Text size="sm" fw={700} color="dimmed" mb="md">EN ÇOK ALINAN ÜRÜNLER</Text>
                                            <Stack gap="xs">
                                                {(urunAnalizi.top_products || urunAnalizi.tekrar_alim)?.map((p: any, i: number) => (
                                                    <Group key={i} justify="space-between">
                                                        <UnstyledButton onClick={() => openProductPortal(p.id || p.urun_id, p.name || p.urun_ad)}>
                                                            <Text size="sm" color="blue" fw={600}>{p.name || p.urun_ad}</Text>
                                                        </UnstyledButton>
                                                        <Badge variant="light">{Math.round(p.total_qty || 0)} Adet</Badge>
                                                    </Group>
                                                ))}
                                            </Stack>
                                        </Paper>
                                    </Grid.Col>
                                    <Grid.Col span={{ base: 12, md: 6 }}>
                                        <AIInsightCard key={`ai-urun-${customerId}`} title="Ürün Bazlı Öneriler" contextType="customer_product" contextId={customerId?.toString() || ''} dataSourceId={activeDataSourceId || ''} />
                                    </Grid.Col>
                                </Grid>
                            )}
                        </Tabs.Panel>

                        {/* --- Timeline Panel --- */}
                        <Tabs.Panel value="yolculuk" pt="lg">
                            {zamanCizelgesiLoading ? (
                                <Center h={300}><Loader /></Center>
                            ) : (() => {
                                const items = Array.isArray(zamanCizelgesi)
                                    ? zamanCizelgesi
                                    : zamanCizelgesi?.aylik_ozet ?? []
                                if (!zamanCizelgesi || items.length === 0) return (
                                    <Center h={300}>
                                        <Stack align="center" gap="xs">
                                            <IconTimeline size={48} color="#9ca3af" stroke={1.5} />
                                            <Text size="sm" c="dimmed">Bu müşteriye ait zaman tüneli verisi bulunmamaktadır</Text>
                                        </Stack>
                                    </Center>
                                )
                                return (
                                    <ScrollArea h={500}>
                                        <Timeline active={0} bulletSize={30} lineWidth={2}>
                                            {items.map((item: any, idx: number) => (
                                                <Timeline.Item
                                                    key={idx}
                                                    bullet={<IconReceipt size={16} />}
                                                    title={item.ay || item.magaza_ad || 'Dönem Bilgisi Yok'}
                                                >
                                                    <Text size="sm">{item.ay} — {item.ziyaret_sayisi ?? 0} ziyaret — ₺{(item.toplam_tutar || 0).toLocaleString('tr-TR')}</Text>
                                                    <Text size="xs" mt={4} c="dimmed">{item.rfm_segment || ''}</Text>
                                                </Timeline.Item>
                                            ))}
                                        </Timeline>
                                    </ScrollArea>
                                )
                            })()}
                        </Tabs.Panel>

                        {/* --- Notes Panel --- */}
                        <Tabs.Panel value="notlar" pt="lg">
                            <Stack gap="md">
                                <Paper withBorder p="md" bg="gray.0">
                                    <Stack gap="sm">
                                        <TextInput 
                                            placeholder="Notunuzu yazın..." 
                                            value={yeniNot} 
                                            onChange={(e) => setYeniNot(e.target.value)} 
                                        />
                                        <Group justify="space-between">
                                            <Select 
                                                data={['normal', 'yuksek', 'kritik']} 
                                                value={yeniNotOnem} 
                                                onChange={(v) => setYeniNotOnem(v || 'normal')} 
                                                size="xs"
                                            />
                                            <Button size="xs" onClick={ekleNot} loading={notEkleniyor}>Ekle</Button>
                                        </Group>
                                    </Stack>
                                </Paper>
                                {notlar.map((n) => (
                                    <Paper key={n.id} withBorder p="sm" radius="md">
                                        <Group justify="space-between">
                                            <Badge color={n.onem === 'kritik' ? 'red' : 'blue'}>{n.onem}</Badge>
                                            <ActionIcon color="red" variant="subtle" onClick={() => silNot(n.id)}><IconX size={14}/></ActionIcon>
                                        </Group>
                                        <Text size="sm" mt="xs">{n.icerik}</Text>
                                        <Text size="10px" c="dimmed" mt={4}>{new Date(n.olusturma_tarihi).toLocaleString()}</Text>
                                    </Paper>
                                ))}
                            </Stack>
                        </Tabs.Panel>
                    </Tabs>
                )}
            </Modal>

            {/* --- Sub-Modals --- */}
            <Modal opened={historyOpened} onClose={closeHistory} size="xl" title="Alışveriş Geçmişi">
                 <Text>Geçmiş detayları...</Text>
            </Modal>

            <Modal opened={basketModalOpened} onClose={closeBasketModal} size="lg" title="Sepet Detayı" closeOnClickOutside={false} closeOnEscape={false}>
                {selectedBasket && (
                    <Stack gap="md">
                        <Paper p="sm" withBorder bg="gray.0">
                            <Grid>
                                <Grid.Col span={6}><Text size="xs" c="dimmed">Fiş No</Text><Text fw={600}>{selectedBasket.fis_no}</Text></Grid.Col>
                                <Grid.Col span={6}><Text size="xs" c="dimmed">Toplam</Text><Text fw={700} color="blue">₺{selectedBasket.toplam_tutar?.toLocaleString()}</Text></Grid.Col>
                            </Grid>
                        </Paper>
                        {basketItemsLoading ? <Center><Loader /></Center> : (
                            <Table striped>
                                <Table.Thead><Table.Tr><Table.Th>Ürün</Table.Th><Table.Th ta="right">Adet</Table.Th><Table.Th ta="right">Tutar</Table.Th></Table.Tr></Table.Thead>
                                <Table.Tbody>
                                    {basketItems.map((item, idx) => (
                                        <Table.Tr key={idx}>
                                            <Table.Td><UnstyledButton onClick={() => openProductPortal(item.urun_id, item.urun_ad)}><Text color="blue" size="sm">{item.urun_ad}</Text></UnstyledButton></Table.Td>
                                            <Table.Td ta="right">{item.miktar}</Table.Td>
                                            <Table.Td ta="right">₺{item.tutar.toLocaleString()}</Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </Table>
                        )}
                    </Stack>
                )}
            </Modal>

            <Modal opened={brandModalOpened} onClose={closeBrandModal} title="Marka Analizi" closeOnClickOutside={false} closeOnEscape={false}>
                {selectedBrand && (
                    <Stack>
                        <Title order={3}>{selectedBrand.name}</Title>
                        <Text fw={700} size="xl">₺{selectedBrand.revenue.toLocaleString()}</Text>
                        <Text size="xs" fw={700} c="dimmed">TOP ÜRÜNLER</Text>
                        {selectedBrand.top_products?.map((p: any, i: number) => (
                            <Paper key={i} withBorder p="xs">
                                <Group justify="space-between">
                                    <UnstyledButton onClick={() => openProductPortal(p.id, p.name)}><Text size="xs" color="blue">{p.name}</Text></UnstyledButton>
                                    <Text size="xs" fw={700}>₺{p.total_revenue.toLocaleString()}</Text>
                                </Group>
                            </Paper>
                        ))}
                    </Stack>
                )}
            </Modal>

            <Modal opened={categoryModalOpened} onClose={closeCategoryModal} title="Kategori Analizi" closeOnClickOutside={false} closeOnEscape={false}>
                {selectedCategory && (
                    <Stack>
                        <Title order={3}>{selectedCategory.name}</Title>
                        <Text fw={700} size="xl" color="teal">₺{selectedCategory.revenue.toLocaleString()}</Text>
                        {selectedCategory.top_products?.map((p: any, i: number) => (
                            <Paper key={i} withBorder p="xs">
                                <Group justify="space-between">
                                    <UnstyledButton onClick={() => openProductPortal(p.id, p.name)}><Text size="xs" color="blue">{p.name}</Text></UnstyledButton>
                                    <Text size="xs" fw={700}>₺{p.total_revenue.toLocaleString()}</Text>
                                </Group>
                            </Paper>
                        ))}
                    </Stack>
                )}
            </Modal>

            <ProductPortal 
                isOpen={productPortalOpened} 
                onClose={() => setProductPortalOpened(false)} 
                productId={ppProductId || 0} 
                productName={ppProductName} 
            />
        </>
    )
}
