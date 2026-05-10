import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Container, Grid, Card, Text, Title, Group, 
  Stack, LoadingOverlay, Paper, Badge, Button,
  ActionIcon, Tooltip, ThemeIcon, Loader
} from '@mantine/core';
import { 
  IconSparkles, IconDeviceAnalytics, IconArrowLeft, 
  IconTrash, IconStar, IconStarFilled, IconDownload
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AIPanelRenderer } from '../components/ai/DynamicDashboard';

// API Base
const BASE_URL = import.meta.env.VITE_API_URL || '/api';

interface WidgetConfig {
  type: 'kpi' | 'trend' | 'rfm' | 'churn';
  title: string;
  source: string; // endpoint
  params?: any;
}

interface AIDashboardData {
  id: number;
  name: string;
  description: string;
  config: {
    widgets?: WidgetConfig[];
    items?: any[];
  };
  is_favorite: boolean;
  created_at: string;
}

export default function DynamicDashboard() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<AIDashboardData | null>(null);
  const [isFav, setIsFav] = useState(false);

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('auth_token');
        const res = await axios.get(`${BASE_URL}/ai/paneller/${id}/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setDashboard(res.data);
        setIsFav(res.data.is_favorite);
      } catch (error) {
        console.error("Dashboard yüklenemedi:", error);
      } finally {
        setLoading(false);
      }
    };

    if (id) fetchDashboard();
  }, [id]);

  const toggleFavorite = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      await axios.post(`${BASE_URL}/ai/paneller/${id}/favori/`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsFav(!isFav);
    } catch (err) {
      console.error("Favori işlemi başarısız");
    }
  };

  if (loading) return <LoadingOverlay visible />;
  if (!dashboard) return <Container py={100}><Title order={2} ta="center">Panel Bulunamadı</Title></Container>;

  return (
    <div className="page-content">
      <Stack gap="xl">
        {/* Header Section */}
        <Paper p="lg" radius="lg" withBorder>
          <Group justify="space-between">
            <Stack gap={4}>
              <Group gap="xs">
                <ActionIcon variant="subtle" color="gray" onClick={() => navigate(-1)}>
                  <IconArrowLeft size={20} />
                </ActionIcon>
                <IconSparkles size={24} color="#6366f1" />
                <Title order={2} fw={800}>{dashboard.name}</Title>
                <Badge variant="light" color="indigo">AI Oluşturdu</Badge>
              </Group>
              <Text size="sm" c="dimmed" ml={34}>{dashboard.description}</Text>
            </Stack>
            <Group>
              <Tooltip label={isFav ? "Favorilerden Çıkar" : "Favoriye Ekle"}>
                <ActionIcon 
                  variant="subtle" 
                  color={isFav ? "yellow" : "gray"} 
                  onClick={toggleFavorite}
                  size="lg"
                >
                  {isFav ? <IconStarFilled size={24} /> : <IconStar size={24} />}
                </ActionIcon>
              </Tooltip>
              <Button leftSection={<IconDownload size={16} />} variant="light">Dışa Aktar</Button>
            </Group>
          </Group>
        </Paper>

        {/* Real AI Dashboard Renderer */}
        <AIPanelRenderer 
          config={dashboard.config as any} 
          dataSourceId="0" 
        />
      </Stack>
    </div>
  );
}


