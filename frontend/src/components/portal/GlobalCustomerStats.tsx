import { useState, useEffect, ReactNode } from 'react'
import {
    Grid,
    Paper,
    Text,
    Title,
    Group,
    SimpleGrid,
    Badge,
    Progress,
    Stack,
    ThemeIcon,
    Alert,
    Button,
    Loader,
    Center,
    Box
} from '@mantine/core'
import {
    IconUsers,
    IconUserCheck,
    IconUserExclamation,
    IconClock,
    IconDatabase,
    IconPhone,
    IconBolt,
    IconTarget,
    IconAlertCircle
} from '@tabler/icons-react'
import apiClient from '../../api/client'
import LoadingOverlay from '../LoadingOverlay'

/* ── Genel tasarımdaki KPI kart bileşeni ─────────────────────────────── */
function KpiCard({ gradient, shadow, label, value, sub, icon }: {
    gradient: string; shadow: string; label: string; value: string; sub?: string; icon: ReactNode
}) {
    return (
        <div style={{
            background: gradient,
            borderRadius: '16px',
            padding: '24px',
            color: 'white',
            boxShadow: `0 10px 25px -5px ${shadow}`,
            position: 'relative',
            overflow: 'hidden',
            minHeight: 120,
        }}>
            <div style={{ fontSize: '0.8rem', opacity: 0.85, marginBottom: '8px', fontWeight: 600, letterSpacing: '0.3px' }}>{label}</div>
            <div style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1.1 }}>{value}</div>
            {sub && <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '6px' }}>{sub}</div>}
            <div style={{ position: 'absolute', right: '-10px', bottom: '-10px', opacity: 0.12 }}>{icon}</div>
        </div>
    )
}

export default function GlobalCustomerStats({ activeDataSourceId }: { activeDataSourceId: string | null }) {
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<any>(null)
    const [error, setError] = useState<string>('')

    useEffect(() => {
        if (activeDataSourceId) {
            fetchData()
        }
    }, [activeDataSourceId])

    const fetchData = async () => {
        setLoading(true)
        setError('')
        try {
            const response = await apiClient.get(`/veri-kaynaklari/${activeDataSourceId}/musteri-bilgisi/`)
            setData(response.data)
        } catch (err: any) {
            setError(err?.response?.data?.error || err?.message || 'Veriler alınamadı')
        } finally {
            setLoading(false)
        }
    }

    const getQualityColor = (quality: string) => {
        switch (quality) {
            case 'Mükemmel': return 'teal'
            case 'Çok İyi': return 'blue'
            case 'İyi': return 'yellow'
            case 'Orta': return 'orange'
            case 'Düşük': return 'red'
            default: return 'gray'
        }
    }

    if (!activeDataSourceId) {
        return (
            <Center h={200}>
                <Text color="dimmed">Lütfen bir veri kaynağı seçin.</Text>
            </Center>
        )
    }

    if (error) {
        return (
            <Alert icon={<IconAlertCircle size={16} />} title="Hata" color="red" variant="light" m="md">
                {error}
                <Button variant="outline" color="red" size="xs" mt="md" onClick={fetchData}>Tekrar Dene</Button>
            </Alert>
        )
    }

    return (
        <div style={{ position: 'relative' }}>
            <LoadingOverlay loading={loading}>
                {!data ? (
                    <Center h={400}><Loader size="xl" /></Center>
                ) : (
                    <Stack gap="xl">
                        {/* Özet Kartlar — genel tasarımla uyumlu KPI kartları */}
                        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
                            <KpiCard
                                gradient="linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)"
                                shadow="rgba(79,70,229,0.35)"
                                label="Toplam Müşteri"
                                value={data.summary.totalCustomers.toLocaleString('tr-TR')}
                                sub="Kayıtlı tüm müşteriler"
                                icon={<IconUsers size={80} stroke={1.2} />}
                            />
                            <KpiCard
                                gradient="linear-gradient(135deg, #10b981 0%, #059669 100%)"
                                shadow="rgba(16,185,129,0.35)"
                                label="Aktif Müşteri"
                                value={data.summary.activeCustomers.toLocaleString('tr-TR')}
                                sub="Kayıp/riskli segment dışı"
                                icon={<IconUserCheck size={80} stroke={1.2} />}
                            />
                            <KpiCard
                                gradient="linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"
                                shadow="rgba(239,68,68,0.35)"
                                label="Pasif Müşteri"
                                value={data.summary.inactiveCustomers.toLocaleString('tr-TR')}
                                sub="Kayıp veya riskli segment"
                                icon={<IconUserExclamation size={80} stroke={1.2} />}
                            />
                            <KpiCard
                                gradient="linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
                                shadow="rgba(245,158,11,0.35)"
                                label="Ort. Müşteri Yaşı"
                                value={`${data.summary.avgCustomerAge} yıl`}
                                sub="Kayıt tarihinden itibaren"
                                icon={<IconClock size={80} stroke={1.2} />}
                            />
                        </SimpleGrid>

                        <Grid>
                            {/* Veri Kalitesi */}
                            <Grid.Col span={{ base: 12, md: 6 }}>
                                <Paper withBorder p="xl" radius="md" shadow="sm">
                                    <Group mb="xl">
                                        <ThemeIcon color="blue" variant="light" size="lg" radius="md">
                                            <IconDatabase size={20} />
                                        </ThemeIcon>
                                        <Title order={4}>Veri Kalitesi ve Doluluk</Title>
                                    </Group>

                                    <Stack gap="lg">
                                        {data.dataQuality.map((item: any, idx: number) => (
                                            <Box key={idx}>
                                                <Group justify="space-between" mb={4}>
                                                    <Text size="sm" fw={600} color="gray.7">{item.field}</Text>
                                                    <Badge size="xs" color={getQualityColor(item.quality)} variant="light">
                                                        {item.quality}
                                                    </Badge>
                                                </Group>
                                                <Progress 
                                                    value={item.percentage} 
                                                    color={getQualityColor(item.quality)} 
                                                    size="sm" 
                                                    radius="xl"
                                                    mb={6}
                                                />
                                                <Group justify="space-between">
                                                    <Text size="xs" color="dimmed">%{item.percentage} Doluluk</Text>
                                                    <Text size="xs" color="red.6">{item.missing.toLocaleString('tr-TR')} Eksik</Text>
                                                </Group>
                                            </Box>
                                        ))}
                                    </Stack>
                                </Paper>
                            </Grid.Col>

                            {/* İletişim Tercihleri */}
                            <Grid.Col span={{ base: 12, md: 6 }}>
                                <Paper withBorder p="xl" radius="md" shadow="sm">
                                    <Group mb="xl">
                                        <ThemeIcon color="violet" variant="light" size="lg" radius="md">
                                            <IconPhone size={20} />
                                        </ThemeIcon>
                                        <Title order={4}>İletişim Kanalları</Title>
                                    </Group>

                                    <Stack gap="md">
                                        {data.contactPreferences.map((pref: any, idx: number) => (
                                            <Paper key={idx} withBorder p="md" radius="md" bg="gray.0">
                                                <Group wrap="nowrap">
                                                    <ThemeIcon variant="white" color="blue" size="lg" radius="md">
                                                        {pref.method.includes('SMS') ? '📱' : (pref.method.includes('Onay') ? '✔️' : '📧')}
                                                    </ThemeIcon>
                                                    <Stack gap={2} style={{ flex: 1 }}>
                                                        <Group justify="space-between">
                                                            <Text size="sm" fw={700}>{pref.method}</Text>
                                                            <Text size="sm" fw={800} color="blue.7">%{pref.percentage}</Text>
                                                        </Group>
                                                        <Text size="xs" color="dimmed">{pref.count.toLocaleString('tr-TR')} Müşteri</Text>
                                                    </Stack>
                                                </Group>
                                            </Paper>
                                        ))}
                                    </Stack>
                                </Paper>
                            </Grid.Col>
                        </Grid>

                        <Grid>
                            {/* Müşteri Aktivitesi */}
                            <Grid.Col span={{ base: 12, md: 6 }}>
                                <Paper withBorder p="xl" radius="md" shadow="sm">
                                    <Group mb="xl">
                                        <ThemeIcon color="orange" variant="light" size="lg" radius="md">
                                            <IconBolt size={20} />
                                        </ThemeIcon>
                                        <Title order={4}>Harcama Bazlı Aktivite</Title>
                                    </Group>

                                    <Stack gap="lg">
                                        {Object.entries(data.customerActivity).map(([key, value]: [string, any]) => {
                                            const labelMap: any = {
                                                highlyActive: 'Çok Aktif (8+ Sipariş)',
                                                active: 'Aktif (4-7 Sipariş)',
                                                moderate: 'Orta (2-3 Sipariş)',
                                                lowActivity: 'Düşük (1 Sipariş)',
                                                inactive: 'İnaktif'
                                            }
                                            const colorMap: any = {
                                                highlyActive: 'indigo',
                                                active: 'teal',
                                                moderate: 'yellow',
                                                lowActivity: 'gray',
                                                inactive: 'red'
                                            }
                                            return (
                                                <Box key={key}>
                                                    <Group justify="space-between" mb={4}>
                                                        <Text size="sm" fw={500}>{labelMap[key]}</Text>
                                                        <Text size="sm" fw={700}>{value.count.toLocaleString('tr-TR')} (%{value.percentage})</Text>
                                                    </Group>
                                                    <Progress value={value.percentage} color={colorMap[key]} size="md" radius="xl" striped />
                                                </Box>
                                            )
                                        })}
                                    </Stack>
                                </Paper>
                            </Grid.Col>

                            {/* İlgi Alanları */}
                            <Grid.Col span={{ base: 12, md: 6 }}>
                                <Paper withBorder p="xl" radius="md" shadow="sm">
                                    <Group mb="xl">
                                        <ThemeIcon color="teal" variant="light" size="lg" radius="md">
                                            <IconTarget size={20} />
                                        </ThemeIcon>
                                        <Title order={4}>Kategori İlgi Odakları</Title>
                                    </Group>

                                    <Stack gap="md">
                                        {data.topInterests.map((interest: any, idx: number) => (
                                            <Paper 
                                                key={idx} 
                                                withBorder 
                                                p="md" 
                                                radius="md" 
                                                style={{ borderLeft: `4px solid ${idx === 0 ? '#4f46e5' : '#e2e8f0'}`, background: '#f8fafc' }}
                                            >
                                                <Group justify="space-between">
                                                    <div>
                                                        <Text fw={700} size="sm">{interest.category}</Text>
                                                        <Text size="xs" color="dimmed">{interest.customers.toLocaleString('tr-TR')} Tekil Müşteri</Text>
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <Text fw={800} size="xl" color="indigo">%{interest.engagement}</Text>
                                                        <Text size="10px" fw={700} color="dimmed" style={{ textTransform: 'uppercase' }}>Etkileşim</Text>
                                                    </div>
                                                </Group>
                                            </Paper>
                                        ))}
                                    </Stack>
                                </Paper>
                            </Grid.Col>
                        </Grid>
                    </Stack>
                )}
            </LoadingOverlay>
        </div>
    )
}
