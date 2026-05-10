import { useState, useEffect } from 'react'
import { 
  Container, 
  Tabs, 
  Paper, 
  Title, 
  Group, 
  SimpleGrid, 
  Text, 
  Badge, 
  Select, 
  ActionIcon, 
  Stack,
  Box,
  Button,
  Loader,
  Pagination
} from '@mantine/core'
import { 
  IconChartBar, 
  IconScale, 
  IconAlertCircle,
  IconArrowUp,
  IconArrowDown,
  IconCalendar
} from '@tabler/icons-react'
import { formatMillion } from '../utils/format'
import FilterPanel, { FilterState } from '../components/FilterPanel'
import apiClient from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'
import useDashboardStore from '../stores/dashboardStore'
import { AIInsightCard } from '../components/ai/AIInsightCard'
import { AISummaryButton } from '../components/ai/AISummaryButton'
import { KpiCard, KPI_COLORS } from '../components/common/KpiCard'
import { notifications } from '@mantine/notifications'
import { useChatStore } from '../stores/chatStore'
import CampaignComparison from '../components/campaign/CampaignComparison'
import '../styles/DashboardHome.css'

export default function Campaigns() {
  const { 
      selectedDataSourceId, 
      selectedYear, 
      selectedMonth, 
      selectedStartDate, 
      selectedEndDate,
      selectedCategories,
      selectedBrands,
      selectedCustomerType,
      selectedApprovalStatus,
      selectedRegion,
      availableYears,
      setSelectedYear,
      setSelectedMonth,
      setDateRange
  } = useDashboardStore()

  const [activeTab, setActiveTab] = useState<string | null>('analysis')
  const [initialLoading, setInitialLoading] = useState(false)
  const [filterLoading, setFilterLoading] = useState(false)
  const [campaignData, setCampaignData] = useState<any>(null)
  const [error, setError] = useState<string>('')
  const [isFirstLoad, setIsFirstLoad] = useState(true)
  const [sortBy, setSortBy] = useState<'revenue' | 'conversions' | 'endDate'>('endDate')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  useEffect(() => {
    if (selectedDataSourceId) {
      fetchCampaignData({
           year: selectedYear,
           month: selectedMonth,
           startDate: selectedStartDate,
           endDate: selectedEndDate,
           categories: selectedCategories,
           brands: selectedBrands,
           customerType: selectedCustomerType,
           approvalStatus: selectedApprovalStatus,
           region: selectedRegion
      }, true)
    }
  }, [selectedDataSourceId])

  useEffect(() => {
     if (selectedDataSourceId && !isFirstLoad) {
        setCurrentPage(1)
        fetchCampaignData({
            year: selectedYear,
            month: selectedMonth,
            startDate: selectedStartDate,
            endDate: selectedEndDate,
            categories: selectedCategories,
            brands: selectedBrands,
            customerType: selectedCustomerType,
            approvalStatus: selectedApprovalStatus,
            region: selectedRegion
       }, false)
     }
  }, [selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedCategories, selectedBrands, selectedCustomerType, selectedApprovalStatus, selectedRegion])

  const fetchCampaignData = async (nextFilters: FilterState, treatAsInitial: boolean) => {
    try {
      if (treatAsInitial || (!campaignData && isFirstLoad)) {
        setInitialLoading(true)
      } else {
        setFilterLoading(true)
      }
      setError('')
      
      const params = new URLSearchParams()
      if (nextFilters.year) params.append('year', nextFilters.year.toString())
      if (nextFilters.month) params.append('month', nextFilters.month.toString())
      if (nextFilters.startDate) params.append('start_date', nextFilters.startDate)
      if (nextFilters.endDate) params.append('end_date', nextFilters.endDate)
      if (nextFilters.categories && nextFilters.categories.length > 0) params.append('categories', nextFilters.categories.join(','))
      if (nextFilters.brands && nextFilters.brands.length > 0) params.append('brands', nextFilters.brands.join(','))
      if (nextFilters.customerType) params.append('customer_type', nextFilters.customerType)
      if (nextFilters.approvalStatus) params.append('approval_status', nextFilters.approvalStatus)
      if (nextFilters.region) params.append('region', nextFilters.region)
      
      const queryString = params.toString()
      const url = `/veri-kaynaklari/${selectedDataSourceId}/kampanyalar/${queryString ? '?' + queryString : ''}`
      
      const response = await apiClient.get(url)
      setCampaignData(response.data)
    } catch (err: any) {
      setCampaignData(null)
      const msg = err?.response?.data?.error || err?.message || 'Kampanya verileri alınamadı'
      setError(msg)
      notifications.show({
        title: 'Hata',
        message: msg,
        color: 'red'
      })
    } finally {
      setInitialLoading(false)
      setFilterLoading(false)
      setIsFirstLoad(false)
    }
  }

  // AI için sayfa bağlamını (context) zenginleştir
  useEffect(() => {
    if (campaignData) {
      const { attachPageContext } = useChatStore.getState();
      attachPageContext('Kampanya Analizi', {
        page: 'campaigns',
        data_source_id: selectedDataSourceId,
        performance: campaignData.performanceMetrics,
        channels: campaignData.channelPerformance.length,
        active_campaigns_count: campaignData.activeCampaigns.filter((c: any) => c.status === 'Aktif').length
      });
    }
  }, [campaignData, selectedDataSourceId]);

  if (error) {
    return (
      <Container size="xl" py="xl">
        <Paper p="xl" radius="md" withBorder style={{ textAlign: 'center' }}>
          <IconAlertCircle size={48} color="red" stroke={1.5} />
          <Title order={3} mt="md">Veri alınamadı</Title>
          <Text color="dimmed" mb="xl">{error}</Text>
          <Button
            onClick={() => fetchCampaignData({
               year: selectedYear,
               month: selectedMonth,
               startDate: selectedStartDate,
               endDate: selectedEndDate,
               categories: selectedCategories,
               brands: selectedBrands,
               customerType: selectedCustomerType,
               approvalStatus: selectedApprovalStatus,
               region: selectedRegion
          }, true)}
            color="indigo"
          >
            Yeniden Dene
          </Button>
        </Paper>
      </Container>
    )
  }

  if (!selectedDataSourceId) return <Container py="xl"><Text ta="center">Veri kaynağı seçiniz.</Text></Container>

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" mb="xl">
        <Stack gap={0}>
          <Title order={2} className="premium-gradient-text">Kampanya Yönetimi</Title>
          <Text c="dimmed" size="sm">Kampanya performansı ve karşılaştırmalı analizler</Text>
        </Stack>
        {campaignData && (
          <AISummaryButton 
            contextType="campaigns_overview" 
            contextId={selectedDataSourceId?.toString()} 
          />
        )}
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab} variant="outline" radius="md">
        <Tabs.List mb="md">
          <Tabs.Tab value="analysis" leftSection={<IconChartBar size={16} />}>Genel Analiz</Tabs.Tab>
          <Tabs.Tab value="comparison" leftSection={<IconScale size={16} />}>Kampanya Karşılaştırma</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="analysis">
          <LoadingOverlay loading={initialLoading || filterLoading}>
            {!campaignData ? (
              <Box h={300} display="flex" style={{ alignItems: 'center', justifyContent: 'center' }}>
                <Loader size="lg" />
              </Box>
            ) : (
              <Stack gap="xl">
                {/* AI Insights Card */}
                <AIInsightCard 
                  contextType="campaigns_overview" 
                  contextId={selectedDataSourceId?.toString()} 
                  title="Kampanya Performans Özeti ve AI Gözlemleri"
                  data={campaignData}
                />

                {/* Performans Özeti */}
                <SimpleGrid cols={{ base: 1, xs: 1, md: 2, lg: 5 }} spacing="md">
                  <KpiCard {...KPI_COLORS.indigo} label="Toplam Kampanya" value={String(campaignData.performanceMetrics.totalCampaigns)} />
                  <KpiCard {...KPI_COLORS.green} label="Aktif Kampanya" value={String(campaignData.performanceMetrics.activeCampaigns)} />
                  <KpiCard {...KPI_COLORS.amber} label="Ort. Dönüşüm" value={`%${campaignData.performanceMetrics.avgConversionRate}`} />
                  <KpiCard {...KPI_COLORS.blue} label="Ort. ROI" value={`${campaignData.performanceMetrics.avgROI}x`} />
                  <KpiCard {...KPI_COLORS.pink} label="Toplam Gelir" value={`₺${formatMillion(campaignData.performanceMetrics.totalRevenue)}`} />
                </SimpleGrid>

                {/* Kampanya Listesi */}
                <Paper p="xl" radius="md" withBorder shadow="sm">
                  <Group justify="space-between" mb="xl">
                    <Title order={4}>Kampanyalar</Title>
                    <Group>
                      <Select
                        size="xs"
                        placeholder="Sırala"
                        data={[
                          { value: 'revenue', label: 'Ciro' },
                          { value: 'conversions', label: 'Dönüşüm' },
                          { value: 'endDate', label: 'Bitiş Tarihi' },
                        ]}
                        value={sortBy}
                        onChange={(val: any) => setSortBy(val)}
                      />
                      <ActionIcon 
                        variant="light" 
                        color="indigo" 
                        onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                      >
                        {sortOrder === 'asc' ? <IconArrowUp size={18} /> : <IconArrowDown size={18} />}
                      </ActionIcon>
                    </Group>
                  </Group>

                  <Stack gap="lg">
                    {/* Aktif Kampanyalar */}
                    <Box>
                      <Group mb="md">
                        <Badge color="green" variant="dot" size="lg">Aktif Kampanyalar</Badge>
                      </Group>
                      <Stack gap="md">
                        {campaignData?.activeCampaigns
                          .filter((c: any) => c.status === 'Aktif')
                          .sort((a: any, b: any) => {
                            const valA = a[sortBy];
                            const valB = b[sortBy];
                            if (sortBy === 'endDate') return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
                            return sortOrder === 'asc' ? valA - valB : valB - valA;
                          })
                          .slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
                          .map((campaign: any) => renderCampaignCard(campaign))
                        }
                        {campaignData?.activeCampaigns.filter((c: any) => c.status === 'Aktif').length === 0 && (
                          <Text c="dimmed" ta="center" py="xl">Aktif kampanya bulunamadı.</Text>
                        )}
                      </Stack>
                    </Box>

                    {/* Geçmiş Kampanyalar */}
                    <Box mt="xl">
                      <Group mb="md">
                        <Badge color="gray" variant="dot" size="lg">Geçmiş Kampanyalar</Badge>
                      </Group>
                      <Stack gap="md">
                        {campaignData?.activeCampaigns
                          .filter((c: any) => c.status === 'Geçmiş')
                          .sort((a: any, b: any) => {
                            const valA = a[sortBy];
                            const valB = b[sortBy];
                            if (sortBy === 'endDate') return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
                            return sortOrder === 'asc' ? valA - valB : valB - valA;
                          })
                          .slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
                          .map((campaign: any) => renderCampaignCard(campaign))
                        }
                      </Stack>
                    </Box>

                    <Group justify="center" mt="xl">
                      <Pagination 
                        total={Math.ceil((campaignData?.activeCampaigns.length || 0) / itemsPerPage)} 
                        value={currentPage} 
                        onChange={setCurrentPage} 
                        color="indigo" 
                      />
                    </Group>
                  </Stack>
                </Paper>
              </Stack>
            )}
          </LoadingOverlay>
        </Tabs.Panel>

        <Tabs.Panel value="comparison">
          {campaignData ? (
            <CampaignComparison campaigns={campaignData.activeCampaigns} />
          ) : (
            <Text ta="center" py="xl">Kampanya verileri yükleniyor...</Text>
          )}
        </Tabs.Panel>
      </Tabs>
    </Container>
  )

  function formatDate(dateStr: string) {
    if (!dateStr) return '';
    try {
      const parts = dateStr.split('-');
      if (parts.length !== 3) return dateStr;
      return `${parts[2]}.${parts[1]}.${parts[0]}`;
    } catch (e) {
      return dateStr;
    }
  }

  function renderCampaignCard(campaign: any) {
    return (
      <Paper 
        key={campaign.id} 
        p="md" 
        radius="md" 
        withBorder 
        className="premium-hover-card"
        style={(theme: any) => ({
          backgroundColor: campaign.status === 'Geçmiş' ? theme.colors.gray[0] : `${campaign.color}15`, // slightly more opacity
          borderLeft: `4px solid ${campaign.status === 'Geçmiş' ? theme.colors.gray[4] : campaign.color}`,
        })}
      >
        <Group justify="space-between" mb="md">
          <Box>
            <Title order={5}>{campaign.name}</Title>
            <Group gap="xs" mt={4}>
              <IconCalendar size={14} color="gray" />
              <Text size="xs" c="dimmed">{formatDate(campaign.startDate)} - {formatDate(campaign.endDate)}</Text>
            </Group>
          </Box>
          <Badge color={campaign.status === 'Geçmiş' ? 'gray' : 'green'} variant="filled">
            {campaign.status}
          </Badge>
        </Group>

        <SimpleGrid cols={{ base: 2, xs: 2, md: 4 }} spacing="md">
          <Box>
            <Text size="xs" c="dimmed">Hedef / Ulaşılan</Text>
            <Text fw={700} size="sm">{campaign.reached} / {campaign.targetCustomers}</Text>
          </Box>
          <Box>
            <Text size="xs" c="dimmed">Dönüşüm</Text>
            <Text fw={700} size="sm" c="teal">{campaign.conversions}</Text>
          </Box>
          <Box>
            <Text size="xs" c="dimmed">Gelir</Text>
            <Text fw={700} size="sm">₺{campaign.revenue.toLocaleString()}</Text>
          </Box>
          <Box>
            <Text size="xs" c="dimmed">ROI</Text>
            <Text fw={700} size="sm" c="orange">{campaign.roi}x</Text>
          </Box>
        </SimpleGrid>
      </Paper>
    )
  }
}
