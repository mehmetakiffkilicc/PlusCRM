import React, { useState, useEffect, useMemo, Suspense, lazy } from 'react';
import useDashboardStore from '../stores/dashboardStore';
import ExcelExportButton from '../components/ExcelExportButton';
import { 
  Title, Text, Paper, Group, Stack, Button, 
  Table, ScrollArea, ActionIcon, 
  Loader, Badge, SimpleGrid, ThemeIcon,
  Box, Avatar
} from '@mantine/core';
import { 
  IconBuildingStore, IconChartBar, 
  IconTrendingUp, IconAlertCircle,
  IconRefresh, IconCash, IconShoppingBag, IconTable
} from '@tabler/icons-react';
import { useMediaQuery } from '@mantine/hooks';
import apiClient from '../api/client';
import { notifications } from '@mantine/notifications';
import { AISummaryButton } from '../components/ai/AISummaryButton';
import { AIInsightCard } from '../components/ai/AIInsightCard';

// Lazy load chart for better performance
const Chart = lazy(() => import('../components/Chart'));

import '../styles/PageLayout.css';

interface StoreStat {
  magaza: string;
  bolge: string;
  ciro: number;
  fisAdedi: number;
  miktar: number;
  sepetOrtalaması: number;
  gunlukOrtCiro: number;
}

export default function StoreAnalysis() {
  const [data, setData] = useState<StoreStat[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { selectedRegion, selectedStartDate, selectedEndDate, selectedCustomerType, selectedApprovalStatus } = useDashboardStore();
  const [regions, setRegions] = useState<string[]>([]);
  const isMobile = useMediaQuery('(max-width: 768px)');

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getStoreAnalysis({
        region: selectedRegion || undefined,
        start_date: selectedStartDate || undefined,
        end_date: selectedEndDate || undefined,
        customer_type: selectedCustomerType || undefined,
        approval_status: selectedApprovalStatus || undefined
      });
      
      if (response && response.status === 'success') {
        setData(response.data);
        setSummary(response.summary);
        
        if (regions.length === 0) {
          const uniqueRegions = Array.from(new Set(response.data.map((s: StoreStat) => s.bolge))) as string[];
          setRegions(uniqueRegions.sort());
        }
      }
    } catch (error) {
      console.error('Store analysis fetch error:', error);
      notifications.show({
        title: 'Hata',
        message: 'Mağaza verileri yüklenirken bir sorun oluştu.',
        color: 'red',
        icon: <IconAlertCircle size={16} />
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedRegion, selectedStartDate, selectedEndDate, selectedCustomerType, selectedApprovalStatus]);

  const chartData = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.ciro - a.ciro).slice(0, 10);
    return {
      labels: sorted.map(s => s.magaza),
      values: sorted.map(s => s.ciro)
    };
  }, [data]);
  const handleClearFilters = () => {
    useDashboardStore.getState().resetFilters();
  };
  const exportUrl = `/magaza-analizi/disa-aktar/?` + new URLSearchParams({
    ...(selectedRegion && { region: selectedRegion }),
    ...(selectedStartDate && { start_date: selectedStartDate }),
    ...(selectedEndDate && { end_date: selectedEndDate }),
    ...(selectedCustomerType && { customer_type: selectedCustomerType }),
    ...(selectedApprovalStatus && { approval_status: selectedApprovalStatus })
  }).toString();

  return (
    <div className="page-content">
      {/* Header Section */}
      <Paper p="xl" radius="lg" className="section-card" withBorder>
        <Group justify="space-between" align="flex-start">
          <Stack gap={4}>
            <Group gap="xs">
              <ThemeIcon variant="light" size="xl" color="indigo" radius="md">
                <IconBuildingStore size={28} />
              </ThemeIcon>
              <Title order={2} fw={800} style={{ letterSpacing: '-0.5px' }}>
                Mağaza Performans Analizi
              </Title>
            </Group>
            <Text c="dimmed" size="sm" ml={48}>
              Şubelerinizin ciro, verimlilik ve bölge bazlı performans metrikleri.
            </Text>
          </Stack>

          <Group gap="sm" mt={isMobile ? 'md' : 0}>
            <ExcelExportButton 
              url={exportUrl}
              filename={`Magaza_Analizi_${new Date().toISOString().slice(0,10)}.xlsx`}
              label="Excel Aktar"
              color="indigo"
              size="sm"
            />
            <AISummaryButton 
              contextType="store_analysis" 
              contextId={selectedRegion || 'all'}
              contextData={{ summary, store_count: data.length }}
            />
            <ActionIcon variant="light" color="indigo" size="lg" onClick={fetchData} loading={loading} radius="md">
              <IconRefresh size={20} />
            </ActionIcon>
          </Group>
        </Group>
      </Paper>

      {/* KPI Cards */}
      {summary && (
        <div className="kpi-summary-grid">
          <Paper className="kpi-gradient-card kpi-gradient-indigo">
            <Text className="kpi-card-label">Toplam Ciro</Text>
            <Text className="kpi-card-value">
              ₺{summary.totalCiro.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
            </Text>
            <Text className="kpi-card-sub">{summary.totalStores} Mağaza Toplamı</Text>
            <IconCash className="kpi-card-icon" size={80} />
          </Paper>

          <Paper className="kpi-gradient-card kpi-gradient-green">
            <Text className="kpi-card-label">Toplam Fiş</Text>
            <Text className="kpi-card-value">
              {summary.totalFis.toLocaleString('tr-TR')}
            </Text>
            <Text className="kpi-card-sub">Gerçekleşen İşlem Sayısı</Text>
            <IconShoppingBag className="kpi-card-icon" size={80} />
          </Paper>

          <Paper className="kpi-gradient-card kpi-gradient-violet">
            <Text className="kpi-card-label">Ort. Sepet Tutarı</Text>
            <Text className="kpi-card-value">
              ₺{(summary.totalCiro / (summary.totalFis || 1)).toLocaleString('tr-TR', { maximumFractionDigits: 2 })}
            </Text>
            <Text className="kpi-card-sub">Sipariş Başına Ortalama</Text>
            <IconTrendingUp className="kpi-card-icon" size={80} />
          </Paper>

          <Paper className="kpi-gradient-card kpi-gradient-slate">
            <Text className="kpi-card-label">Aktif Mağazalar</Text>
            <Text className="kpi-card-value">
              {summary.totalStores}
            </Text>
            <Text className="kpi-card-sub">Satış Yapan Şubeler</Text>
            <IconBuildingStore className="kpi-card-icon" size={80} />
          </Paper>
        </div>
      )}

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {/* Chart Section */}
        <Paper p="xl" radius="lg" className="section-card" withBorder>
          <Group mb="xl" justify="space-between">
            <Group gap="sm">
              <ThemeIcon variant="light" color="indigo" radius="md">
                <IconChartBar size={20} />
              </ThemeIcon>
              <Text fw={700} size="lg">En Yüksek Cirolu Mağazalar (Top 10)</Text>
            </Group>
          </Group>
          <Box h={350}>
            <Suspense fallback={<Loader variant="dots" />}>
              {data.length > 0 ? (
                <Chart 
                  type="bar" 
                  manualData={chartData} 
                  height="100%" 
                />
              ) : (
                <Stack align="center" justify="center" h="100%" gap="xs">
                  <IconChartBar size={40} color="#e5e7eb" />
                  <Text c="dimmed">Görselleştirilecek veri bulunmuyor.</Text>
                </Stack>
              )}
            </Suspense>
          </Box>
        </Paper>

        {/* AI Insight Section */}
        {data.length > 0 && (
          <AIInsightCard 
            contextType="store_analysis" 
            contextId={selectedRegion || 'all'}
            dataSourceId={localStorage.getItem('activeDataSourceId') || ''}
            title="Mağaza Zekası ve AI Gözlemleri"
            staticText="Mağaza performans trendleri ve anomali tespiti için AI analizi."
            data={{ summary, top_stores: data.slice(0, 5) }}
          />
        )}
      </SimpleGrid>

      {/* Table Section */}
      <Paper radius="lg" className="section-card-table" withBorder>
        <div className="section-card-table-header">
          <Group justify="space-between">
            <Group gap="xs">
              <IconTable size={20} color="#6366f1" />
              <Text fw={700}>Mağaza Karşılaştırma Listesi</Text>
              <Badge variant="light" color="indigo" size="sm">{data.length} Mağaza</Badge>
            </Group>
          </Group>
        </div>

        <ScrollArea h={500} scrollbars="y">
          {loading ? (
            <Stack align="center" py={100} gap="md">
              <Loader color="indigo" variant="bars" />
              <Text size="sm" c="dimmed">Mağaza verileri işleniyor...</Text>
            </Stack>
          ) : data.length === 0 ? (
            <Stack align="center" py={100} gap="xs">
              <IconBuildingStore size={48} color="#e5e7eb" />
              <Text fw={600} c="dimmed">Eşleşen mağaza verisi bulunamadı.</Text>
              <Button variant="subtle" size="xs" onClick={handleClearFilters}>
                Filtreleri Temizle
              </Button>
            </Stack>
          ) : (
            <Table highlightOnHover verticalSpacing="md" horizontalSpacing="xl" className="premium-table">
              <Table.Thead style={{ backgroundColor: '#f8fafc', position: 'sticky', top: 0, zIndex: 10 }}>
                <Table.Tr>
                  <Table.Th w={60}>Sıra</Table.Th>
                  <Table.Th>Mağaza Adı</Table.Th>
                  <Table.Th>Bölge</Table.Th>
                  <Table.Th ta="right">Ciro</Table.Th>
                  <Table.Th ta="right">Fiş Adedi</Table.Th>
                  <Table.Th ta="right">Miktar</Table.Th>
                  <Table.Th ta="right">Sepet Ort.</Table.Th>
                  <Table.Th ta="right">Günlük Ort.</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.map((item, idx) => (
                  <Table.Tr key={item.magaza}>
                    <Table.Td>
                      <Text size="sm" fw={600} c="dimmed">#{idx + 1}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="sm">
                        <Avatar color="indigo" radius="sm" size="sm">{item.magaza.charAt(0)}</Avatar>
                        <Text size="sm" fw={600}>{item.magaza}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="dot" color="blue">{item.bolge}</Badge>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm" fw={700}>₺{item.ciro.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</Text>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm">{item.fisAdedi.toLocaleString('tr-TR')}</Text>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm">{item.miktar.toLocaleString('tr-TR')}</Text>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm" fw={600} c="teal">₺{item.sepetOrtalaması.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</Text>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm">₺{item.gunlukOrtCiro.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </ScrollArea>
      </Paper>
    </div>
  );
}

