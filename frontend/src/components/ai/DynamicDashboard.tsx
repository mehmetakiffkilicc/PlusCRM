import React, { useEffect, useState, useMemo } from 'react';
import { SimpleGrid, Paper, Text, Stack, Card, Group, Badge, Loader, Center, ThemeIcon, Alert } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconMinus, IconAlertCircle, IconChartBar } from '@tabler/icons-react';
import apiClient from '../../api/client';
import Chart from '../Chart';

interface DashboardItem {
  type: 'kpi' | 'chart' | 'table' | 'nba';
  title: string;
  metric?: string;
  chartType?: 'bar' | 'line' | 'pie' | 'area';
  params?: Record<string, any>;
  width?: number;
}

interface DynamicDashboardProps {
  config: {
    layout?: 'grid' | 'stack';
    items: DashboardItem[];
  };
  dataSourceId: string;
}

async function fetchMetricValue(
  metric: string | undefined,
  dataSourceId: string,
  params?: Record<string, any>
): Promise<{ value: any; change?: number; trend?: string; chartData?: any[] ; error?: boolean }> {
  if (!metric) return { value: '—' };

  try {
    const toCamel = (s: string) => s.replace(/([-_][a-z])/g, group => group.toUpperCase().replace('-', '').replace('_', ''));
    
    if (metric.startsWith('kpi.')) {
      const kpis = await apiClient.getDashboardKpis({ data_source_id: dataSourceId, ...params });
      const key = metric.replace('kpi.', '');
      const dataObj = kpis?.data || kpis;
      
      const keyMap: Record<string, string> = {
        'revenue': 'totalRevenue',
        'sales': 'totalRevenue',
        'receipts': 'totalReceipts',
        'orders': 'totalReceipts',
        'customers': 'totalCustomers',
        'active_customers': 'totalCustomers',
        'registered': 'totalRegisteredCustomers',
        'registered_customers': 'totalRegisteredCustomers',
        'brands': 'totalBrands',
        'products': 'totalProducts',
        'aov': 'averageOrderValue',
        'churn_rate': 'churnRate',
        'loyalty': 'loyaltyShare'
      };
      
      const mappedKey = keyMap[key] || key;
      const possibleKeys = [mappedKey, toCamel(mappedKey), key, toCamel(key)];
      
      if (key === 'activeCustomerRate' || key === 'active_customer_rate') {
        const active = dataObj?.totalCustomers || 0;
        const total = dataObj?.totalRegisteredCustomers || 1;
        return { value: `%${((active / total) * 100).toFixed(1)}` };
      }
      
      let entry: any = undefined;
      for (const k of possibleKeys) {
        if (dataObj?.[k] !== undefined) {
          entry = dataObj[k];
          break;
        }
      }
      
      if (entry && typeof entry === 'object') {
        const changeValue = entry.change ?? 0;
        return {
          value: entry.value ?? '—',
          change: changeValue,
          trend: changeValue > 0 ? 'up' : changeValue < 0 ? 'down' : 'neutral',
        };
      }
      return { value: entry ?? '—' };
    }

    if (metric.startsWith('clv.')) {
      const clv = await apiClient.getCLVAnalysis(dataSourceId, params);
      const data = clv?.data || clv;
      const key = metric.replace('clv.', '');
      const mappedKey = key === 'average' || key === 'avg' ? 'average_clv' : key === 'total' ? 'total_clv' : key;
      return { 
        value: data?.summary?.[mappedKey] ?? data?.summary?.[toCamel(mappedKey)] ?? data?.summary?.averageCLV ?? '—' 
      };
    }

    if (metric === 'churn_rate' || metric.startsWith('churn.')) {
      const churn = await apiClient.getChurnAnalysis(dataSourceId, params);
      const summary = churn?.data?.summary ?? churn?.summary;
      if (!summary) {
        const kpis = await apiClient.getDashboardKpis({ data_source_id: dataSourceId, ...params });
        const kpiData = kpis?.data || kpis;
        if (kpiData?.churnRate !== undefined) {
           return { value: `%${kpiData.churnRate}`, change: 0, trend: 'neutral' };
        }
        return { value: '—' };
      }
      if (metric === 'churn_rate') return { value: `%${summary.churnRate || 0}`, change: 0, trend: 'neutral' };
      if (metric === 'churn.total') return { value: summary.churnedCustomers || 0, change: 0, trend: 'down' };
      if (metric === 'churn.at_risk') return { value: summary.atRiskCustomers || 0, change: 0, trend: 'neutral' };
      return { value: summary.churnRate ?? '—' };
    }

    if (metric === 'rfm_summary' || metric.startsWith('rfm.')) {
      const rfm = await apiClient.getRFMAnalysis(dataSourceId, params);
      const data = rfm?.data || rfm;
      if (!data) return { value: '—' };
      
      const chartData = data.segment_data ? Object.entries(data.segment_data).map(([name, info]: [string, any]) => ({
        name: name.includes('-)') ? name.split('-) ')[1] : name,
        value: info.count
      })) : [];

      if (metric === 'rfm_summary') return { value: data.total_unique_customers ?? '—', chartData };
      if (metric === 'rfm.champions') return { value: data.segment_data?.['01-) Şampiyonlar']?.count ?? data.segment_data?.['Şampiyonlar']?.count ?? '—' };
      if (metric === 'rfm.at_risk') return { value: data.segment_data?.['09-) Risk Altındakiler']?.count ?? data.segment_data?.['Risk Altında']?.count ?? '—' };
      return { value: data.total_unique_customers ?? '—', chartData };
    }

    if (metric === 'trend' || metric === 'revenue_trend' || metric.includes('trend')) {
      const trendRes = await apiClient.getDashboardTrend({ data_source_id: dataSourceId, ...params });
      const rows = trendRes?.trend ?? trendRes?.data?.trend ?? trendRes?.salesByMonth ?? trendRes?.data?.salesByMonth ?? [];
      return {
        value: rows.length > 0 ? rows[rows.length - 1]?.value ?? rows[rows.length - 1]?.ciro ?? '—' : '—',
        chartData: rows,
      };
    }
    
    if (metric === 'clv' || metric === 'clv.average') {
      const clv = await apiClient.getCLVAnalysis(dataSourceId, params);
      const summary = clv?.summary || clv?.data?.summary;
      return { 
        value: summary?.averageCLV ?? summary?.average_clv ?? '—',
        chartData: clv?.segmentDistribution || clv?.data?.segmentDistribution || []
      };
    }

    if (metric === 'category.top' || metric === 'category.all') {
      const data = await apiClient.getDataSourceAnalytics(dataSourceId, [], [], [], undefined, undefined, params?.start_date, params?.end_date);
      const cats = data?.analytics?.productCategories || [];
      return {
        value: cats.length > 0 ? (cats[0].name || cats[0].category || cats[0].category_name || '—') : '—',
        chartData: cats.map((c: any) => ({ name: c.name || c.category || c.category_name, value: c.revenue || c.sales || 0 }))
      };
    }

    if (metric === 'brand.top' || metric === 'brand.all') {
      const data = await apiClient.getDataSourceAnalytics(dataSourceId, [], [], [], undefined, undefined, params?.start_date, params?.end_date);
      const brands = data?.analytics?.brandRevenue || [];
      return {
        value: brands.length > 0 ? (brands[0].name || brands[0].brand || brands[0].brand_name || '—') : '—',
        chartData: brands.map((b: any) => ({ name: b.name || b.brand || b.brand_name, value: b.revenue || b.sales || 0 }))
      };
    }

    if (metric.startsWith('category.')) {
      const categoryName = metric.replace('category.', '');
      let level = params?.level || 'ana';
      if (level === 'primary') level = 'ana';
      const data = await apiClient.getCategoryDetails(dataSourceId, categoryName, level);
      const analysis = data?.data || data;
      return {
        value: analysis?.kpis?.revenue ?? analysis?.summary?.revenue ?? '—',
        chartData: analysis?.top_products?.map((p: any) => ({ name: p.name, value: p.revenue })) || [],
      };
    }

    if (metric.startsWith('brand.')) {
      const brandName = metric.replace('brand.', '');
      const data = await apiClient.getBrandDetail(dataSourceId, { name: brandName });
      const brandData = data?.data || data;
      return {
        value: brandData?.total_sales ?? brandData?.summary?.revenue ?? '—',
        chartData: brandData?.top_products?.map((p: any) => ({ name: p.name, value: p.revenue })) || [
          { name: 'Satışlar', value: brandData?.total_sales || 0 },
          { name: 'Siparişler', value: brandData?.order_count || 0 }
        ],
      };
    }

    if (metric === 'nba' || metric === 'actions' || metric.startsWith('campaign.')) {
      const recParams: any = params || {};
      const recommendations = await apiClient.getCampaignRecommendations(
        recParams.status || 'Bekliyor',
        recParams.type || 'Tümü',
        recParams.category || 'all',
        recParams.kategoriYoneticisi || 'all',
        recParams.brand || 'all',
        recParams.page || 1,
        recParams.limit || 50,
        recParams.sortBy || 'default',
        recParams.sortOrder || 'DESC',
        recParams.minLift || 0,
        recParams.minConfidence || 0,
        recParams.brandBothSides || false
      );
      return {
        value: recommendations?.length || 0,
        chartData: recommendations || []
      };
    }

    if (metric === 'top_customers' || metric === 'churn_risk_list' || metric.startsWith('customers.')) {
        let customers = [];
        let fetchParams: any = { ...params };
        
        if (metric === 'top_customers') {
          fetchParams.sort_by = 'revenue';
          fetchParams.sort_order = 'DESC';
        } else if (metric === 'churn_risk_list') {
          fetchParams.churn_risk = 'high';
        }

        const res = await apiClient.getCustomers(dataSourceId, 1, 10, fetchParams);
        customers = res?.customers || [];
        
        return {
             value: customers.length,
             chartData: customers
         };
     }
  } catch (err) {
    console.error(`DynamicDashboard fetch error for ${metric}:`, err);
    return { value: 'Hata', error: true };
  }
  
  return { value: '—' };
}

const TrendIcon: React.FC<{ trend?: string }> = ({ trend }) => {
  if (trend === 'up') return <ThemeIcon color="green" variant="light" size="sm" radius="xl"><IconTrendingUp size={14} /></ThemeIcon>;
  if (trend === 'down') return <ThemeIcon color="red" variant="light" size="sm" radius="xl"><IconTrendingDown size={14} /></ThemeIcon>;
  return <ThemeIcon color="gray" variant="light" size="sm" radius="xl"><IconMinus size={14} /></ThemeIcon>;
};

const WidgetWrapper: React.FC<{ item: DashboardItem; dataSourceId: string }> = ({ item, dataSourceId }) => {
  const [data, setData] = useState<{ value: any; change?: number; trend?: string; chartData?: any[]; error?: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    fetchMetricValue(item.metric, dataSourceId, item.params).then((res) => {
      if (isMounted) {
        setData(res);
        setLoading(false);
      }
    });
    return () => { isMounted = false; };
  }, [item.metric, dataSourceId, JSON.stringify(item.params)]);

  const manualChartData = useMemo(() => {
    if (!data?.chartData || data.chartData.length === 0) return null;
    return {
      labels: data.chartData.map(r => r.date || r.month || r.ay || r.tarih || r.name || ''),
      values: data.chartData.map(r => r.value || r.sales || r.ciro || r.revenue || 0)
    };
  }, [data?.chartData]);

  if (loading) {
    return (
      <Paper p="md" withBorder radius="md" shadow="xs" style={{ minHeight: 120, background: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Stack gap="xs" align="center">
           <Loader size="sm" color="indigo" />
           <Text size="xs" c="gray.6" fw={600}>Veriler Hazırlanıyor...</Text>
        </Stack>
      </Paper>
    );
  }

  if (data?.error) {
    return (
      <Alert icon={<IconAlertCircle size={16} />} title="Hata" color="red" radius="md" variant="light">
        Veri yüklenirken bir sorun oluştu.
      </Alert>
    );
  }

  if (item.type === 'kpi') {
    return (
      <Paper p="md" withBorder radius="md" shadow="sm" style={{ borderLeft: '4px solid var(--mantine-color-indigo-6)', background: '#ffffff' }}>
        <Stack gap={4}>
          <Text size="xs" c="indigo.8" fw={700} tt="uppercase" lts="0.5px" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {item.title}
          </Text>
          <Group align="center" gap="xs">
            <Text size="xl" fw={900} c="dark.9" style={{ fontFamily: 'Inter, sans-serif', letterSpacing: '-0.5px' }}>
              {(() => {
                const val = data?.value;
                const isCurrency = item.metric?.toLowerCase().includes('revenue') || 
                                  item.metric?.toLowerCase().includes('ciro') || 
                                  item.metric?.toLowerCase().includes('harcama') ||
                                  item.metric?.toLowerCase().includes('clv') ||
                                  item.metric?.toLowerCase().includes('value');
                
                if (typeof val === 'number') {
                  const formatted = val.toLocaleString('tr-TR', { maximumFractionDigits: 0 });
                  return isCurrency ? `₺${formatted}` : formatted;
                }
                return val !== undefined && val !== null ? String(val) : '—';
              })()}
            </Text>
            <TrendIcon trend={data?.trend} />
          </Group>
          {data?.change !== undefined && data.change !== 0 && (
            <Group gap={4}>
               <Text size="xs" fw={700} c={data.change > 0 ? 'green' : 'red'}>
                {data.change > 0 ? '+' : ''}{data.change}%
              </Text>
              <Text size="xs" c="gray.8" fw={500}>önceki döneme göre</Text>
            </Group>
          )}
        </Stack>
      </Paper>
    );
  }

  if (item.type === 'chart') {
    return (
      <Card withBorder radius="md" p="md" shadow="sm">
        <Group justify="space-between" mb="md" wrap="nowrap">
          <Group gap="xs" style={{ overflow: 'hidden', flex: 1 }}>
            <ThemeIcon color="indigo" variant="light" size="md"><IconChartBar size={18} /></ThemeIcon>
            <Text fw={700} size="sm" c="dark.9" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {item.title}
            </Text>
          </Group>
          <Badge variant="light" size="xs" color="indigo" style={{ flexShrink: 0 }}>AI Analiz</Badge>
        </Group>
        
        <div style={{ height: 200 }}>
          {manualChartData ? (
             <Chart 
               type={item.chartType === 'area' ? 'line' : (item.chartType || 'line') as any} 
               manualData={manualChartData} 
               height="100%"
               axisType="category"
             />
          ) : (
             <Center h="100%">
               <Stack align="center" gap="xs">
                  <IconAlertCircle size={32} color="var(--mantine-color-gray-6)" />
                  <Text size="xs" c="gray.8" fw={600}>Grafik verisi yüklenemedi.</Text>
                </Stack>
             </Center>
          )}
        </div>
      </Card>
    );
  }

  if (item.type === 'nba') {
    return (
      <Card withBorder radius="md" p="md" shadow="sm" style={{ borderTop: '4px solid #f59e0b', background: '#fff' }}>
        <Group justify="space-between" mb="xs">
          <Group gap="xs">
            <ThemeIcon color="orange" variant="light" size="md" radius="md"><IconTrendingUp size={18} /></ThemeIcon>
            <Text fw={800} size="sm" c="dark.9" tt="uppercase" lts="0.5px">{item.title}</Text>
          </Group>
          <Badge color="orange" variant="filled" size="xs">AKSIYON</Badge>
        </Group>
        <Stack gap="sm" mt="sm">
          {data?.chartData && data.chartData.length > 0 ? (
            data.chartData.slice(0, 3).map((nba: any, idx: number) => (
              <Paper key={idx} p="xs" withBorder radius="md" bg="#fffbeb" style={{ borderColor: '#fef3c7' }}>
                <Text size="xs" fw={700} c="orange.9">{nba.title || nba.recommendation}</Text>
                <Text size="xs" c="gray.7" mt={2} lineClamp={2}>{nba.offer || nba.reason || nba.description}</Text>
                <Group justify="flex-end" mt={4}>
                   <Badge size="xs" variant="outline" color="orange">{nba.segment || 'Tüm Kitle'}</Badge>
                </Group>
              </Paper>
            ))
          ) : (
            <Center py="sm">
              <Text size="xs" c="dimmed">Şu an öneri bulunmuyor.</Text>
            </Center>
          )}
        </Stack>
      </Card>
    );
  }

  if (item.type === 'table') {
    return (
      <Card withBorder radius="md" p="md" shadow="sm">
        <Group gap="xs" mb="md">
          <ThemeIcon color="indigo" variant="light" size="md"><IconChartBar size={18} /></ThemeIcon>
          <Text fw={800} size="sm" c="dark.9" tt="uppercase" lts="0.5px">{item.title}</Text>
        </Group>
        <Stack gap={4}>
          {data?.chartData && data.chartData.length > 0 ? (
            data.chartData.slice(0, 5).map((row: any, idx: number) => (
              <Group key={idx} justify="space-between" p="xs" style={{ borderBottom: '1px solid #f1f5f9' }}>
                <Stack gap={0}>
                  <Text size="xs" fw={700} c="indigo.9">{row.ad || row.name || `Kayıt #${row.id}`}</Text>
                  <Text size="xs" c="gray.6">{row.segment || row.sehir || row.category || ''}</Text>
                </Stack>
                <Text size="xs" fw={800} c="dark.9">
                    {row.total_sales || row.revenue ? `₺${(row.total_sales || row.revenue).toLocaleString('tr-TR')}` : row.value || ''}
                </Text>
              </Group>
            ))
          ) : (
            <Text size="xs" c="dimmed" ta="center" py="md">Gösterilecek kayıt bulunmuyor.</Text>
          )}
        </Stack>
      </Card>
    );
  }

  return (
    <Paper p="md" withBorder radius="md" shadow="sm" style={{ background: '#ffffff' }}>
      <Text fw={700} size="sm" mb="xs" c="indigo.7" lts="0.3px" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {item.title}
      </Text>
      <Text size="sm" fw={600} c="dark.9">{String(data?.value ?? '—')}</Text>
    </Paper>
  );
};

export const AIPanelRenderer: React.FC<DynamicDashboardProps> = ({ config, dataSourceId }) => {
  const items = useMemo(() => {
    return config?.items || (config as any)?.widgets || [];
  }, [config]);

  if (!items.length) {
    return (
      <Stack align="center" py="xl">
        <Text c="dimmed">Bu panelde henüz widget bulunmuyor.</Text>
      </Stack>
    );
  }

  return (
    <SimpleGrid cols={{ base: 1, md: 2, lg: 3 }} spacing="md">
      {items.map((item: any, idx: number) => (
        <div
          key={idx}
          style={{
            gridColumn: item.width && item.width > 1 ? `span ${Math.min(item.width, 3)}` : undefined,
          }}
        >
          <WidgetWrapper item={item} dataSourceId={dataSourceId} />
        </div>
      ))}
    </SimpleGrid>
  );
};
