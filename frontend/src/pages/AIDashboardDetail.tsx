import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Title, Text, Group, Button, ActionIcon, Stack, Skeleton, SimpleGrid, Alert } from '@mantine/core';
import { IconArrowLeft, IconStar, IconTrash, IconAlertCircle } from '@tabler/icons-react';
import { AIPanelRenderer } from '../components/ai/DynamicDashboard';
import apiClient from '../api/client';
import useDashboardStore from '../stores/dashboardStore';
import { notifications } from '@mantine/notifications';

export default function AIDashboardDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { selectedDataSourceId } = useDashboardStore();

  useEffect(() => {
    if (id) {
      const dashId = parseInt(id);
      if (!isNaN(dashId)) {
        fetchDashboard(dashId);
      } else {
        setLoading(false);
      }
    }
  }, [id]);

  const fetchDashboard = async (dashId: number) => {
    try {
      const data = await apiClient.getAIDashboard(dashId);
      setDashboard(data);
    } catch (err) {
      console.error('Fetch dashboard error:', err);
      notifications.show({ title: 'Hata', message: 'Panel yüklenemedi.', color: 'red' });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!dashboard) return;
    try {
      await apiClient.deleteAIDashboard(dashboard.id);
      notifications.show({ title: 'Silindi', message: 'Panel silindi.' });
      navigate('/ai-paneller');
    } catch (err) {
      notifications.show({ title: 'Hata', message: 'Silme işlemi başarısız.', color: 'red' });
    }
  };

  if (loading) {
    return (
      <Container size="xl" py="md">
        <Skeleton height={40} width="40%" mb="xl" />
        <Skeleton height={200} mb="md" />
        <SimpleGrid cols={3}>
           <Skeleton height={150} />
           <Skeleton height={150} />
           <Skeleton height={150} />
        </SimpleGrid>
      </Container>
    );
  }

  if (!dashboard) {
    return (
      <Container size="sm" py={100}>
        <Alert 
          variant="light" 
          color="gray" 
          title="Panel Bulunamadı" 
          icon={<IconAlertCircle size={24} />}
          radius="md"
        >
          <Stack gap="md">
            <Text size="sm">
              İstediğiniz AI paneli bulunamadı veya silinmiş olabilir. Lütfen tüm paneller listesine dönerek tekrar deneyin.
            </Text>
            <Button 
              variant="outline" 
              color="gray" 
              size="xs" 
              leftSection={<IconArrowLeft size={16} />}
              onClick={() => navigate('/ai-paneller')}
            >
              Panellere Dön
            </Button>
          </Stack>
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" mb="xl">
        <Group>
          <ActionIcon variant="subtle" onClick={() => navigate('/ai-paneller')}>
            <IconArrowLeft size={20} />
          </ActionIcon>
          <Stack gap={0}>
            <Title order={2}>{dashboard.name}</Title>
            <Text size="sm" c="dimmed">{dashboard.description || 'Özel AI Paneli'}</Text>
          </Stack>
        </Group>

        <Group>
          <ActionIcon variant="outline" size="lg" color={dashboard.is_favorite ? 'yellow' : 'gray'}>
             <IconStar size={20} fill={dashboard.is_favorite ? 'currentColor' : 'none'} />
          </ActionIcon>
          <Button variant="outline" color="red" leftSection={<IconTrash size={18} />} onClick={handleDelete}>
            Paneli Sil
          </Button>
        </Group>
      </Group>

      <AIPanelRenderer config={dashboard.config} dataSourceId={selectedDataSourceId || '0'} />
    </Container>
  );
}
