import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { Group, Badge, Loader, ThemeIcon, Modal, Text, Title, Select } from '@mantine/core'
import { 
    IconClock, IconAlertCircle, IconChevronDown, IconChevronRight,
    IconBuildingWarehouse
} from '@tabler/icons-react'
import apiClient from '../../api/client'
import { BeklenenMusteri, BeklenenMusteriResponse } from '../../types/customer'
import ExcelExportButton from '../ExcelExportButton'

interface Store {
    id: string
    ad: string
    bolge: string
}

interface BeklenenMusteriSectionProps {
    activeDataSourceId: string | null
    onCustomerClick: (id: number) => void
    formatOnlyDate: (dateStr: string | null | undefined) => string
}

export const BeklenenMusteriSection: React.FC<BeklenenMusteriSectionProps> = ({
    activeDataSourceId,
    onCustomerClick,
    formatOnlyDate
}) => {
    // Mağaza State
    const [stores, setStores] = useState<Store[]>([])
    const [selectedStore, setSelectedStore] = useState<string | null>(null)
    const [storesLoading, setStoresLoading] = useState(false)

    // Beklenen Müşteriler State
    const [beklenen, setBeklenen] = useState<BeklenenMusteriResponse | null>(null)
    const [beklenenLoading, setBeklenenLoading] = useState(false)
    const [beklenenExpanded, setBeklenenExpanded] = useState(false)
    const [beklenenError, setBeklenenError] = useState(false)
    const [beklenenFiltre, setBeklenenFiltre] = useState<'bugun' | 'bu_hafta' | '7_gun' | 'bu_ay'>('bu_hafta')
    const [beklenenSort, setBeklenenSort] = useState<{ key: keyof BeklenenMusteri; order: 'asc' | 'desc' }>({ key: 'tahmini_ziyaret_tarihi', order: 'asc' })

    // Geciken Müşteriler State
    const [geciken, setGeciken] = useState<BeklenenMusteriResponse | null>(null)
    const [gecikenLoading, setGecikenLoading] = useState(false)
    const [gecikenExpanded, setGecikenExpanded] = useState(false)
    const [gecikenError, setGecikenError] = useState(false)
    const [gecikenFiltre, setGecikenFiltre] = useState<'bugun' | 'bu_hafta' | 'bu_ay' | '7_gun' | '30_gun'>('30_gun')
    const [gecikenSort, setGecikenSort] = useState<{ key: keyof BeklenenMusteri; order: 'asc' | 'desc' }>({ key: 'gecikme_gun', order: 'desc' })

    // Tümünü Gör Modal State
    const [tumunuGorTip, setTumunuGorTip] = useState<'beklenen' | 'geciken' | null>(null)
    const [tumunuGorMusteriler, setTumunuGorMusteriler] = useState<BeklenenMusteri[]>([])
    const [tumunuGorToplam, setTumunuGorToplam] = useState(0)
    const [tumunuGorPage, setTumunuGorPage] = useState(1)
    const [tumunuGorHasMore, setTumunuGorHasMore] = useState(true)
    const [tumunuGorLoading, setTumunuGorLoading] = useState(false)

    const PAGE_SIZE_MODAL = 50

    // Fetch methods
    useEffect(() => {
        if (!activeDataSourceId) return
        setStoresLoading(true)
        apiClient.get('/magazalar/')
            .then(res => setStores(res.data.stores || []))
            .catch(() => setStores([]))
            .finally(() => setStoresLoading(false))
    }, [activeDataSourceId])

    const fetchBeklenen = useCallback(() => {
        if (!activeDataSourceId || !beklenenExpanded) return
        setBeklenenLoading(true)
        setBeklenenError(false)
        const storeParam = selectedStore ? `&magaza_id=${selectedStore}` : ''
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/beklenen-musteriler/?limit=50&tip=beklenen&filtre=${beklenenFiltre}&sort_by=${beklenenSort.key}&sort_order=${beklenenSort.order}${storeParam}`)
            .then(res => setBeklenen(res.data))
            .catch(() => { setBeklenenError(true) })
            .finally(() => setBeklenenLoading(false))
    }, [activeDataSourceId, beklenenExpanded, beklenenFiltre, beklenenSort, selectedStore])

    const fetchGeciken = useCallback(() => {
        if (!activeDataSourceId || !gecikenExpanded) return
        setGecikenLoading(true)
        setGecikenError(false)
        const storeParam = selectedStore ? `&magaza_id=${selectedStore}` : ''
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/beklenen-musteriler/?limit=50&tip=geciken&filtre=${gecikenFiltre}&sort_by=${gecikenSort.key}&sort_order=${gecikenSort.order}${storeParam}`)
            .then(res => setGeciken(res.data))
            .catch(() => { setGecikenError(true) })
            .finally(() => setGecikenLoading(false))
    }, [activeDataSourceId, gecikenExpanded, gecikenFiltre, gecikenSort, selectedStore])

    useEffect(() => { fetchBeklenen() }, [fetchBeklenen])
    useEffect(() => { fetchGeciken() }, [fetchGeciken])

    const fetchTumunuGorPage = (tip: 'beklenen' | 'geciken', pageNum: number, currentSort: any, filtre?: string) => {
        if (!activeDataSourceId) return
        setTumunuGorLoading(true)
        const filtrePar = filtre || (tip === 'geciken' ? gecikenFiltre : beklenenFiltre)
        const storeParam = selectedStore ? `&magaza_id=${selectedStore}` : ''
        apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/beklenen-musteriler/?limit=${PAGE_SIZE_MODAL}&page=${pageNum}&tip=${tip}&filtre=${filtrePar}&sort_by=${currentSort.key}&sort_order=${currentSort.order}${storeParam}`)
            .then(res => {
                const newItems: BeklenenMusteri[] = res.data.musteriler || []
                setTumunuGorMusteriler(prev => pageNum === 1 ? newItems : [...prev, ...newItems])
                if (res.data.toplam >= 0) setTumunuGorToplam(res.data.toplam)
                setTumunuGorHasMore(newItems.length === PAGE_SIZE_MODAL)
            })
            .catch(() => {})
            .finally(() => setTumunuGorLoading(false))
    }

    const openTumunuGor = (tip: 'beklenen' | 'geciken') => {
        const sortToUse = tip === 'geciken' ? gecikenSort : beklenenSort
        setTumunuGorTip(tip)
        setTumunuGorMusteriler([])
        setTumunuGorToplam(0)
        setTumunuGorPage(1)
        setTumunuGorHasMore(true)
        fetchTumunuGorPage(tip, 1, sortToUse)
    }

    useEffect(() => {
        if (!tumunuGorTip) return
        const sortToUse = tumunuGorTip === 'geciken' ? gecikenSort : beklenenSort
        setTumunuGorPage(1)
        fetchTumunuGorPage(tumunuGorTip, 1, sortToUse)
    }, [beklenenSort, gecikenSort, tumunuGorTip])

    const handleTumunuGorScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const el = e.currentTarget
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 100 && tumunuGorHasMore && !tumunuGorLoading && tumunuGorTip) {
            const nextPage = tumunuGorPage + 1
            const sortToUse = tumunuGorTip === 'geciken' ? gecikenSort : beklenenSort
            setTumunuGorPage(nextPage)
            fetchTumunuGorPage(tumunuGorTip, nextPage, sortToUse)
        }
    }

    const sortMusteriler = (lista: BeklenenMusteri[], sortCfg: { key: keyof BeklenenMusteri; order: 'asc' | 'desc' }) => {
        const guvenMap: Record<string, number> = { 'Yuksek': 3, 'Orta': 2, 'Dusuk': 1 }
        return [...lista].sort((a, b) => {
            let valA = a[sortCfg.key]
            let valB = b[sortCfg.key]
            if (valA === null || valA === undefined || valA === '') return (valB === null || valB === undefined || valB === '') ? 0 : 1
            if (valB === null || valB === undefined || valB === '') return -1
            if (sortCfg.key === 'guven_skoru') {
                const priorityA = guvenMap[valA as string] || 0
                const priorityB = guvenMap[valB as string] || 0
                return sortCfg.order === 'asc' ? priorityA - priorityB : priorityB - priorityA
            }
            if (typeof valA === 'string' && typeof valB === 'string') {
                const cmp = valA.localeCompare(valB, 'tr')
                return sortCfg.order === 'asc' ? cmp : -cmp
            }
            if (valA < valB) return sortCfg.order === 'asc' ? -1 : 1
            if (valA > valB) return sortCfg.order === 'asc' ? 1 : -1
            return 0
        })
    }

    const sortedBeklenenList = useMemo(() => sortMusteriler(beklenen?.musteriler || [], beklenenSort), [beklenen?.musteriler, beklenenSort])
    const sortedGecikenList = useMemo(() => sortMusteriler(geciken?.musteriler || [], gecikenSort), [geciken?.musteriler, gecikenSort])
    const sortedModalList = useMemo(() => {
        const currentSort = tumunuGorTip === 'geciken' ? gecikenSort : beklenenSort
        return sortMusteriler(tumunuGorMusteriler, currentSort)
    }, [tumunuGorMusteriler, tumunuGorTip, beklenenSort, gecikenSort])

    return (
        <>
            {/* Mağaza Filtresi */}
            <Group gap="sm" mb="md" align="center">
                <IconBuildingWarehouse size={18} color="#6b7280" />
                <Select
                    placeholder="Tüm Mağazalar"
                    data={stores.map(s => ({ value: String(s.id), label: `${s.ad} (${s.bolge})` }))}
                    value={selectedStore}
                    onChange={setSelectedStore}
                    clearable
                    searchable
                    size="sm"
                    style={{ minWidth: '250px' }}
                />
                {selectedStore && (
                    <Text size="xs" color="dimmed">
                        {stores.find(s => s.id === selectedStore)?.ad} mağazasına ait müşteriler gösteriliyor
                    </Text>
                )}
            </Group>

            {/* Bu Hafta Bekleniyor Card */}
            {(beklenen || beklenenLoading || beklenenError || !beklenenExpanded) && (
                <div style={{ background: 'white', borderRadius: '16px', border: '2px solid #fbbf24', boxShadow: '0 4px 20px rgba(251,191,36,0.15)', marginBottom: '12px', overflow: 'hidden' }}>
                    <div
                        style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 20px', cursor: 'pointer', background: 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)' }}
                        onClick={() => { setBeklenenExpanded(!beklenenExpanded); if (!beklenenExpanded) setGecikenExpanded(false) }}
                    >
                        <div style={{ background: '#f59e0b', borderRadius: '10px', padding: '8px', display: 'flex' }}>
                            <IconClock size={20} stroke={2} color="white" />
                        </div>
                        <div style={{ flex: 1 }}>
                            <Group gap={10}>
                                <span style={{ fontWeight: 700, fontSize: '1rem', color: '#92400e' }}>Bu Hafta Bekleniyor</span>
                                {beklenen && (
                                    <Badge variant="filled" color="orange" radius="xl">
                                        {beklenen.toplam.toLocaleString('tr-TR')} müşteri
                                    </Badge>
                                )}
                                {beklenenLoading && <Loader size="xs" color="orange" />}
                            </Group>
                            <Text size="xs" color="#78350f">Bu hafta ziyaret etmesi beklenen düzenli müşteriler</Text>
                        </div>
                        <div style={{ color: '#92400e' }}>{beklenenExpanded ? <IconChevronDown size={18} /> : <IconChevronRight size={18} />}</div>
                    </div>

                    {beklenenExpanded && (
                        <div style={{ padding: '10px 20px', background: '#fffbeb', borderTop: '1px solid #fde68a' }}>
                            <Group gap={8} mb="md">
                                {(['bugun', 'bu_hafta', '7_gun', 'bu_ay'] as const).map(f => (
                                    <button key={f} onClick={() => setBeklenenFiltre(f)} style={{
                                        padding: '4px 12px', borderRadius: '999px', border: '1px solid',
                                        borderColor: beklenenFiltre === f ? '#f59e0b' : '#fde68a',
                                        background: beklenenFiltre === f ? '#f59e0b' : 'white',
                                        color: beklenenFiltre === f ? 'white' : '#92400e',
                                        fontSize: '0.78rem', cursor: 'pointer'
                                    }}>{f === 'bugun' ? 'Bugün' : f === 'bu_hafta' ? 'Bu Hafta' : f === '7_gun' ? '7 Gün' : 'Bu Ay'}</button>
                                ))}
                            </Group>
                            {beklenen?.musteriler.length ? (
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                                        <thead>
                                            <tr style={{ background: '#f9fafb', borderBottom: '1px solid #f3f4f6' }}>
                                                <th style={{ textAlign: 'left', padding: '8px', cursor: 'pointer' }} onClick={() => setBeklenenSort({ key: 'ad_soyad', order: beklenenSort.order === 'asc' ? 'desc' : 'asc' })}>Müşteri</th>
                                                <th style={{ textAlign: 'center', padding: '8px' }}>Son Ziyaret</th>
                                                <th style={{ textAlign: 'center', padding: '8px' }}>Durum</th>
                                                <th style={{ textAlign: 'center', padding: '8px' }}>Segment</th>
                                                <th style={{ textAlign: 'right', padding: '8px' }}>Toplam Harcama</th>
                                                <th style={{ textAlign: 'right', padding: '8px' }}>Ort. Sepet</th>
                                                <th style={{ textAlign: 'right', padding: '8px', background: '#fef3c7', borderRadius: '6px 6px 0 0' }}>Tahmini Tutar</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sortedBeklenenList.slice(0, 10).map((m, i) => (
                                                <tr key={m.musteri_id} style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }} onClick={() => onCustomerClick(m.musteri_id)}>
                                                    <td style={{ padding: '8px' }}>{m.ad_soyad || `Müşteri #${m.musteri_id}`}</td>
                                                    <td style={{ textAlign: 'center', padding: '8px' }}>{formatOnlyDate(m.son_ziyaret_tarihi)}</td>
                                                    <td style={{ textAlign: 'center', padding: '8px' }}>
                                                        <Badge color={m.durum === 'Bugun' ? 'green' : 'orange'} variant="light">
                                                            {m.durum === 'Bugun' ? 'Bugün' : formatOnlyDate(m.tahmini_ziyaret_tarihi)}
                                                        </Badge>
                                                    </td>
                                                    <td style={{ padding: '8px' }}>{m.rfm_segment || '-'}</td>
                                                    <td style={{ textAlign: 'right', padding: '8px', fontWeight: 500 }}>₺{(m.toplam_harcama || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                                    <td style={{ textAlign: 'right', padding: '8px', color: '#6b7280' }}>₺{(m.ortalama_sepet_tutari || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                                    <td style={{ textAlign: 'right', padding: '8px', fontWeight: 700, color: '#d97706', background: '#fffbeb' }}>₺{(m.tahmini_alisveris_tutari || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    {beklenen.toplam > 10 && (
                                        <Text ta="center" py="sm" color="orange" fw={600} style={{ cursor: 'pointer' }} onClick={() => openTumunuGor('beklenen')}>
                                            Tümünü Gör — {beklenen.toplam} müşteri
                                        </Text>
                                    )}
                                </div>
                            ) : <Text ta="center" py="xl" c="dimmed">Müşteri bulunamadı</Text>}
                        </div>
                    )}
                </div>
            )}

            {/* Gelmesi Bekleniyordu Card */}
            {(geciken || gecikenLoading || gecikenError || !gecikenExpanded) && (
                <div style={{ background: 'white', borderRadius: '16px', border: '2px solid #ef4444', boxShadow: '0 4px 20px rgba(239,68,68,0.12)', marginBottom: '12px', overflow: 'hidden' }}>
                    <div
                        style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 20px', cursor: 'pointer', background: 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)' }}
                        onClick={() => { setGecikenExpanded(!gecikenExpanded); if (!gecikenExpanded) setBeklenenExpanded(false) }}
                    >
                        <div style={{ background: '#ef4444', borderRadius: '10px', padding: '8px', display: 'flex' }}>
                            <IconAlertCircle size={20} stroke={2} color="white" />
                        </div>
                        <div style={{ flex: 1 }}>
                            <Group gap={10}>
                                <span style={{ fontWeight: 700, fontSize: '1rem', color: '#991b1b' }}>Gelmesi Bekleniyordu</span>
                                {geciken && (
                                    <Badge variant="filled" color="red" radius="xl">
                                        {geciken.toplam.toLocaleString('tr-TR')} müşteri
                                    </Badge>
                                )}
                                {gecikenLoading && <Loader size="xs" color="red" />}
                            </Group>
                            <Text size="xs" color="#7f1d1d">Ziyaret tarihi geçmiş ancak henüz gelmeyenler</Text>
                        </div>
                        <div style={{ color: '#991b1b' }}>{gecikenExpanded ? <IconChevronDown size={18} /> : <IconChevronRight size={18} />}</div>
                    </div>

                    {gecikenExpanded && (
                        <div style={{ padding: '10px 20px', background: '#fef2f2', borderTop: '1px solid #fecaca' }}>
                             <Group gap={8} mb="md">
                                {(['bugun', 'bu_hafta', 'bu_ay', '30_gun'] as const).map(f => (
                                    <button key={f} onClick={() => setGecikenFiltre(f)} style={{
                                        padding: '4px 12px', borderRadius: '999px', border: '1px solid',
                                        borderColor: gecikenFiltre === f ? '#ef4444' : '#fecaca',
                                        background: gecikenFiltre === f ? '#ef4444' : 'white',
                                        color: gecikenFiltre === f ? 'white' : '#991b1b',
                                        fontSize: '0.78rem', cursor: 'pointer'
                                    }}>{f === 'bugun' ? 'Bugün' : f === 'bu_hafta' ? 'Bu Hafta' : f === 'bu_ay' ? 'Bu Ay' : '30 Gün'}</button>
                                ))}
                            </Group>
                            {geciken?.musteriler.length ? (
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                                        <thead>
                                            <tr style={{ background: '#f9fafb', borderBottom: '1px solid #f3f4f6' }}>
                                                <th style={{ textAlign: 'left', padding: '8px' }}>Müşteri</th>
                                                <th style={{ textAlign: 'center', padding: '8px' }}>Son Ziyaret</th>
                                                <th style={{ textAlign: 'center', padding: '8px' }}>Gecikme</th>
                                                <th style={{ textAlign: 'center', padding: '8px' }}>Segment</th>
                                                <th style={{ textAlign: 'right', padding: '8px' }}>Toplam Harcama</th>
                                                <th style={{ textAlign: 'right', padding: '8px' }}>Ort. Sepet</th>
                                                <th style={{ textAlign: 'right', padding: '8px', background: '#fee2e2', borderRadius: '6px 6px 0 0' }}>Tahmini Tutar</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sortedGecikenList.slice(0, 10).map((m, i) => (
                                                <tr key={m.musteri_id} style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }} onClick={() => onCustomerClick(m.musteri_id)}>
                                                    <td style={{ padding: '8px' }}>{m.ad_soyad || `Müşteri #${m.musteri_id}`}</td>
                                                    <td style={{ textAlign: 'center', padding: '8px' }}>{formatOnlyDate(m.son_ziyaret_tarihi)}</td>
                                                    <td style={{ textAlign: 'center', padding: '8px' }}>
                                                        <Badge color={m.gecikme_gun >= 30 ? 'red' : 'orange'} variant="filled">
                                                            +{m.gecikme_gun} gün
                                                        </Badge>
                                                    </td>
                                                    <td style={{ padding: '8px' }}>{m.rfm_segment || '-'}</td>
                                                    <td style={{ textAlign: 'right', padding: '8px', fontWeight: 500 }}>₺{(m.toplam_harcama || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                                    <td style={{ textAlign: 'right', padding: '8px', color: '#6b7280' }}>₺{(m.ortalama_sepet_tutari || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                                    <td style={{ textAlign: 'right', padding: '8px', fontWeight: 700, color: '#dc2626', background: '#fef2f2' }}>₺{(m.tahmini_alisveris_tutari || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    {geciken.toplam > 10 && (
                                        <Text ta="center" py="sm" color="red" fw={600} style={{ cursor: 'pointer' }} onClick={() => openTumunuGor('geciken')}>
                                            Tümünü Gör — {geciken.toplam} müşteri
                                        </Text>
                                    )}
                                </div>
                            ) : <Text ta="center" py="xl" c="dimmed">Müşteri bulunamadı</Text>}
                        </div>
                    )}
                </div>
            )}

            {/* Tümünü Gör Modal */}
            <Modal
                opened={tumunuGorTip !== null}
                onClose={() => { setTumunuGorTip(null); setTumunuGorMusteriler([]); setTumunuGorToplam(0) }}
                size="90%"
                radius="md"
                title={
                    <Group gap="sm" justify="space-between" style={{ width: '100%' }}>
                        <Group gap="sm">
                            <ThemeIcon size="lg" radius="md" color={tumunuGorTip === 'geciken' ? 'red' : 'yellow'}>
                                {tumunuGorTip === 'geciken' ? <IconAlertCircle size={18} /> : <IconClock size={18} />}
                            </ThemeIcon>
                            <div>
                                <Text fw={700}>{tumunuGorTip === 'geciken' ? 'Gelmesi Bekleniyordu' : 'Bu Hafta Bekleniyor'}</Text>
                                {tumunuGorToplam > 0 && <Text size="xs" c="dimmed">{tumunuGorToplam.toLocaleString('tr-TR')} müşteri</Text>}
                            </div>
                        </Group>
                        {tumunuGorTip && (
                            <ExcelExportButton
                                url={`/beklenen-musteriler-excel/?tip=${tumunuGorTip}`}
                                filename={tumunuGorTip === 'geciken' ? 'Geciken_Musteriler.xlsx' : 'Bu_Hafta_Beklenen.xlsx'}
                                label="Excel İndir"
                                size="xs"
                            />
                        )}
                    </Group>
                }
                styles={{ body: { padding: 0 } }}
            >
                <div style={{ maxHeight: '70vh', overflowY: 'auto' }} onScroll={handleTumunuGorScroll}>
                    {tumunuGorMusteriler.length > 0 ? (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                            <thead style={{ position: 'sticky', top: 0, zIndex: 1, background: '#f9fafb' }}>
                                <tr style={{ borderBottom: '2px solid #f3f4f6' }}>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Müşteri</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>Son Ziyaret</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>Durum/Gecikme</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>Segment</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>Güven</th>
                                    <th style={{ padding: '12px', textAlign: 'right' }}>Toplam Harcama</th>
                                    <th style={{ padding: '12px', textAlign: 'right' }}>Ort. Sepet</th>
                                    <th style={{ padding: '12px', textAlign: 'right', background: tumunuGorTip === 'geciken' ? '#fee2e2' : '#fef3c7', fontWeight: 700 }}>Tahmini Tutar</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedModalList.map((m) => (
                                    <tr key={m.musteri_id} style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }} onClick={() => { setTumunuGorTip(null); onCustomerClick(m.musteri_id) }}>
                                        <td style={{ padding: '12px' }}>
                                            <div style={{ fontWeight: 600 }}>{m.ad_soyad || `Müşteri #${m.musteri_id}`}</div>
                                            <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{m.telefon}</div>
                                        </td>
                                        <td style={{ textAlign: 'center', padding: '12px' }}>{formatOnlyDate(m.son_ziyaret_tarihi)}</td>
                                        <td style={{ textAlign: 'center', padding: '12px' }}>
                                            {tumunuGorTip === 'geciken' ? (
                                                <Badge color={m.gecikme_gun >= 30 ? 'red' : 'orange'} variant="filled">+{m.gecikme_gun} gün</Badge>
                                            ) : (
                                                <Badge color={m.durum === 'Bugun' ? 'green' : 'orange'} variant="light">{m.durum === 'Bugun' ? 'Bugün' : formatOnlyDate(m.tahmini_ziyaret_tarihi)}</Badge>
                                            )}
                                        </td>
                                        <td style={{ textAlign: 'center', padding: '12px' }}>{m.rfm_segment || '-'}</td>
                                        <td style={{ textAlign: 'center', padding: '12px' }}>
                                            <Text size="xs" fw={700} color={m.guven_skoru === 'Yuksek' ? 'green' : m.guven_skoru === 'Orta' ? 'orange' : 'gray'}>
                                                {m.guven_skoru || 'Düşük'}
                                            </Text>
                                        </td>
                                        <td style={{ textAlign: 'right', padding: '12px', fontWeight: 500 }}>₺{(m.toplam_harcama || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                        <td style={{ textAlign: 'right', padding: '12px', color: '#6b7280' }}>₺{(m.ortalama_sepet_tutari || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                        <td style={{ textAlign: 'right', padding: '12px', fontWeight: 700, color: tumunuGorTip === 'geciken' ? '#dc2626' : '#d97706', background: tumunuGorTip === 'geciken' ? '#fef2f2' : '#fffbeb' }}>₺{(m.tahmini_alisveris_tutari || 0).toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : tumunuGorLoading ? <Center py="xl"><Loader /></Center> : <Text ta="center" py="xl" c="dimmed">Müşteri bulunamadı</Text>}
                    {tumunuGorLoading && tumunuGorMusteriler.length > 0 && <Center py="md"><Loader size="sm" /></Center>}
                </div>
            </Modal>
        </>
    )
}

const Center: React.FC<{children: React.ReactNode, py?: string}> = ({children, py}) => (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: py || '0' }}>{children}</div>
)
