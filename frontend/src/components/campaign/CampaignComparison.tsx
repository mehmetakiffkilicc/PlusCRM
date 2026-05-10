import React, { useState, useEffect } from 'react';
import { 
  Box, 
  SimpleGrid, 
  Paper, 
  Text, 
  Title, 
  Checkbox, 
  Table, 
  Group, 
  Badge, 
  ThemeIcon,
  Progress,
  ScrollArea,
  Button,
  Stack
} from '@mantine/core';
import { 
  IconTrendingUp, 
  IconScale
} from '@tabler/icons-react';

interface CampaignComparisonProps {
  campaigns: any[];
}

const CampaignComparison: React.FC<CampaignComparisonProps> = ({ campaigns }) => {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [comparisonData, setComparisonData] = useState<any[]>([]);

  useEffect(() => {
    // Sadece seçili kampanyaları filtrele
    const filtered = campaigns.filter(c => selectedIds.includes(c.id));
    setComparisonData(filtered);
  }, [selectedIds, campaigns]);

  const toggleSelection = (id: number) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const clearSelection = () => setSelectedIds([]);

  const maxRevenue = Math.max(...comparisonData.map(c => c.revenue || 0), 1);
  const maxConversions = Math.max(...comparisonData.map(c => c.conversions || 0), 1);
  const maxCustomers = Math.max(...comparisonData.map(c => c.customerCount || c.targetCustomers || 0), 1);
  const maxReceipts = Math.max(...comparisonData.map(c => c.receiptCount || 0), 1);

  return (
    <Stack gap="xl">
      <Paper p="md" radius="md" withBorder>
        <Group justify="space-between" mb="md">
          <Title order={4} c="indigo">Kampanya Seçimi</Title>
          <Group>
            <Text size="sm" c="dimmed">{selectedIds.length} kampanya seçildi</Text>
            {selectedIds.length > 0 && (
              <Button variant="subtle" color="red" size="xs" onClick={clearSelection}>Temizle</Button>
            )}
          </Group>
        </Group>
        
        <ScrollArea h={200}>
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            {campaigns.map(c => (
              <Checkbox
                key={c.id}
                label={c.name}
                checked={selectedIds.includes(c.id)}
                onChange={() => toggleSelection(c.id)}
                styles={{ body: { alignItems: 'center' } }}
              />
            ))}
          </SimpleGrid>
        </ScrollArea>
      </Paper>

      {comparisonData.length > 0 ? (
        <Stack gap="lg">
          <Title order={4}>Performans Karşılaştırması</Title>
          
          <SimpleGrid cols={1} verticalSpacing="lg">
            {comparisonData.map(c => (
              <Paper key={c.id} p="lg" radius="md" withBorder shadow="sm">
                <Group justify="space-between" mb="md">
                  <Group>
                    <ThemeIcon size="xl" radius="md" variant="light" color={c.color || 'blue'}>
                      <IconScale size={24} />
                    </ThemeIcon>
                    <Box>
                      <Text fw={700} size="lg">{c.name}</Text>
                      <Badge size="xs" color={c.status === 'Aktif' ? 'green' : 'gray'}>{c.status}</Badge>
                    </Box>
                  </Group>
                  <Box ta="right">
                    <Text size="xl" fw={800} c="indigo">₺{c.revenue?.toLocaleString()}</Text>
                    <Text size="xs" c="dimmed">Toplam Gelir</Text>
                  </Box>
                </Group>

                <SimpleGrid cols={2} mb="md">
                  <Box>
                    <Group justify="space-between" mb={5}>
                      <Text size="xs" fw={700}>Ciro Payı (Seçili İçinde)</Text>
                      <Text size="xs" fw={700}>{((c.revenue / maxRevenue) * 100).toFixed(1)}%</Text>
                    </Group>
                    <Progress value={(c.revenue / maxRevenue) * 100} color="indigo" size="sm" radius="xl" />
                  </Box>
                  <Box>
                    <Group justify="space-between" mb={5}>
                      <Text size="xs" fw={700}>Dönüşüm Payı</Text>
                      <Text size="xs" fw={700}>{((c.conversions / maxConversions) * 100).toFixed(1)}%</Text>
                    </Group>
                    <Progress value={(c.conversions / maxConversions) * 100} color="teal" size="sm" radius="xl" />
                  </Box>
                </SimpleGrid>
 
                 <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
                   <Box>
                     <Text size="xs" c="dimmed">Müşteri Sayısı</Text>
                     <Text fw={700} c="blue">{c.customerCount || c.targetCustomers || 'N/A'}</Text>
                   </Box>
                   <Box>
                     <Text size="xs" c="dimmed">Fiş Sayısı</Text>
                     <Text fw={700} c="cyan">{c.receiptCount || 'N/A'}</Text>
                   </Box>
                   <Box>
                     <Text size="xs" c="dimmed">Ort. Sepet (₺)</Text>
                     <Text fw={700} c="green">{c.avgBasket || (c.revenue && c.receiptCount ? (c.revenue / c.receiptCount).toFixed(0) : 'N/A')}</Text>
                   </Box>
                   <Box>
                     <Text size="xs" c="dimmed">ROI</Text>
                     <Text fw={700} c="orange">{c.roi}x</Text>
                   </Box>
                 </SimpleGrid>
              </Paper>
            ))}
          </SimpleGrid>

          <Paper p="md" radius="md" withBorder shadow="sm">
            <Title order={5} mb="md">Karşılaştırmalı Tablo</Title>
            <ScrollArea>
               <Table verticalSpacing="sm">
                 <thead>
                   <tr>
                     <th>Kampanya</th>
                     <th>Gelir (₺)</th>
                     <th>Müşteri</th>
                     <th>Fiş Sayısı</th>
                     <th>Ort. Sepet</th>
                     <th>Öncesi/Şimdi</th>
                     <th>ROI</th>
                     <th>Başarı</th>
                   </tr>
                 </thead>
                 <tbody>
                   {comparisonData.sort((a,b) => b.revenue - a.revenue).map(c => (
                     <tr key={c.id}>
                       <td>{c.name}</td>
                       <td>{c.revenue?.toLocaleString()}</td>
                       <td>{c.customerCount || 'N/A'}</td>
                       <td>{c.receiptCount?.toLocaleString() || 'N/A'}</td>
                       <td>
                         {c.avgBasket 
                           ? `₺${Number(c.avgBasket).toFixed(0)}` 
                           : (c.revenue && c.receiptCount ? `₺${(c.revenue / c.receiptCount).toFixed(0)}` : 'N/A')}
                       </td>
                       <td>
                         {c.beforeSales && c.afterSales ? (
                           <Group gap={4}>
                             <Text size="xs" c="dimmed" td="line-through">₺{c.beforeSales?.toLocaleString()}</Text>
                             <IconTrendingUp size={14} color="green" />
                             <Text size="xs" fw={600} c="green">₺{c.afterSales?.toLocaleString()}</Text>
                           </Group>
                         ) : 'N/A'}
                       </td>
                       <td>{c.roi}x</td>
                       <td>
                         <Badge color={c.roi > 5 ? 'green' : c.roi > 3 ? 'blue' : 'gray'}>
                           {c.roi > 5 ? 'Mükemmel' : c.roi > 3 ? 'İyi' : 'Normal'}
                         </Badge>
                       </td>
                     </tr>
                   ))}
                 </tbody>
               </Table>
            </ScrollArea>
          </Paper>
        </Stack>
      ) : (
        <Paper p={50} radius="md" withBorder style={{ textAlign: 'center', borderStyle: 'dashed' }}>
          <Stack align="center" gap="xs">
            <ThemeIcon size={60} radius="xl" variant="light" color="gray">
              <IconScale size={34} />
            </ThemeIcon>
            <Text fw={600}>Kampanya Seçilmedi</Text>
            <Text size="sm" c="dimmed">Karşılaştırma yapmak için yukarıdaki listeden en az iki kampanya seçin.</Text>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
};

export default CampaignComparison;
