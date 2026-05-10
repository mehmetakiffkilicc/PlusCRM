import React, { useEffect, useState } from 'react';
import { Title, Text, Stack, SimpleGrid, Card, Group, Badge, ActionIcon, Button, Loader, Container } from '@mantine/core';
import { IconLayoutDashboard, IconStar, IconTrash, IconSparkles } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { notifications } from '@mantine/notifications';
import useUIStore from '../stores/uiStore';

export default function AIDashboards() {
  const [dashboards, setDashboards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboards();
  }, []);

  const fetchDashboards = async () => {
    try {
      const data = await apiClient.getAIDashboards();
      setDashboards(data);
    } catch (err) {
      console.error('Dashboards load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.deleteAIDashboard(id);
      setDashboards(dashboards.filter(d => d.id !== id));
      notifications.show({ title: 'Silindi', message: 'Panel başarıyla silindi.', color: 'gray' });
    } catch (err) {
      notifications.show({ title: 'Hata', message: 'Silme işlemi başarısız.', color: 'red' });
    }
  };

  const handleFavorite = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await apiClient.toggleAIDashboardFavorite(id);
      setDashboards(dashboards.map(d => d.id === id ? { ...d, is_favorite: res.data.is_favorite } : d));
    } catch (err) {
      console.error('Toggle favorite error:', err);
    }
  };

  if (loading) return <Loader p={50} />;

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" mb="xl">
        <Stack gap={0}>
          <Title order={2}>Özel AI Panelleri</Title>
          <Text c="dimmed" size="sm">Yapay zeka tarafından sizin için özel olarak oluşturulan dashboardlar.</Text>
        </Stack>
         <Button 
           leftSection={<IconSparkles size={18} />} 
           variant="gradient" 
           gradient={{ from: 'indigo', to: 'grape' }}
           onClick={() => useUIStore.getState().setChatOpened(true)}
         >
           Yeni Panel Oluştur
         </Button>
      </Group>

      {dashboards.length === 0 ? (
        <Card withBorder p={50} radius="lg" style={{ textAlign: 'center', background: '#f8fafc' }}>
          <IconLayoutDashboard size={48} color="gray" style={{ margin: '0 auto' }} />
          <Text fw={800} mt="md" size="lg">Henüz Özel Paneliniz Yok</Text>
           <Text size="sm" c="dimmed" mb="xl" maw={400} mx="auto">
             Sol üstteki AI Widget'ını kullanarak işletmeniz için özel bir veri paneli hazırlamasını isteyebilirsiniz.
           </Text>
           <Button variant="gradient" gradient={{ from: 'indigo', to: 'violet' }} onClick={() => useUIStore.getState().setChatOpened(true)}>
             AI Zeka Asistanı
           </Button>
        </Card>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="xl">
          {dashboards.map((dash) => (
            <Card 
              key={dash.id} 
              withBorder 
              radius="lg" 
              p="lg" 
              onClick={() => navigate(`/ai-paneller/${dash.id}`)}
              style={{ 
                cursor: 'pointer',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                border: '1px solid #e2e8f0',
                background: '#ffffff'
              }}
              className="dashboard-card"
            >
              <Group justify="space-between" mb="sm">
                <Badge 
                  variant="gradient" 
                  gradient={{ from: 'indigo', to: 'grape' }} 
                  size="sm" 
                  radius="md"
                  leftSection={<IconSparkles size={12} />}
                  style={{ textTransform: 'none', fontWeight: 800 }}
                >
                  AI Özel
                </Badge>
                <Group gap={4}>
                  <ActionIcon 
                    variant="subtle" 
                    color={dash.is_favorite ? 'yellow' : 'gray'}
                    onClick={(e) => handleFavorite(dash.id, e)}
                  >
                    <IconStar size={18} fill={dash.is_favorite ? 'currentColor' : 'none'} />
                  </ActionIcon>
                  <ActionIcon variant="subtle" color="red" onClick={(e) => handleDelete(dash.id, e)}>
                    <IconTrash size={18} />
                  </ActionIcon>
                </Group>
              </Group>

              <Text fw={800} size="lg" mb={4} c="dark.9">{dash.name}</Text>
              <Text size="sm" c="dimmed" lineClamp={2} mb="xl" style={{ height: 40, lineHeight: 1.5 }}>
                {dash.description || 'Bu stratejik panel yapay zeka tarafından verileriniz analiz edilerek oluşturulmuştur.'}
              </Text>

              <Group justify="space-between" align="center" mt="auto">
                  <Stack gap={0}>
                    <Text size="10px" c="dimmed" fw={700} tt="uppercase">Oluşturulma</Text>
                    <Text size="xs" fw={700}>
                        {new Date(dash.created_at).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' })}
                    </Text>
                  </Stack>
                  <Button variant="light" color="indigo" size="xs" radius="md">Paneli Aç</Button>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Container>
  );
}
