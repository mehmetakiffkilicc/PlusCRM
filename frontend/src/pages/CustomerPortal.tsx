import { useState, useEffect, useMemo, useRef } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
    Container, Card, Text, Title, Group, Badge, Stack,
    TextInput, Paper, Avatar, ScrollArea,
    Button, Loader,
    UnstyledButton, Indicator,
    Menu, Tabs
} from '@mantine/core'
import {
    IconSearch, IconChevronRight, IconTrendingUp, IconAlertCircle,
    IconFilter, IconX, IconChecks,
    IconArrowsSort, IconSortAscending, IconSortDescending, IconChartPie, IconList
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useChatStore } from '../stores/chatStore'
import { useDisclosure, useIntersection } from '@mantine/hooks'
import ReactECharts from 'echarts-for-react'
import ExcelExportButton from '../components/ExcelExportButton'
import useAuthStore from '../stores/authStore'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { AINBAWidget } from '../components/ai/AINBAWidget'
import { BeklenenMusteriSection } from '../components/portal/BeklenenMusteriSection'
import { CustomerDetailPortal } from '../components/portal/CustomerDetailPortal'
import GlobalCustomerStats from '../components/portal/GlobalCustomerStats'
import { CustomerFilters } from '../components/portal/CustomerFilters'

import { Customer } from '../types/customer'
import useDashboardStore from '../stores/dashboardStore'
import apiClient from '../api/client'
import ProductPortal from '../components/ProductPortal'

const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    try {
        return new Date(dateStr).toLocaleString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    } catch (e) {
        return dateStr
    }
}

const formatOnlyDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    try {
        const d = new Date(dateStr)
        if (isNaN(d.getTime())) return dateStr
        return d.toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        })
    } catch (e) {
        return dateStr
    }
}


interface KpiItem {
    measure: string
    value: number
}

const getSegmentColor = (segment: string) => {
    if (!segment) return 'blue';
    if (segment.includes('Sampiyon') || segment.includes('Sadik')) return 'teal';
    if (segment.includes('Risk') || segment.includes('Kayip')) return 'red';
    if (segment.includes('Uyuyan') || segment.includes('Ilgi')) return 'orange';
    if (segment.includes('Potansiyel')) return 'lime';
    return 'blue';
}

export default function CustomerPortal() {
    const { user } = useAuthStore()
    const {
        selectedDataSourceId: activeDataSourceId,
        selectedYear: globalYear,
        selectedMonth: globalMonth,
        selectedStartDate: globalStartDate,
        selectedEndDate: globalEndDate,
        selectedCustomerType: globalCustomerType,
        selectedApprovalStatus: globalApprovalStatus,
        selectedRegion: globalRegion,
        setSelectedYear,
        setSelectedMonth,
        setDateRange,
        setSelectedCustomerType,
        setSelectedApprovalStatus,
        setSelectedRegion,
    } = useDashboardStore()
    const location = useLocation()
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

    // State
    const [searchInput, setSearchInput] = useState('')
    const [search, setSearch] = useState('')

    // Arama debounce - 300ms
    useEffect(() => {
        const timer = setTimeout(() => setSearch(searchInput), 300)
        return () => clearTimeout(timer)
    }, [searchInput])
    const [selectedSegment, setSelectedSegment] = useState<string[]>([])
    // Header global filtreleri — local state yerine store'dan oku
    const year = globalYear ?? ''
    const month = globalMonth ?? ''
    const startDate = globalStartDate ?? ''
    const endDate = globalEndDate ?? ''
    const region = globalRegion ?? null
    const customerType = globalCustomerType ?? null
    const approvalStatus = globalApprovalStatus ?? null
    const [showFilters, setShowFilters] = useState(false)
    const [minSpend, setMinSpend] = useState<number | ''>('')
    const [maxSpend, setMaxSpend] = useState<number | ''>('')
    const [minVisits, setMinVisits] = useState<number | ''>('')
    const [activityStatus, setActivityStatus] = useState<string | null>(null)
    const [trend, setTrend] = useState<string | null>(null)
    const [churnRisk, setChurnRisk] = useState<string | null>(null)
    const [basketSegment, setBasketSegment] = useState<string | null>(null)
    const [sortBy, setSortBy] = useState<string>('total_spend')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
    const [selectedLabels, setSelectedLabels] = useState<string[]>([])

    const [page, setPage] = useState(1)
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<{ customers: any[], total: number }>({ customers: [], total: 0 })
    const [selectedId, setSelectedId] = useState<number | null>(null)
    const [hasMore, setHasMore] = useState(true)

    // Modal Control
    const [opened, { open, close }] = useDisclosure(false)


    // Bu Hafta Bekleniyor + Geciken state moved to BeklenenMusteriSection



    // Sorted lists logic moved to components



    // Intersection observer for infinite scroll
    const lastElementRef = useIntersection({
        root: null,
        threshold: 0.1,
    })

    // URL'den gelen filtreleri yakala (Derin Linkleme)
    useEffect(() => {
        const seg = searchParams.get('segment');
        const reg = searchParams.get('region');
        const type = searchParams.get('type');
        const app = searchParams.get('approval');
        const id = searchParams.get('id');

        if (seg) setSelectedSegment([seg]);
        if (reg) setSelectedRegion(reg as any);
        if (type) setSelectedCustomerType(type as any);
        if (app) setSelectedApprovalStatus(app as any);
        
        // BUG-AI-NAV: URL'den doğrudan müşteri ID'si geldiyse modalı aç
        if (id) {
            const customerId = parseInt(id);
            if (!isNaN(customerId)) {
                setSelectedId(customerId);
                open();
            }
        }
    }, [searchParams, open]);

    useEffect(() => {
        if (lastElementRef.entry?.isIntersecting && hasMore && !loading) {
            setPage(p => p + 1)
        }
    }, [lastElementRef.entry?.isIntersecting])

    // Fetch customer list — filter değişince page sıfırla, sonra tek effect ile fetch
    const filterKey = JSON.stringify([search, selectedSegment, selectedLabels, minSpend, maxSpend, minVisits, activityStatus, trend, churnRisk, basketSegment, sortBy, sortOrder, region, customerType, approvalStatus, year, month, startDate, endDate])
    const prevFilterKey = useRef(filterKey)

    useEffect(() => {
        if (!activeDataSourceId) return
        const controller = new AbortController()

        // Filtre değiştiyse page=1'e sıfırla ve listeyi temizle
        const filterChanged = prevFilterKey.current !== filterKey
        if (filterChanged) {
            prevFilterKey.current = filterKey
            setPage(1)
            setData({ customers: [], total: 0 })
            setHasMore(true)
        }

        const currentPage = filterChanged ? 1 : page
        setLoading(true)

        const segments = selectedSegment.length > 0 ? selectedSegment.join(',') : undefined
        const etiketler = selectedLabels.length > 0 ? selectedLabels.join(',') : undefined

        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteriler/`, {
            params: {
                search: search || undefined,
                page: currentPage,
                segments,
                etiketler,
                min_spend: minSpend || undefined,
                max_spend: maxSpend || undefined,
                min_visits: minVisits || undefined,
                activity_status: activityStatus || undefined,
                trend: trend || undefined,
                churn_risk: churnRisk || undefined,
                basket_segment: basketSegment || undefined,
                customer_type: customerType || undefined,
                approval_status: approvalStatus || undefined,
                region: region || undefined,
                year: year || undefined,
                month: month || undefined,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
                sort_by: sortBy,
                sort_order: sortOrder
            },
            signal: controller.signal
        })
        .then(res => {
            if (controller.signal.aborted) return
            const newCustomers = res.data.customers || []
            const newTotal = res.data.total
            setData(prev => ({
                customers: currentPage === 1 ? newCustomers : [...prev.customers, ...newCustomers],
                total: newTotal >= 0 ? newTotal : prev.total
            }))
            setHasMore(newCustomers.length === 20)
        })
        .catch(err => {
            if (err?.code === 'ERR_CANCELED' || controller.signal.aborted) return
            console.error('Müşteri listesi çekilemedi:', err)
            notifications.show({
                title: 'Hata',
                message: 'Müşteri listesi yüklenirken bir sorun oluştu.',
                color: 'red',
                icon: <IconAlertCircle size={16} />
            })
        })
        .finally(() => {
            if (!controller.signal.aborted) setLoading(false)
        })

        return () => controller.abort()
    }, [activeDataSourceId, filterKey, page])

    // AI için sayfa bağlamını (context) zenginleştir
    useEffect(() => {
        if (data.customers.length > 0) {
            const { attachPageContext } = useChatStore.getState();
            attachPageContext('Müşteri Portalı', {
                page: 'customer_portal',
                data_source_id: activeDataSourceId,
                total_displayed: data.total,
                active_filters: {
                    search: search || undefined,
                    segments: selectedSegment,
                    labels: selectedLabels,
                    region: region || undefined,
                    activity: activityStatus || undefined,
                    churn_risk: churnRisk || undefined
                }
            });
        }
    }, [data, activeDataSourceId, search, selectedSegment, selectedLabels]);

    // Fetch logic moved to BeklenenMusteriSection



    const handleCustomerClick = (id: number) => {
        // Mevcut filtreleri ve sayfa durumunu kaydet
        const currentFilters = {
            search, selectedSegment, selectedLabels, minSpend, maxSpend,
            minVisits, activityStatus, trend, churnRisk, basketSegment,
            sortBy, sortOrder, region, customerType, approvalStatus,
            year, month, startDate, endDate, page
        };
        useDashboardStore.getState().setReturnTo(location.pathname, currentFilters);
        setSelectedId(id);
        open();
    }

    // Segmentasyon sayfasından yönlendirme: location.state.customerId ile direkt modal aç
    // activeDataSourceId da dependency'de — ikisi de hazır olduğunda çalışır
    useEffect(() => {
        const state = location.state as { customerId?: number; returnTo?: any } | null
        if (state?.customerId && activeDataSourceId) {
            setSelectedId(state.customerId)
            open()
            // State'i temizle — sayfa tekrar focus aldığında yeniden tetiklenmesin
            navigate(location.pathname, { replace: true, state: {} })
        }
    }, [location.state, activeDataSourceId])

    // Geri dönüşte filtreleri geri yükle
    useEffect(() => {
        const { returnTo, clearReturnTo } = useDashboardStore.getState();
        if (returnTo && returnTo.filters && !location.state?.customerId) {
            const f = returnTo.filters;
            setSearch(f.search || '');
            setSearchInput(f.search || '');
            setSelectedSegment(f.selectedSegment || []);
            setSelectedLabels(f.selectedLabels || []);
            setMinSpend(f.minSpend || '');
            setMaxSpend(f.maxSpend || '');
            setMinVisits(f.minVisits || '');
            setActivityStatus(f.activityStatus || null);
            setTrend(f.trend || null);
            setChurnRisk(f.churnRisk || null);
            setBasketSegment(f.basketSegment || null);
            setSortBy(f.sortBy || 'total_spend');
            setSortOrder(f.sortOrder || 'desc');
            setSelectedRegion(f.region || null);
            setSelectedCustomerType(f.customerType || undefined);
            setSelectedApprovalStatus(f.approvalStatus || undefined);
            setSelectedYear(f.year || undefined);
            setSelectedMonth(f.month || undefined);
            setDateRange(f.startDate || undefined, f.endDate || undefined);
            setPage(f.page || 1);
            clearReturnTo();
        }
    }, [])

    const handleClearAll = () => {
        setSelectedCustomerType(undefined); setSelectedApprovalStatus(undefined); setSelectedRegion(undefined);
        setSelectedMonth(undefined); setSelectedYear(undefined); setDateRange(undefined, undefined);
        setSelectedSegment([]); setSelectedLabels([]); setMinSpend(''); setMaxSpend('');
        setMinVisits(''); setActivityStatus(null); setTrend(null); setChurnRisk(null); setBasketSegment(null);
    }
 
    const activeFilterCount = useMemo(() => {
        let count = 0;
        if (selectedSegment.length > 0) count++;
        if (selectedLabels.length > 0) count++;
        if (minSpend) count++;
        if (maxSpend) count++;
        if (minVisits) count++;
        if (activityStatus) count++;
        if (trend) count++;
        if (churnRisk) count++;
        if (basketSegment) count++;
        if (region) count++;
        if (customerType) count++;
        if (approvalStatus) count++;
        if (year) count++;
        if (month) count++;
        if (startDate) count++;
        if (endDate) count++;
        return count;
    }, [selectedSegment, selectedLabels, minSpend, maxSpend, minVisits, activityStatus, trend, churnRisk, region, customerType, approvalStatus, year, month, startDate, endDate]);

    return (
        <Container size="xl" py="md">
            <Tabs defaultValue="list" variant="outline" radius="md">
                <Tabs.List mb="lg">
                    <Tabs.Tab value="list" leftSection={<IconList size={16} />}>
                        Müşteri Listesi
                    </Tabs.Tab>
                    <Tabs.Tab value="global" leftSection={<IconChartPie size={16} />}>
                        Global Analiz & Kalite
                    </Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="list">
                    <BeklenenMusteriSection 
                activeDataSourceId={activeDataSourceId}
                onCustomerClick={setSelectedId}
                formatOnlyDate={formatOnlyDate}
            />
            <Stack gap="md" mb="xl">
                <Group justify="space-between">
                </Group>

                <Group gap="sm" wrap="nowrap">
                    <TextInput 
                        placeholder="Müşteri ara (İsim, Telefon veya ID)..." 
                        leftSection={<IconSearch size={18} stroke={1.5} />}
                        style={{ flex: 1 }}
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        radius="md"
                        size="md"
                    />
                    <Group gap="xs" wrap="nowrap">
                        <Menu shadow="md" width={200} position="bottom-end">
                            <Menu.Target>
                                <Button 
                                    variant="light" 
                                    color="gray" 
                                    leftSection={<IconArrowsSort size={20} />}
                                    radius="md"
                                    size="md"
                                >
                                    Sırala
                                </Button>
                            </Menu.Target>
                            <Menu.Dropdown>
                                <Menu.Label>Sıralama Ölçütü</Menu.Label>
                                <Menu.Item 
                                    leftSection={<IconChecks size={14} opacity={sortBy === 'id' ? 1 : 0} />} 
                                    onClick={() => setSortBy('id')}
                                >
                                    Varsayılan (ID)
                                </Menu.Item>
                                <Menu.Item 
                                    leftSection={<IconChecks size={14} opacity={sortBy === 'ad' ? 1 : 0} />} 
                                    onClick={() => setSortBy('ad')}
                                >
                                    İsim (A-Z)
                                </Menu.Item>
                                <Menu.Item 
                                    leftSection={<IconChecks size={14} opacity={sortBy === 'total_spend' ? 1 : 0} />} 
                                    onClick={() => setSortBy('total_spend')}
                                >
                                    Toplam Harcama
                                </Menu.Item>
                                <Menu.Item 
                                    leftSection={<IconChecks size={14} opacity={sortBy === 'total_visits' ? 1 : 0} />} 
                                    onClick={() => setSortBy('total_visits')}
                                >
                                    Toplam Ziyaret
                                </Menu.Item>
                                <Menu.Item 
                                    leftSection={<IconChecks size={14} opacity={sortBy === 'last_shopping' ? 1 : 0} />} 
                                    onClick={() => setSortBy('last_shopping')}
                                >
                                    Son Alışveriş
                                </Menu.Item>
                                
                                <Menu.Divider />
                                <Menu.Label>Düzen</Menu.Label>
                                <Menu.Item 
                                    leftSection={<IconSortAscending size={16} />} 
                                    onClick={() => setSortOrder('asc')}
                                    bg={sortOrder === 'asc' ? '#f1f3f5' : undefined}
                                >
                                    Artan
                                </Menu.Item>
                                <Menu.Item 
                                    leftSection={<IconSortDescending size={16} />} 
                                    onClick={() => setSortOrder('desc')}
                                    bg={sortOrder === 'desc' ? '#f1f3f5' : undefined}
                                >
                                    Azalan
                                </Menu.Item>
                            </Menu.Dropdown>
                        </Menu>

                        <Indicator disabled={activeFilterCount === 0} label={activeFilterCount} size={20} color="blue" offset={2} withBorder>
                            <Button 
                                variant="light"
                                color="blue"
                                leftSection={<IconFilter size={20} />}
                                onClick={() => setShowFilters(true)}
                                radius="md"
                                size="md"
                            >
                                Filtrele
                            </Button>
                        </Indicator>
                    </Group>
                </Group>

                {/* Aktif Filtre Rozetleri (Minimal Tasarım) */}
                {activeFilterCount > 0 && (
                    <ScrollArea>
                        <Group gap="xs" wrap="nowrap">
                            {customerType && <Badge variant="flat" color="blue" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setSelectedCustomerType(undefined)} />}>Tip: {customerType}</Badge>}
                            {approvalStatus && <Badge variant="flat" color="green" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setSelectedApprovalStatus(undefined)} />}>Onay: {approvalStatus}</Badge>}
                            {region && <Badge variant="flat" color="orange" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setSelectedRegion(undefined)} />}>Bölge: {region}</Badge>}
                            {month && <Badge variant="flat" color="cyan" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setSelectedMonth(undefined)} />}>Ay: {month}</Badge>}
                            {year && <Badge variant="flat" color="indigo" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setSelectedYear(undefined)} />}>Yıl: {year}</Badge>}
                            {startDate && <Badge variant="flat" color="teal">Başlangıç: {startDate}</Badge>}
                            {endDate && <Badge variant="flat" color="teal">Bitiş: {endDate}</Badge>}
                            {selectedSegment.length > 0 && <Badge variant="flat" color="grape">Segmentler: {selectedSegment.length}</Badge>}
                            {selectedLabels.length > 0 && <Badge variant="flat" color="violet" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setSelectedLabels([])} />}>Etiketler: {selectedLabels.length}</Badge>}
                            {basketSegment && <Badge variant="flat" color="cyan" rightSection={<IconX size={10} style={{ cursor: 'pointer' }} onClick={() => setBasketSegment(null)} />}>Sepet: {basketSegment === 'kucuk' ? 'Küçük' : basketSegment === 'orta' ? 'Orta' : basketSegment === 'buyuk' ? 'Büyük' : 'Mega'}</Badge>}
                            <Button variant="subtle" size="compact-xs" color="red" onClick={handleClearAll}>Temizle</Button>
                        </Group>
                    </ScrollArea>
                )}

                {/* AI Global Insight Card */}
                {!loading && data.customers.length > 0 && activeDataSourceId && (
                    <AIInsightCard 
                        contextType="rfm_summary" 
                        contextId={activeDataSourceId?.toString()} 
                        dataSourceId={activeDataSourceId || ''}
                        title="Segment Analizi & AI Öngörüleri"
                        staticText={`${selectedSegment.length > 0 ? selectedSegment.join(', ') : 'Tüm'} segmentler için AI özeti.`}
                        data={data}
                    />
                )}

                <CustomerFilters
                    opened={showFilters}
                    onClose={() => setShowFilters(false)}
                    customerType={customerType}
                    setCustomerType={(v: any) => setSelectedCustomerType(v ?? undefined)}
                    approvalStatus={approvalStatus}
                    setApprovalStatus={(v: any) => setSelectedApprovalStatus(v ?? undefined)}
                    region={region}
                    setRegion={(v: any) => setSelectedRegion(v ?? undefined)}
                    month={month}
                    setMonth={(v: any) => setSelectedMonth(v || undefined)}
                    year={year}
                    setYear={(v: any) => setSelectedYear(v || undefined)}
                    startDate={startDate}
                    setStartDate={(v: string) => setDateRange(v || undefined, globalEndDate)}
                    endDate={endDate}
                    setEndDate={(v: string) => setDateRange(globalStartDate, v || undefined)}
                    selectedSegment={selectedSegment}
                    setSelectedSegment={setSelectedSegment}
                    selectedLabels={selectedLabels}
                    setSelectedLabels={setSelectedLabels}
                    activityStatus={activityStatus}
                    setActivityStatus={setActivityStatus}
                    trend={trend}
                    setTrend={setTrend}
                    minSpend={minSpend}
                    setMinSpend={setMinSpend}
                    minVisits={minVisits}
                    setMinVisits={setMinVisits}
                    maxSpend={maxSpend}
                    setMaxSpend={setMaxSpend}
                    churnRisk={churnRisk}
                    setChurnRisk={setChurnRisk}
                    basketSegment={basketSegment}
                    setBasketSegment={setBasketSegment}
                    onClearAll={handleClearAll}
                />
            </Stack>

            {/* Müşteri Listesi */}
            <Stack gap={4}>
                {data.customers.length === 0 && !loading && (
                    <Paper withBorder p="xl" radius="md" bg="gray.0">
                        <Stack align="center" gap="xs">
                            <IconSearch size={40} color="gray" />
                            <Text fw={500}>Müşteri Bulunamadı</Text>
                            <Text size="sm" color="dimmed">Seçili filtrelere uygun sonuç bulunamadı. Lütfen filtrelerinizi güncelleyin.</Text>
                            <Button variant="light" size="xs" onClick={handleClearAll}>Filtreleri Temizle</Button>
                        </Stack>
                    </Paper>
                )}
                {data.customers.map((customer) => (
                    <UnstyledButton
                        key={customer.id}
                        onClick={() => handleCustomerClick(customer.id)}
                        style={{ width: '100%' }}
                    >
                        <Card withBorder shadow="xs" radius="md" py={8} px="md">
                            <Group justify="space-between" wrap="nowrap">
                                <Group wrap="nowrap" flex={1} gap="sm">
                                    <Avatar color="blue" radius="xl" size="32px">{customer.ad?.charAt(0) || '?'}</Avatar>
                                    <div style={{ flex: 1, minWidth: 0, maxWidth: 400 }}>
                                        <Group gap={8} wrap="nowrap">
                                            <Text size="sm" fw={700} truncate>{customer.ad || 'İsimsiz'}</Text>
                                            <Badge variant="light" size="xs">{customer.rfm_segment}</Badge>
                                            {customer.trend === 'Yukseliyor' && <IconTrendingUp size={12} color="green" />}
                                        </Group>
                                        <Group gap={4} mt={2} wrap="wrap">
                                            <Text size="xs" color="dimmed">{customer.telefon || 'Tel Yok'} • {customer.tip || 'Müşteri'}</Text>
                                            {customer.bekleniyor && <Badge size="xs" color="orange" variant="filled">Bu Hafta Bekleniyor</Badge>}
                                            {customer.sadik_musteri && <Badge size="xs" color="teal" variant="dot">Sadık</Badge>}
                                            {customer.kaybedilmemesi_gereken && <Badge size="xs" color="violet" variant="dot">⭐ VIP Risk</Badge>}
                                            {customer.gizli_risk && <Badge size="xs" color="orange" variant="dot">Gizli Risk</Badge>}
                                            {customer.kaybedilme_riski_yuksek && <Badge size="xs" color="red" variant="dot">Risk ↑</Badge>}
                                            {customer.tamamen_kaybedilmis && <Badge size="xs" color="gray" variant="dot">Kayıp</Badge>}
                                            {customer.winback_adayi && <Badge size="xs" color="blue" variant="dot">Winback</Badge>}
                                            {customer.indirim_avcisi && <Badge size="xs" color="yellow" variant="dot">İndirim Avcısı</Badge>}
                                        </Group>
                                    </div>
                                </Group>

                                <Group gap="xl" wrap="nowrap" visibleFrom="sm" style={{ flexShrink: 0 }}>
                                    <Stack gap={0} align="center" w={100}>
                                        <Text size="10px" color="dimmed">Harcama</Text>
                                        <Text size="xs" fw={600}>₺{(customer.total_spend || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</Text>
                                    </Stack>

                                    <Stack gap={0} align="center" w={80}>
                                        <Text size="10px" color="dimmed">Ziyaret</Text>
                                        <Text size="xs" fw={600}>{customer.total_visits || 0}</Text>
                                    </Stack>

                                    <Stack gap={0} align="center" w={90}>
                                        <Text size="10px" color="dimmed">Ort. Sepet</Text>
                                        <Text size="xs" fw={600}>₺{Math.round(customer.avg_basket || 0).toLocaleString()}</Text>
                                        {(() => {
                                            const avg = customer.avg_basket || 0
                                            const seg = avg < 200 ? 'kucuk' : avg < 1000 ? 'orta' : avg < 3000 ? 'buyuk' : 'mega'
                                            const colors: Record<string, string> = { kucuk: 'gray', orta: 'blue', buyuk: 'teal', mega: 'violet' }
                                            const labels: Record<string, string> = { kucuk: 'Küçük', orta: 'Orta', buyuk: 'Büyük', mega: 'Mega' }
                                            return <Badge size="xs" variant="light" color={colors[seg]}>{labels[seg]}</Badge>
                                        })()}
                                    </Stack>

                                    <Stack gap={0} align="flex-end" w={150}>
                                        <Text size="10px" color="dimmed">Son Alışveriş</Text>
                                        <Text size="xs" color="dimmed">{customer.last_shopping_date ? formatDate(customer.last_shopping_date) : '-'}</Text>
                                    </Stack>
                                </Group>

                                <IconChevronRight size="16px" color="#ced4da" />
                            </Group>
                        </Card>
                    </UnstyledButton>
                ))}
            </Stack>

            {/* Load More Trigger */}
            <div ref={lastElementRef.ref} style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {loading && <Loader size="md" />}
                {!hasMore && data.customers.length > 0 && <Text color="dimmed" size="sm">Tüm müşteriler yüklendi.</Text>}
            </div>

            {/* Tümünü Gör Modal moved to BeklenenMusteriSection */}

                <CustomerDetailPortal 
                    opened={opened}
                    onClose={close}
                    customerId={selectedId}
                    activeDataSourceId={activeDataSourceId}
                    initialStartDate={startDate}
                    initialEndDate={endDate}
                />

            <CustomerFilters 
                opened={showFilters}
                onClose={() => setShowFilters(false)}
                customerType={customerType}
                setCustomerType={(v: any) => setSelectedCustomerType(v ?? undefined)}
                approvalStatus={approvalStatus}
                setApprovalStatus={(v: any) => setSelectedApprovalStatus(v ?? undefined)}
                region={region}
                setRegion={(v: any) => setSelectedRegion(v ?? undefined)}
                month={month}
                setMonth={(v: any) => setSelectedMonth(v || undefined)}
                year={year}
                setYear={(v: any) => setSelectedYear(v || undefined)}
                startDate={startDate}
                setStartDate={(v: string) => setDateRange(v || undefined, globalEndDate)}
                endDate={endDate}
                setEndDate={(v: string) => setDateRange(globalStartDate, v || undefined)}
                selectedSegment={selectedSegment}
                setSelectedSegment={setSelectedSegment}
                selectedLabels={selectedLabels}
                setSelectedLabels={setSelectedLabels}
                activityStatus={activityStatus}
                setActivityStatus={setActivityStatus}
                trend={trend}
                setTrend={setTrend}
                minSpend={minSpend}
                setMinSpend={setMinSpend}
                minVisits={minVisits}
                setMinVisits={setMinVisits}
                maxSpend={maxSpend}
                setMaxSpend={setMaxSpend}
                churnRisk={churnRisk}
                setChurnRisk={setChurnRisk}
                basketSegment={basketSegment}
                setBasketSegment={setBasketSegment}
                onClearAll={handleClearAll}
            />
                </Tabs.Panel>

                <Tabs.Panel value="global">
                    <Group justify="flex-end" mb="md">
                        <AISummaryButton contextType="global_stats" />
                    </Group>
                    <GlobalCustomerStats activeDataSourceId={activeDataSourceId} />
                </Tabs.Panel>
            </Tabs>
        </Container>
    )
}
