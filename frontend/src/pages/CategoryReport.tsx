import React, { useState, useEffect, useMemo } from 'react'
import { formatPercent, axisFormatter } from '../utils/format'
import { useNavigate } from 'react-router-dom'
import {
    Grid,
    Card,
    Text,
    Group,
    Badge,
    ScrollArea,
    ActionIcon,
    TextInput,
    Button,
    Stack,
    Paper,
    Collapse,
    MultiSelect,
    SegmentedControl,
    Tooltip,
    SimpleGrid,
    Box,
    Pagination,
    Alert
} from '@mantine/core'
import {
    IconCategory,
    IconChartBar,
    IconUsers,
    IconPlus,
    IconTrash,
    IconChevronDown,
    IconChevronRight,
    IconAffiliate,
    IconSearch,
    IconCoin,
    IconReceipt,
    IconPackage,
    IconAlertCircle,
} from '@tabler/icons-react'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import useUIStore from '../stores/uiStore'
import LoadingOverlay from '../components/LoadingOverlay'
import ReactECharts from 'echarts-for-react'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { notifications } from '@mantine/notifications'
import styles from '../styles/CategoryReport.module.css'
import ExcelExportButton from '../components/ExcelExportButton'

interface CategoryDetails {
    info: any
    kpis: any
    trends: any[]
    topProducts: any[]
    rfmDistribution: any[]
    associations: any[]
    comparison: {
        marketShare: number
        parentName: string | null
        levelLabel: string
        benchmarks: {
            parentRevenue?: number
            parentAvgPrice?: number
        }
        siblings: { name: string; revenue: number }[]
    }
    brandTrends: { name: string; data: { month: string; share: number }[] }[]
    brandCustomerAnalysis: { name: string; count: number; share: number }[]
}

/* ── Shared ECharts theme tokens ── */
const CHART_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

const TOOLTIP_STYLE = {
    backgroundColor: '#1e293b',
    borderColor: '#334155',
    borderWidth: 1,
    textStyle: { color: '#f1f5f9', fontSize: 12, fontFamily: CHART_FONT },
    confine: true,
}

const AXIS_LABEL = { color: '#94a3b8', fontSize: 11, fontFamily: CHART_FONT }
const SPLIT_LINE  = { lineStyle: { type: 'dashed' as const, color: '#f1f5f9' } }
const AXIS_LINE   = { show: true,  lineStyle: { color: '#e2e8f0' } }
const NO_TICK     = { show: false }

export default function CategoryReport() {
    const navigate = useNavigate()
    const { selectedDataSourceId } = useDashboardStore()

    const [loading, setLoading]                           = useState(false)
    const [error, setError]                               = useState<string | null>(null)
    const [categoryTree, setCategoryTree]                 = useState<any[]>([])
    const [selectedCategory, setSelectedCategory]         = useState<{ name: string; level: string } | null>(null)
    const [details, setDetails]                           = useState<CategoryDetails | null>(null)
    const [newTag, setNewTag]                             = useState('')
    const [expanded, setExpanded]                         = useState<Record<string, boolean>>({})
    const [searchTerm, setSearchTerm]                     = useState('')
    const [selectedBrands, setSelectedBrands]             = useState<string[]>([])
    const [recommendationStrategy, setRecommendationStrategy] = useState<string>('volume')

    // Kategori terk analizi state'leri
    const [terkKategoriler, setTerkKategoriler] = useState<{ana_kategori: string; musteri_sayisi: number}[]>([])
    const [terkAcik, setTerkAcik] = useState<Record<string, boolean>>({})
    const [terkMusteri, setTerkMusteri] = useState<Record<string, any[]>>({})
    const [terkToplam, setTerkToplam] = useState<Record<string, number>>({})
    const [terkSayfa, setTerkSayfa] = useState<Record<string, number>>({})
    const [terkYukleniyor, setTerkYukleniyor] = useState<Record<string, boolean>>({})

    /* ── filtered tree ── */
    const filteredTree = useMemo(() => {
        if (!searchTerm) return categoryTree
        const term = searchTerm.toLowerCase()
        const filterNodes = (nodes: any[]): any[] =>
            nodes
                .map(node => {
                    if (!node?.name) return null
                    const nodeMatches = node.name.toLowerCase().includes(term)
                    const children = node.children ? filterNodes(node.children) : []
                    if (nodeMatches || children.length > 0) return { ...node, children }
                    return null
                })
                .filter(Boolean)
        return filterNodes(categoryTree)
    }, [categoryTree, searchTerm])

    useEffect(() => {
        if (selectedDataSourceId) loadCategoryTree()
    }, [selectedDataSourceId])

    useEffect(() => {
        if (!selectedDataSourceId) return
        apiClient.get(`/veri-kaynaklari/${selectedDataSourceId}/kategori-terk-by-kategori/`)
            .then((r: any) => setTerkKategoriler(r.data.kategoriler || []))
            .catch(() => {})
    }, [selectedDataSourceId])

    const loadTerkMusteriler = async (kategori: string, sayfa: number) => {
        setTerkYukleniyor(p => ({ ...p, [kategori]: true }))
        try {
            const r: any = await apiClient.get(
                `/veri-kaynaklari/${selectedDataSourceId}/kategori-terk-by-kategori/`,
                { params: { ana_kategori: kategori, page: sayfa, limit: 20 } }
            )
            setTerkMusteri(p => ({ ...p, [kategori]: r.data.musteriler || [] }))
            setTerkToplam(p => ({ ...p, [kategori]: r.data.toplam || 0 }))
            setTerkSayfa(p => ({ ...p, [kategori]: sayfa }))
        } catch (e) {
            // sessizce geç
        } finally {
            setTerkYukleniyor(p => ({ ...p, [kategori]: false }))
        }
    }

    const toggleTerk = async (kat: string) => {
        const yeniAcik = !terkAcik[kat]
        setTerkAcik(p => ({ ...p, [kat]: yeniAcik }))
        if (yeniAcik && !terkMusteri[kat]) await loadTerkMusteriler(kat, 1)
    }

    const loadCategoryTree = async () => {
        if (!selectedDataSourceId) return
        try {
            const tree = await apiClient.getCategoryTree(selectedDataSourceId)
            setCategoryTree(Array.isArray(tree) ? tree : (tree.categories || []))
        } catch (error: any) {
            if (!error.message?.includes('Network Error')) console.error('Error loading category tree:', error)
        }
    }

    const loadCategoryDetails = async (name: string, level: string, strategy: string = recommendationStrategy) => {
        if (!selectedDataSourceId) { setLoading(false); return }
        setLoading(true)
        setError(null)
        try {
            const data = await apiClient.getCategoryDetails(selectedDataSourceId, name, level, strategy)
            setDetails(data)
            setSelectedCategory({ name, level })
            if (data.brandTrends) setSelectedBrands(data.brandTrends.map((bt: any) => bt.name))
        } catch (error: any) {
            if (!error.message?.includes('Network Error')) {
                console.error('Error loading category details:', error)
                notifications.show({
                  title: 'Hata',
                  message: 'Kategori detayları yüklenirken bir hata oluştu.',
                  color: 'red',
                  icon: <IconAlertCircle size={16} />
                })
                setError('Kategori detayları yüklenirken bir hata oluştu.')
            }
        } finally {
            setLoading(false)
        }
    }

    const toggleExpand = (id: string, e: React.MouseEvent) => {
        e.stopPropagation()
        setExpanded(prev => ({ ...prev, [id]: !prev[id] }))
    }

    const handleAddTag = async () => {
        if (!selectedDataSourceId || !selectedCategory || !newTag) return
        try {
        } catch (error) {
            console.error('Error adding tag:', error)
        }
    }

    const handleRemoveTag = async (_tag: string) => {
        if (!selectedDataSourceId || !selectedCategory) return
        try {
            // Placeholder
        } catch (error) {
            console.error('Error removing tag:', error)
        }
    }

    /* ── Tree Node Component ── */
    const CategoryTreeNode = ({
        node,
        depth = 0,
        path = '',
    }: {
        node: any
        depth?: number
        path?: string
    }) => {
        const currentPath = path ? `${path} > ${node.name}` : node.name
        const isExpanded  = searchTerm ? true : expanded[currentPath]
        const isSelected  = selectedCategory?.name === node.name && selectedCategory?.level === node.level
        const hasChildren = node.children && node.children.length > 0

        return (
            <Box mb={2}>
                <div
                    className={`${styles.treeNode} ${isSelected ? styles.treeNodeSelected : ''}`}
                    style={{ marginLeft: depth * 14 }}
                    onClick={() => node.name && node.level && loadCategoryDetails(node.name, node.level)}
                >
                    <div className={styles.treeNodeInner}>
                        <div className={styles.treeNodeLeft}>
                            {hasChildren ? (
                                <ActionIcon
                                    size="xs"
                                    variant="subtle"
                                    color="gray"
                                    onClick={(e) => toggleExpand(currentPath, e)}
                                >
                                    {isExpanded
                                        ? <IconChevronDown size={12} />
                                        : <IconChevronRight size={12} />}
                                </ActionIcon>
                            ) : (
                                <Box w={20} />
                            )}
                            <span className={`${styles.treeNodeName} ${isSelected ? styles.treeNodeNameSelected : ''}`}>
                                {node.name}
                            </span>
                        </div>
                        <span className={styles.treeNodeRevenue}>
                            ₺{Math.round(node.revenue).toLocaleString()}
                        </span>
                    </div>
                </div>

                {hasChildren && (
                    <Collapse in={isExpanded}>
                        {node.children.map((child: any, idx: number) => (
                            <CategoryTreeNode key={idx} node={child} depth={depth + 1} path={currentPath} />
                        ))}
                    </Collapse>
                )}
            </Box>
        )
    }

    /* ── Derived values ── */
    const levelLabel =
        details?.info.level === 'ana'  ? 'Ana Kategori' :
        details?.info.level === 'alt1' ? 'Alt Kategori 1' :
        'Alt Kategori 2'

    const months = details?.trends.map(t => t.month).reverse() || []

    /* ── Chart Configs ── */
    const trendOption = {
        tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
        xAxis: {
            type: 'category',
            data: months,
            boundaryGap: false,
            axisLine: AXIS_LINE,
            axisTick: NO_TICK,
            axisLabel: AXIS_LABEL,
            splitLine: { show: false },
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                ...AXIS_LABEL,
                formatter: axisFormatter,
            },
            axisLine: { show: false },
            axisTick: NO_TICK,
            ...SPLIT_LINE,
        },
        series: [{
            name: 'Ciro',
            data: details?.trends.map(t => t.revenue).reverse() || [],
            type: 'line',
            smooth: true,
            lineStyle: { color: '#3b82f6', width: 3 },
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#3b82f6', borderColor: '#fff', borderWidth: 2 },
            areaStyle: {
                color: {
                    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(59,130,246,0.22)' },
                        { offset: 1, color: 'rgba(59,130,246,0.02)' },
                    ],
                },
            },
        }],
    }

    const rfmOption = {
        tooltip: { trigger: 'item', ...TOOLTIP_STYLE, formatter: '{b}: <b>{c}</b> ({d}%)' },
        color: ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#06b6d4','#ec4899','#14b8a6','#a855f7','#f97316','#6b7280'],
        series: [{
            name: 'CRM Segmentasyonu',
            type: 'pie',
            radius: ['42%', '72%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
            label: { show: false },
            emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', fontFamily: CHART_FONT } },
            data: (details?.rfmDistribution?.length ?? 0) > 0
                ? (details?.rfmDistribution ?? []).map(r => ({ value: r.count, name: r.segment }))
                : [{ value: 0, name: 'Veri Yok', itemStyle: { color: '#e2e8f0' } }],
        }],
    }

    const comparisonOption = {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...TOOLTIP_STYLE },
        grid: { left: '3%', right: '8%', bottom: '3%', top: '5%', containLabel: true },
        xAxis: {
            type: 'value',
            axisLabel: { show: false },
            splitLine: { show: false },
            axisLine: { show: false },
            axisTick: NO_TICK,
        },
        yAxis: {
            type: 'category',
            data: details?.comparison.siblings.map(s => s.name).reverse() || [],
            axisLabel: { fontSize: 10, width: 110, overflow: 'break' as const, color: '#64748b', fontFamily: CHART_FONT },
            axisLine: { show: false },
            axisTick: NO_TICK,
            splitLine: { show: false },
        },
        series: [{
            name: 'Ciro',
            type: 'bar',
            barMaxWidth: 24,
            data: (details?.comparison.siblings.map(s => {
                const isSelf = s.name === details!.info.ana
                return {
                    value: Math.round(s.revenue),
                    itemStyle: {
                        color: isSelf
                            ? { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#3b82f6' }, { offset: 1, color: '#4f46e5' }] }
                            : '#f1f5f9',
                        borderRadius: [0, 4, 4, 0],
                    },
                }
            }) || []).reverse(),
            label: {
                show: true,
                position: 'right',
                formatter: (p: any) => `₺${(p.value / 1000).toFixed(0)}k`,
                fontSize: 10,
                color: '#64748b',
                fontFamily: CHART_FONT,
            },
        }],
    }

    const brandShareOption = {
        tooltip: { trigger: 'axis', ...TOOLTIP_STYLE },
        legend: {
            type: 'scroll',
            bottom: 5,
            icon: 'circle',
            textStyle: { fontSize: 10, color: '#64748b', fontFamily: CHART_FONT },
            pageIconColor: '#4f46e5',
            pageTextStyle: { color: '#64748b', fontSize: 10 },
        },
        grid: { left: '3%', right: '4%', bottom: '18%', top: '5%', containLabel: true },
        xAxis: {
            type: 'category',
            data: months,
            axisLine: AXIS_LINE,
            axisTick: NO_TICK,
            axisLabel: AXIS_LABEL,
            splitLine: { show: false },
        },
        yAxis: {
            type: 'value',
            axisLabel: { ...AXIS_LABEL, formatter: '{value}%' },
            axisLine: { show: false },
            axisTick: NO_TICK,
            ...SPLIT_LINE,
        },
        series: details?.brandTrends
            .filter(bt => selectedBrands.includes(bt.name))
            .map(bt => ({
                name: bt.name,
                type: 'line',
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 2 },
                data: months.map(m => {
                    const found = bt.data.find(d => d.month === m)
                    return found ? found.share : 0
                }),
            })) || [],
    }

    const filteredBrandCustomers = details?.brandCustomerAnalysis.filter(b => selectedBrands.includes(b.name)) || []
    const dataZoomEnd = filteredBrandCustomers.length > 15
        ? (15 / filteredBrandCustomers.length) * 100
        : 100

    const brandCustomerOption = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            ...TOOLTIP_STYLE,
            formatter: (params: any) => {
                const bCount = params[0]
                const bShare = params[1]
                if (!bShare) return `<b>${bCount.name}</b><br/>${bCount.seriesName}: <b>${bCount.value.toLocaleString()}</b>`
                return `<b>${bCount.name}</b><br/><span style="color:${bCount.color}">●</span> ${bCount.seriesName}: <b>${bCount.value.toLocaleString()}</b><br/><span style="color:${bShare.color}">●</span> ${bShare.seriesName}: <b>%${bShare.value}</b>`
            },
        },
        legend: { top: 0, icon: 'circle', textStyle: { fontSize: 10, color: '#64748b', fontFamily: CHART_FONT } },
        grid: { left: '3%', right: '4%', bottom: '18%', top: '12%', containLabel: true },
        dataZoom: [
            { type: 'inside', start: 0, end: dataZoomEnd },
            { type: 'slider', height: 18, bottom: 5, start: 0, end: dataZoomEnd, borderColor: '#e2e8f0', fillerColor: 'rgba(59,130,246,0.1)', handleStyle: { color: '#3b82f6' } },
        ],
        xAxis: {
            type: 'category',
            data: filteredBrandCustomers.map(b => b.name),
            axisLabel: {
                interval: 0,
                rotate: 35,
                fontSize: 9,
                color: '#94a3b8',
                fontFamily: CHART_FONT,
                formatter: (value: string) => value.length > 12 ? value.substring(0, 10) + '..' : value,
            },
            axisLine: AXIS_LINE,
            axisTick: NO_TICK,
            splitLine: { show: false },
        },
        yAxis: [
            {
                type: 'value',
                name: 'Müşteri',
                nameTextStyle: { color: '#94a3b8', fontSize: 10, fontFamily: CHART_FONT },
                axisLabel: AXIS_LABEL,
                axisLine: { show: false },
                axisTick: NO_TICK,
                ...SPLIT_LINE,
            },
            {
                type: 'value',
                name: 'Pay',
                nameTextStyle: { color: '#94a3b8', fontSize: 10, fontFamily: CHART_FONT },
                position: 'right',
                axisLabel: { ...AXIS_LABEL, formatter: '{value}%' },
                axisLine: { show: false },
                axisTick: NO_TICK,
                splitLine: { show: false },
            },
        ],
        series: [
            {
                name: 'Müşteri Sayısı',
                type: 'bar',
                data: filteredBrandCustomers.map(b => b.count),
                itemStyle: {
                    color: {
                        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: '#60a5fa' },
                            { offset: 1, color: '#3b82f6' },
                        ],
                    },
                    borderRadius: [4, 4, 0, 0],
                },
                barMaxWidth: 36,
                label: { show: true, position: 'top', fontSize: 9, fontWeight: 600, color: '#3b82f6', fontFamily: CHART_FONT },
            },
            {
                name: 'Müşteri Payı (%)',
                type: 'line',
                yAxisIndex: 1,
                data: filteredBrandCustomers.map(b => b.share),
                lineStyle: { color: '#f59e0b', width: 3 },
                itemStyle: { color: '#f59e0b', borderColor: '#fff', borderWidth: 2 },
                symbol: 'circle',
                symbolSize: 7,
            },
        ],
    }

    /* ════════════════════════════════════════
       RENDER
    ════════════════════════════════════════ */
    return (
        <div className={styles.pageWrapper}>
            <Grid gutter="md">

                {/* ───────────────────────────
                    Left Panel: Category Tree
                ─────────────────────────── */}
                <Grid.Col span={{ base: 12, md: 4 }}>
                    <Card withBorder shadow="sm" radius="lg" p="md" style={{ position: 'sticky', top: 20 }}>
                        <div className={styles.panelHeader}>
                            <div className={styles.panelIconWrap}>
                                <IconCategory size={18} color="#3b82f6" />
                            </div>
                            <Text fw={700} size="sm" c="#0f172a">Kategori Hiyerarşisi</Text>
                        </div>

                        <TextInput
                            placeholder="Kategori ara..."
                            mb="md"
                            leftSection={<IconSearch size={15} />}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            radius="md"
                            size="sm"
                        />

                        <ScrollArea h={680} offsetScrollbars scrollbarSize={5}>
                            <Stack gap={0}>
                                {filteredTree.map((cat, idx) => (
                                    <CategoryTreeNode key={idx} node={cat} />
                                ))}
                            </Stack>
                        </ScrollArea>
                    </Card>
                </Grid.Col>

                {/* ───────────────────────────
                    Right Panel: Analysis
                ─────────────────────────── */}
                <Grid.Col span={{ base: 12, md: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>Kategori Analiz Raporu</h1>
                        <AISummaryButton 
                            contextType="category_report" 
                            contextId={selectedDataSourceId} 
                            contextData={{ category: selectedCategory?.name, revenue: details?.kpis.total_revenue }}
                        />
                    </div>

                    {error && (
                        <Alert icon={<IconAlertCircle size={16} />} title="Hata" color="red" mb="md" variant="light">
                            {error}
                        </Alert>
                    )}

                    {details && !loading && (
                        <div style={{ marginBottom: '16px' }}>
                            <AIInsightCard 
                                contextType="category_report" 
                                contextId={selectedDataSourceId.toString()} 
                                title={`${selectedCategory?.name} Kategorisi AI Yorumu`}
                                data={details}
                            />
                        </div>
                    )}

                    <LoadingOverlay loading={loading}>

                        {/* ── Empty State ── */}
                        {!details ? (
                            <div className={styles.emptyState}>
                                <div className={styles.emptyIcon}>
                                    <IconCategory size={72} />
                                </div>
                                <Text c="dimmed" size="sm" fw={500}>Analiz için bir kategori seçin</Text>
                            </div>
                        ) : (
                            <Stack gap="md">

                                {/* ── Category Header + KPIs ── */}
                                <div className={styles.sectionCard}>
                                    <div className={styles.sectionCardBody}>
                                        <Group justify="space-between" mb="md" wrap="nowrap" align="flex-start">
                                            <div>
                                                <h2 className={styles.catTitle}>{details.info.ana}</h2>
                                                <p className={styles.catSubtitle}>Seviye: {levelLabel}</p>
                                            </div>
                                            <div className={styles.tagRow}>
                                                {details.info.etiketler
                                                    ?.split(',')
                                                    .filter(Boolean)
                                                    .map((tag: string) => (
                                                        <Badge
                                                            key={tag}
                                                            variant="filled"
                                                            color="indigo"
                                                            size="sm"
                                                            rightSection={
                                                                <ActionIcon size="xs" color="white" variant="transparent" onClick={() => handleRemoveTag(tag)}>
                                                                    <IconTrash size={9} />
                                                                </ActionIcon>
                                                            }
                                                        >
                                                            {tag}
                                                        </Badge>
                                                    ))}
                                                <TextInput
                                                    placeholder="Yeni Etiket"
                                                    size="xs"
                                                    value={newTag}
                                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewTag(e.target.value)}
                                                    onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && handleAddTag()}
                                                    style={{ width: 110 }}
                                                    radius="md"
                                                />
                                                <Tooltip label="Etiket ekle">
                                                    <ActionIcon variant="light" color="indigo" radius="md" onClick={handleAddTag}>
                                                        <IconPlus size={15} />
                                                    </ActionIcon>
                                                </Tooltip>
                                            </div>
                                        </Group>

                                        {/* KPI Row */}
                                        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm">
                                            <div className={`${styles.kpiCard} ${styles.kpiCardBlue}`}>
                                                <div className={styles.kpiCardIcon}>
                                                    <IconCoin size={16} color="#3b82f6" />
                                                </div>
                                                <div className={styles.kpiLabel}>CİRO</div>
                                                <div className={styles.kpiValue}>
                                                    ₺{Math.round(details.kpis.total_revenue).toLocaleString()}
                                                </div>
                                            </div>

                                            <div className={`${styles.kpiCard} ${styles.kpiCardGreen}`}>
                                                <div className={styles.kpiCardIcon}>
                                                    <IconReceipt size={16} color="#10b981" />
                                                </div>
                                                <div className={styles.kpiLabel}>FİŞ SAYISI</div>
                                                <div className={styles.kpiValue}>
                                                    {details.kpis.total_receipts.toLocaleString()}
                                                </div>
                                            </div>

                                            <div className={`${styles.kpiCard} ${styles.kpiCardIndigo}`}>
                                                <div className={styles.kpiCardIcon}>
                                                    <IconUsers size={16} color="#4f46e5" />
                                                </div>
                                                <div className={styles.kpiLabel}>MÜŞTERİ</div>
                                                <div className={styles.kpiValue}>
                                                    {details.kpis.total_customers.toLocaleString()}
                                                </div>
                                            </div>

                                            <div className={`${styles.kpiCard} ${styles.kpiCardPurple}`}>
                                                <div className={styles.kpiCardIcon}>
                                                    <IconPackage size={16} color="#8b5cf6" />
                                                </div>
                                                <div className={styles.kpiLabel}>ADET</div>
                                                <div className={styles.kpiValue}>
                                                    {details.kpis.total_quantity.toLocaleString()}
                                                </div>
                                            </div>
                                        </SimpleGrid>
                                    </div>
                                </div>

                                {/* ── Trend + RFM Charts Row ── */}
                                <div className={styles.chartsRow}>
                                    <div className={`${styles.sectionCard} ${styles.chartTrend}`}>
                                        <div className={styles.sectionCardBody}>
                                            <p className={styles.sectionTitle}>Satış Trendi (Son 12 Ay)</p>
                                            <ReactECharts option={trendOption} style={{ height: 250 }} notMerge={true} />
                                        </div>
                                    </div>
                                    <div className={`${styles.sectionCard} ${styles.chartRfm}`}>
                                        <div className={styles.sectionCardBody}>
                                            <p className={styles.sectionTitle}>CRM Segmentasyonu</p>
                                            <ReactECharts option={rfmOption} style={{ height: 250 }} notMerge={true} />
                                        </div>
                                    </div>
                                </div>

                                {/* ── Comparison Section ── */}
                                {details.comparison.parentName && (
                                    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                                        {/* Hierarchy Share */}
                                        <div className={styles.sectionCard}>
                                            <div className={styles.sectionCardBody}>
                                                <Group justify="space-between" mb="xs">
                                                    <p className={styles.sectionTitle}>Hiyerarşi Payı</p>
                                                    <Badge color="blue" variant="light" size="sm">
                                                        {details.comparison.parentName}
                                                    </Badge>
                                                </Group>
                                                <Text size="xs" c="dimmed" mb="md">
                                                    Bu kategorinin bağlı olduğu gruptaki ağırlığı
                                                </Text>

                                                <Stack gap="lg" py="sm">
                                                    <div>
                                                        <Group justify="space-between" mb={6}>
                                                            <Text size="sm" fw={600}>Ciro Payı</Text>
                                                            <Text size="sm" fw={700} c="blue">
                                                                %{formatPercent(details.comparison.marketShare)}
                                                            </Text>
                                                        </Group>
                                                        <div className={styles.shareBar}>
                                                            <div
                                                                className={styles.shareBarFill}
                                                                style={{ width: `${Math.min(details.comparison.marketShare, 100)}%` }}
                                                            />
                                                        </div>
                                                    </div>

                                                    <SimpleGrid cols={2} spacing="sm">
                                                        <Paper withBorder p="xs" radius="md" bg="#f8fafc">
                                                            <Text size="xs" c="dimmed" fw={600}>Sektör Ort. Fiyat</Text>
                                                            <Text fw={700} size="sm">
                                                                ₺{Math.round(details.comparison.benchmarks.parentAvgPrice || 0).toLocaleString()}
                                                            </Text>
                                                        </Paper>
                                                        <Paper withBorder p="xs" radius="md" bg="#f8fafc">
                                                            <Text size="xs" c="dimmed" fw={600}>Bu Kat. Ort. Fiyat</Text>
                                                            <Text
                                                                fw={700}
                                                                size="sm"
                                                                c={details.kpis.avg_price > (details.comparison.benchmarks.parentAvgPrice || 0) ? 'red' : 'green'}
                                                            >
                                                                ₺{Math.round(details.kpis.avg_price).toLocaleString()}
                                                            </Text>
                                                        </Paper>
                                                    </SimpleGrid>
                                                </Stack>
                                            </div>
                                        </div>

                                        {/* Peers */}
                                        <div className={styles.sectionCard}>
                                            <div className={styles.sectionCardBody}>
                                                <p className={styles.sectionTitle}>Akran Kıyaslaması</p>
                                                <Text size="xs" c="dimmed" mb="sm">
                                                    {details.comparison.parentName} altındaki diğer kategoriler
                                                </Text>
                                                <ReactECharts option={comparisonOption} style={{ height: 200 }} notMerge={true} />
                                            </div>
                                        </div>
                                    </SimpleGrid>
                                )}

                                {/* ── Brand Share Trend ── */}
                                <div className={styles.sectionCard}>
                                    <div className={styles.sectionCardBody}>
                                        <div className={styles.sectionHeader}>
                                            <div>
                                                <p className={styles.sectionTitle}>Marka Pazar Payı Trendi</p>
                                                <p className={styles.sectionSubtitle}>Seçili markaların aylık pazar payı değişimi</p>
                                            </div>
                                            <Group gap="xs" wrap="nowrap">
                                                <Button
                                                    variant="subtle"
                                                    size="compact-xs"
                                                    color="blue"
                                                    onClick={() => setSelectedBrands(details?.brandTrends.map(bt => bt.name) || [])}
                                                >
                                                    Tümünü Seç
                                                </Button>
                                                <Button
                                                    variant="subtle"
                                                    size="compact-xs"
                                                    color="red"
                                                    onClick={() => setSelectedBrands([])}
                                                >
                                                    Tümünü Sil
                                                </Button>
                                                <MultiSelect
                                                    data={details?.brandTrends.map(bt => bt.name) || []}
                                                    value={selectedBrands}
                                                    onChange={setSelectedBrands}
                                                    placeholder="Marka seçin"
                                                    searchable
                                                    clearable
                                                    size="xs"
                                                    style={{ width: 220 }}
                                                    hidePickedOptions
                                                />
                                            </Group>
                                        </div>
                                        <ReactECharts option={brandShareOption} style={{ height: 320 }} notMerge={true} />
                                    </div>
                                </div>

                                {/* ── Brand Customer Distribution ── */}
                                <div className={styles.sectionCard}>
                                    <div className={styles.sectionCardBody}>
                                        <div className={styles.sectionHeader}>
                                            <div>
                                                <p className={styles.sectionTitle}>Marka Müşteri Dağılımı ve Penetrasyonu</p>
                                                <p className={styles.sectionSubtitle}>
                                                    Seçili markaların bu kategorideki eşsiz müşteri sayıları ve pazar payları
                                                </p>
                                            </div>
                                        </div>
                                        <ReactECharts option={brandCustomerOption} style={{ height: 320 }} notMerge={true} />
                                    </div>
                                </div>

                                {/* ── Top Products ── */}
                                <div className={styles.sectionCard}>
                                    <div className={styles.sectionCardBody}>
                                        <div className={styles.sectionHeader}>
                                            <div className={styles.sectionHeaderLeft}>
                                                <div className={styles.sectionIconWrap}>
                                                    <IconChartBar size={17} color="#3b82f6" />
                                                </div>
                                                <div>
                                                    <p className={styles.sectionTitle}>En Çok Satan Ürünler</p>
                                                    <p className={styles.sectionSubtitle}>Kategori liderleri</p>
                                                </div>
                                            </div>
                                            <Badge variant="dot" color="blue" size="sm">
                                                Kategori Liderleri
                                            </Badge>
                                        </div>

                                        <Stack gap="xs">
                                            {details.topProducts.map((p, i) => {
                                                const maxRev = details.topProducts[0]?.revenue || 1
                                                const pct    = (p.revenue / maxRev) * 100
                                                return (
                                                    <div key={i} className={styles.productRow}>
                                                        <div style={{ flex: '0 0 200px', minWidth: 0 }}>
                                                            <Text
                                                                size="sm"
                                                                fw={700}
                                                                c="blue"
                                                                lineClamp={2}
                                                                style={{ cursor: 'pointer' }}
                                                                onClick={() => navigate(`/products?productId=${p.product_id}`)}
                                                            >
                                                                {p.product_name}
                                                            </Text>
                                                            <Text size="10px" c="dimmed" fw={600} tt="uppercase" mt={2}>Ürün Adı</Text>
                                                        </div>
                                                        <div className={styles.productMetrics}>
                                                            <div className={styles.metricCol}>
                                                                <span className={styles.metricLabel}>Müşteri</span>
                                                                <span className={`${styles.metricValue} ${styles.metricBlue}`}>
                                                                    {(p.customer_count || 0).toLocaleString()}
                                                                </span>
                                                            </div>
                                                            <div className={styles.metricCol}>
                                                                <span className={styles.metricLabel}>Fiş</span>
                                                                <span className={`${styles.metricValue} ${styles.metricGreen}`}>
                                                                    {(p.receipt_count || 0).toLocaleString()}
                                                                </span>
                                                            </div>
                                                            <div className={styles.metricCol} style={{ flex: 1 }}>
                                                                <span className={styles.metricLabel}>
                                                                    Toplam Ciro (%{pct.toFixed(0)})
                                                                </span>
                                                                <span className={`${styles.metricValue} ${styles.metricBlue}`}>
                                                                    ₺{Math.round(p.revenue).toLocaleString()}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )
                                            })}
                                        </Stack>
                                    </div>
                                </div>

                                {/* ── Association Analysis ── */}
                                <div className={styles.sectionCard}>
                                    <div className={styles.sectionCardBody}>
                                        <div className={styles.sectionHeader}>
                                            <div className={styles.sectionHeaderLeft}>
                                                <div className={`${styles.sectionIconWrap} ${styles.sectionIconWrapGreen}`}>
                                                    <IconAffiliate size={17} color="#10b981" />
                                                </div>
                                                <div>
                                                    <p className={styles.sectionTitle}>Birliktelik Analizi</p>
                                                </div>
                                            </div>
                                            <SegmentedControl
                                                size="xs"
                                                radius="xl"
                                                value={recommendationStrategy}
                                                onChange={(val) => {
                                                    setRecommendationStrategy(val)
                                                    if (selectedCategory) {
                                                        loadCategoryDetails(selectedCategory.name, selectedCategory.level, val)
                                                    }
                                                }}
                                                data={[
                                                    { label: 'Garanti', value: 'volume' },
                                                    { label: 'Keşif',   value: 'discovery' },
                                                    { label: 'Kâr',     value: 'profit' },
                                                ]}
                                            />
                                        </div>

                                        <div className={styles.assocList}>
                                            {details.associations.map((assoc: any, i: number) => {
                                                const score      = assoc.score || 0
                                                const scoreClass = score > 0.7
                                                    ? styles.scoreHigh
                                                    : score > 0.4
                                                    ? styles.scoreMid
                                                    : styles.scoreLow

                                                return (
                                                    <div
                                                        key={i}
                                                        className={styles.assocCard}
                                                        onClick={() => {
                                                            if (selectedCategory) {
                                                                loadCategoryDetails(assoc.category_name, selectedCategory.level)
                                                                window.scrollTo({ top: 0, behavior: 'smooth' })
                                                            }
                                                        }}
                                                    >
                                                        <div className={styles.assocCategoryCol}>
                                                            <div className={styles.assocCategoryName}>
                                                                {assoc.category_name}
                                                            </div>
                                                            <div className={styles.assocCategoryTag}>
                                                                Kategori (Tıkla ve Git)
                                                            </div>
                                                        </div>

                                                        <div className={styles.assocMetrics}>
                                                            <div className={styles.metricCol}>
                                                                <span className={styles.metricLabel}>MÜŞTERİ</span>
                                                                <span className={`${styles.metricValue} ${styles.metricBlue}`}>
                                                                    {(assoc.ortak_musteri_sayisi || 0).toLocaleString()}
                                                                </span>
                                                            </div>
                                                            <div className={styles.metricCol}>
                                                                <span className={styles.metricLabel}>FİŞ</span>
                                                                <span className={`${styles.metricValue} ${styles.metricGreen}`}>
                                                                    {(assoc.ortak_fis_sayisi || 0).toLocaleString()}
                                                                </span>
                                                            </div>
                                                            <div className={styles.metricCol}>
                                                                <span className={styles.metricLabel}>GÜVEN</span>
                                                                <span className={`${styles.metricValue} ${styles.metricTeal}`}>
                                                                    %{Math.round((assoc.confidence || 0) * 100)}
                                                                </span>
                                                            </div>
                                                            <div className={styles.metricCol}>
                                                                <span className={styles.metricLabel}>LIFT</span>
                                                                <span className={`${styles.metricValue} ${styles.metricOrange}`}>
                                                                    {(assoc.lift || 0).toFixed(1)}x
                                                                </span>
                                                            </div>
                                                        </div>

                                                        <div className={`${styles.scoreCircle} ${scoreClass}`}>
                                                            {Math.round(score * 100)}
                                                        </div>
                                                    </div>
                                                )
                                            })}

                                            {details.associations.length === 0 && (
                                                <Paper
                                                    p="xl"
                                                    withBorder
                                                    style={{ borderStyle: 'dashed', borderColor: '#e2e8f0' }}
                                                >
                                                    <Text size="sm" c="dimmed" ta="center">
                                                        Veri henüz hesaplanmamış
                                                    </Text>
                                                </Paper>
                                            )}
                                        </div>
                                    </div>
                                </div>

                            </Stack>
                        )}
                    </LoadingOverlay>
                </Grid.Col>

            </Grid>

            {/* Kategori Terk Analizi */}
            {terkKategoriler.length > 0 && (
                <div style={{ marginTop: 32, paddingBottom: 32 }}>
                    <Text fw={600} size="md" mb="md">Kategori Terk Analizi</Text>
                    <Stack gap="xs">
                        {terkKategoriler.map(kat => (
                            <Card key={kat.ana_kategori} withBorder p={0}>
                                <Group
                                    justify="space-between"
                                    p="sm"
                                    style={{ cursor: 'pointer' }}
                                    onClick={() => toggleTerk(kat.ana_kategori)}
                                >
                                    <Group gap="sm">
                                        <IconChevronDown
                                            size={16}
                                            style={{
                                                transition: 'transform 0.2s',
                                                transform: terkAcik[kat.ana_kategori] ? 'rotate(180deg)' : 'none',
                                            }}
                                        />
                                        <Text fw={500}>{kat.ana_kategori}</Text>
                                        <Badge color="red" variant="light">{kat.musteri_sayisi} müşteri</Badge>
                                    </Group>
                                    <div onClick={(e) => e.stopPropagation()}>
                                        <ExcelExportButton
                                            url={`/veri-kaynaklari/${selectedDataSourceId}/kategori-terk-by-kategori/?ana_kategori=${encodeURIComponent(kat.ana_kategori)}&format=xlsx`}
                                            filename={`kategori_terk_${kat.ana_kategori}.xlsx`}
                                            label="Excel"
                                            size="xs"
                                        />
                                    </div>
                                </Group>
                                <Collapse in={!!terkAcik[kat.ana_kategori]}>
                                    <div style={{ padding: '0 12px 12px' }}>
                                        {terkYukleniyor[kat.ana_kategori] ? (
                                            <Text size="sm" c="dimmed" ta="center" py="md">Yükleniyor...</Text>
                                        ) : (
                                            <>
                                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                                                    <thead>
                                                        <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                                                            <th style={{ textAlign: 'left', padding: '6px 8px', color: '#64748b', fontWeight: 600 }}>Müşteri</th>
                                                            <th style={{ textAlign: 'left', padding: '6px 8px', color: '#64748b', fontWeight: 600 }}>Segment</th>
                                                            <th style={{ textAlign: 'right', padding: '6px 8px', color: '#64748b', fontWeight: 600 }}>Toplam Harcama</th>
                                                            <th style={{ textAlign: 'right', padding: '6px 8px', color: '#64748b', fontWeight: 600 }}>Terk Edilen Kat.</th>
                                                            <th style={{ textAlign: 'right', padding: '6px 8px', color: '#64748b', fontWeight: 600 }}>Harcama Değ. 3A</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(terkMusteri[kat.ana_kategori] || []).map((m: any) => (
                                                            <tr key={m.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                                <td style={{ padding: '6px 8px' }}>{m.ad}</td>
                                                                <td style={{ padding: '6px 8px' }}>
                                                                    <Badge size="xs" variant="light">{m.rfm_segment}</Badge>
                                                                </td>
                                                                <td style={{ textAlign: 'right', padding: '6px 8px' }}>
                                                                    ₺{(m.toplam_harcama || 0).toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
                                                                </td>
                                                                <td style={{ textAlign: 'right', padding: '6px 8px' }}>
                                                                    {m.terk_edilen_kategori_sayisi}
                                                                </td>
                                                                <td style={{
                                                                    textAlign: 'right',
                                                                    padding: '6px 8px',
                                                                    color: (m.harcama_degisim_3ay || 0) < 0 ? '#ef4444' : '#22c55e',
                                                                    fontWeight: 500,
                                                                }}>
                                                                    {(m.harcama_degisim_3ay || 0) > 0 ? '+' : ''}%{formatPercent(m.harcama_degisim_3ay || 0)}
                                                                </td>
                                                            </tr>
                                                        ))}
                                                        {(terkMusteri[kat.ana_kategori] || []).length === 0 && (
                                                            <tr>
                                                                <td colSpan={5} style={{ padding: '12px 8px', textAlign: 'center', color: '#94a3b8' }}>
                                                                    Veri bulunamadı
                                                                </td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                                {(terkToplam[kat.ana_kategori] || 0) > 20 && (
                                                    <Group justify="center" mt="sm">
                                                        <Pagination
                                                            value={terkSayfa[kat.ana_kategori] || 1}
                                                            total={Math.ceil((terkToplam[kat.ana_kategori] || 0) / 20)}
                                                            size="xs"
                                                            onChange={(s) => loadTerkMusteriler(kat.ana_kategori, s)}
                                                        />
                                                    </Group>
                                                )}
                                            </>
                                        )}
                                    </div>
                                </Collapse>
                            </Card>
                        ))}
                    </Stack>
                </div>
            )}
        </div>
    )
}
