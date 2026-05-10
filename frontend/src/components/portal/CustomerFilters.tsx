import { 
    Drawer, Stack, Paper, Text, SimpleGrid, Select, 
    MultiSelect, Group, TextInput, Accordion, Checkbox, 
    Button, Badge
} from '@mantine/core'
import { LABEL_KATEGORILER, LABEL_DISPLAY } from '../../constants/customerLabels'

interface CustomerFiltersProps {
    opened: boolean;
    onClose: () => void;
    // Filter States
    customerType: string | null;
    setCustomerType: (val: string | null) => void;
    approvalStatus: string | null;
    setApprovalStatus: (val: string | null) => void;
    region: string | null;
    setRegion: (val: string | null) => void;
    month: number | '';
    setMonth: (val: number | '') => void;
    year: number | '';
    setYear: (val: number | '') => void;
    startDate: string;
    setStartDate: (val: string) => void;
    endDate: string;
    setEndDate: (val: string) => void;
    selectedSegment: string[];
    setSelectedSegment: (val: string[]) => void;
    selectedLabels: string[];
    setSelectedLabels: (val: string[] | ((prev: string[]) => string[])) => void;
    activityStatus: string | null;
    setActivityStatus: (val: string | null) => void;
    trend: string | null;
    setTrend: (val: string | null) => void;
    minSpend: number | '';
    setMinSpend: (val: number | '') => void;
    minVisits: number | '';
    setMinVisits: (val: number | '') => void;
    maxSpend: number | '';
    setMaxSpend: (val: number | '') => void;
    churnRisk: string | null;
    setChurnRisk: (val: string | null) => void;
    basketSegment: string | null;
    setBasketSegment: (val: string | null) => void;
    // Actions
    onClearAll: () => void;
}

export const CustomerFilters = ({
    opened,
    onClose,
    customerType,
    setCustomerType,
    approvalStatus,
    setApprovalStatus,
    region,
    setRegion,
    month,
    setMonth,
    year,
    setYear,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    selectedSegment,
    setSelectedSegment,
    selectedLabels,
    setSelectedLabels,
    activityStatus,
    setActivityStatus,
    trend,
    setTrend,
    minSpend,
    setMinSpend,
    minVisits,
    setMinVisits,
    maxSpend,
    setMaxSpend,
    churnRisk,
    setChurnRisk,
    basketSegment,
    setBasketSegment,
    onClearAll
}: CustomerFiltersProps) => {
    
    const availableCustomerTypes = [
        { label: 'Bireysel', value: 'Bireysel' },
        { label: 'Kurumsal', value: 'Kurumsal' }
    ]
    const availableApprovalStatuses = [
        { label: 'Onaylı', value: 'Onaylı' },
        { label: 'Beklemede', value: 'Beklemede' },
        { label: 'Reddedildi', value: 'Reddedildi' }
    ]
    const availableRegions = [
        { label: 'Marmara', value: 'Marmara' },
        { label: 'Ege', value: 'Ege' },
        { label: 'Akdeniz', value: 'Akdeniz' }
    ]
    const availableYears = [2023, 2022, 2021, 2020]

    return (
        <Drawer
            opened={opened}
            onClose={onClose}
            title={<Text fw={700} size="lg">Filtreleme Seçenekleri</Text>}
            position="right"
            size="md"
        >
            <Stack gap="lg">
                <Paper withBorder p="md" radius="md" bg="#f8f9fa">
                    <Stack gap="md">
                        <Text size="xs" fw={700} color="dimmed">GENEL FİLTRELER</Text>
                        <SimpleGrid cols={2} spacing="xs">
                            <Select 
                                label="Müşteri Tipi" 
                                placeholder="Seçiniz" 
                                data={availableCustomerTypes} 
                                value={customerType} 
                                onChange={setCustomerType}
                                clearable
                            />
                            <Select 
                                label="Onay Durumu" 
                                placeholder="Seçiniz" 
                                data={availableApprovalStatuses} 
                                value={approvalStatus} 
                                onChange={setApprovalStatus}
                                clearable
                            />
                        </SimpleGrid>
                        <Select 
                            label="Bölge" 
                            placeholder="Seçiniz" 
                            data={availableRegions} 
                            value={region} 
                            onChange={setRegion}
                            clearable
                        />
                        <SimpleGrid cols={2} spacing="xs">
                            <Select 
                                label="Ay" 
                                placeholder="Tümü" 
                                data={[1,2,3,4,5,6,7,8,9,10,11,12].map(m => ({ label: `${m}. Ay`, value: m.toString() }))} 
                                value={month ? month.toString() : null} 
                                onChange={(v) => setMonth(v ? Number(v) : '')}
                                clearable
                            />
                            <Select 
                                label="Yıl" 
                                placeholder="Tümü" 
                                data={availableYears.map(y => ({ label: y.toString(), value: y.toString() }))} 
                                value={year ? year.toString() : null} 
                                onChange={(v) => setYear(v ? Number(v) : '')}
                                clearable
                            />
                        </SimpleGrid>
                    </Stack>
                </Paper>

                <Paper withBorder p="md" radius="md" bg="#f8f9fa">
                    <Stack gap="md">
                        <Text size="xs" fw={700} color="dimmed">TARİH ARALIĞI</Text>
                        <Group grow gap="xs">
                            <TextInput type="date" label="Başlangıç" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                            <TextInput type="date" label="Bitiş" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                        </Group>
                    </Stack>
                </Paper>

                <Paper withBorder p="md" radius="md" bg="#fceaff">
                    <Stack gap="md">
                        <Text size="xs" fw={700} color="grape">GELİŞMİŞ ANALİTİK</Text>
                        <MultiSelect
                            label="RFM Segmentleri"
                            placeholder="Segment seçiniz"
                            data={[
                                { label: 'Şampiyonlar', value: 'Sampiyonlar' },
                                { label: 'Sadıklar', value: 'Sadiklar' },
                                { label: 'Potansiyel Şampiyonlar', value: 'Potansiyel Sampiyonlar' },
                                { label: 'Yeni Müşteriler', value: 'Yeni Musteriler' },
                                { label: 'Adaylar', value: 'Sadik Olmaya Adaylar' },
                                { label: 'Tekrar Kazanılanlar', value: 'Tekrar Kazanilanlar' },
                                { label: 'Yüksek Harcama', value: 'Yuksek Harcama Yapanlar' },
                                { label: 'İlgi Bekleyenler', value: 'Ilgi Bekleyenler' },
                                { label: 'Risk Altındakiler', value: 'Risk Altindakiler' },
                                { label: 'Uyuyanlar', value: 'Uyuyanlar' },
                                { label: 'Kayıp Müşteriler', value: 'Kayip Musteriler' }
                            ]}
                            value={selectedSegment}
                            onChange={setSelectedSegment}
                            searchable
                        />
                        {/* Davranış Etiketleri - Kategori bazlı */}
                        <Text size="xs" fw={700} color="dimmed" mt="xs">DAVRANIŞ ETİKETLERİ</Text>
                        {selectedLabels.length > 0 && (
                            <Group gap={4} wrap="wrap">
                                {selectedLabels.map(lbl => (
                                    <Badge key={lbl} size="xs" variant="filled" color="violet"
                                        rightSection={<span style={{ cursor: 'pointer', marginLeft: 2 }} onClick={() => setSelectedLabels(prev => (prev as string[]).filter(l => l !== lbl))}>×</span>}>
                                        {LABEL_DISPLAY[lbl] || lbl}
                                    </Badge>
                                ))}
                                <Badge size="xs" variant="outline" color="red" style={{ cursor: 'pointer' }} onClick={() => setSelectedLabels([])}>Temizle</Badge>
                            </Group>
                        )}
                        <Accordion variant="separated" radius="md" chevronSize={16}>
                            {LABEL_KATEGORILER.map(kat => {
                                const secili = kat.etiketler.filter(e => selectedLabels.includes(e.value)).length
                                return (
                                    <Accordion.Item key={kat.key} value={kat.key} style={{ border: `1px solid ${secili > 0 ? kat.renk + '60' : '#e9ecef'}`, background: secili > 0 ? kat.renk + '08' : undefined }}>
                                        <Accordion.Control>
                                            <Group gap="xs">
                                                <span style={{ color: kat.renk, display: 'flex' }}>{kat.icon}</span>
                                                <Text size="sm" fw={600}>{kat.ad}</Text>
                                                {secili > 0 && <Badge size="xs" variant="filled" style={{ background: kat.renk }}>{secili}</Badge>}
                                            </Group>
                                        </Accordion.Control>
                                        <Accordion.Panel>
                                            <Checkbox.Group value={selectedLabels} onChange={(vals) => setSelectedLabels(vals)}>
                                                <Stack gap={6}>
                                                    {kat.etiketler.map(e => (
                                                        <Checkbox key={e.value} value={e.value} label={e.label} size="sm" color={kat.renk} />
                                                    ))}
                                                </Stack>
                                            </Checkbox.Group>
                                        </Accordion.Panel>
                                    </Accordion.Item>
                                )
                            })}
                        </Accordion>
                        <SimpleGrid cols={2} spacing="xs">
                            <Select label="Aktivite" data={['Cok Aktif', 'Aktif', 'Pasif', 'Uyuyan']} value={activityStatus} onChange={setActivityStatus} clearable />
                            <Select label="Trend" data={['Yukseliyor', 'Dusuyor', 'Stabil']} value={trend} onChange={setTrend} clearable />
                        </SimpleGrid>
                        <Group grow gap="xs">
                            <TextInput label="Min Harcama" type="number" value={minSpend} onChange={(e) => setMinSpend(e.target.value ? Number(e.target.value) : '')} />
                            <TextInput label="Max Harcama" type="number" value={maxSpend} onChange={(e) => setMaxSpend(e.target.value ? Number(e.target.value) : '')} />
                        </Group>
                        <Group grow gap="xs">
                            <TextInput label="Min Ziyaret" type="number" value={minVisits} onChange={(e) => setMinVisits(e.target.value ? Number(e.target.value) : '')} />
                            <Select label="Churn Riski" data={['Yuksek', 'Orta', 'Dusuk']} value={churnRisk} onChange={setChurnRisk} clearable />
                        </Group>
                        <Select 
                            label="Sepet Segmenti" 
                            placeholder="Tüm Sepetler"
                            data={[
                                { label: 'Küçük Sepet (0-200₺)', value: 'kucuk' },
                                { label: 'Orta Sepet (200-1.000₺)', value: 'orta' },
                                { label: 'Büyük Sepet (1.000-3.000₺)', value: 'buyuk' },
                                { label: 'Mega Sepet (3.000₺+)', value: 'mega' }
                            ]} 
                            value={basketSegment} 
                            onChange={setBasketSegment} 
                            clearable 
                        />
                    </Stack>
                </Paper>

                <Button fullWidth color="blue" onClick={onClose}>Filtreleri Uygula</Button>
                <Button fullWidth variant="light" color="red" onClick={onClearAll}>Tümünü Temizle</Button>
            </Stack>
        </Drawer>
    )
}
