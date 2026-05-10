import React, { useState, useEffect } from 'react';
import { Card, Text, Group, Button, Loader, Alert, Badge, Stack, ThemeIcon, ScrollArea, Divider, Title, Center } from '@mantine/core';
import { IconSparkles, IconRefresh, IconAlertCircle, IconBook, IconBrain, IconTarget } from '@tabler/icons-react';
import apiClient from '../../api/client';

function cleanAIText(text: string): string {
  return text
    .replace(/<tool_code>[\s\S]*?<\/tool_code>/gi, '')
    .replace(/<tool_output>[\s\S]*?<\/tool_output>/gi, '')
    .replace(/<\/?tool_code>/gi, '')
    .replace(/<\/?tool_output>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

interface CustomerNarrativeSectionProps {
  customerId: string;
  dataSourceId: string;
}

export const CustomerNarrativeSection = ({
  customerId,
  dataSourceId,
}: CustomerNarrativeSectionProps) => {
  const [narrative, setNarrative] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNarrative = async () => {
    setLoading(true);
    setError(null);

    try {
      // Backend tools.py içindeki get_customer_narrative aracını tetiklemek için
      // context_type="customer_narratology" kullanıyoruz.
      const payload = {
        text: `Müşteri ID: ${customerId} için narratoloji (hikaye) analizi yap. get_customer_narrative aracını kullan.`,
        context_type: 'customer_narratology',
        context_id: customerId,
        data_source_id: dataSourceId,
      };
      
      const res = await apiClient.post('/ai/ozet/', payload);
      setNarrative(res.data.summary || 'Hikaye oluşturulamadı.');
    } catch (err: any) {
      const status = err?.response?.status;
      const serverMsg = err?.response?.data?.error;
      let msg: string;
      if (status === 503) {
        msg = serverMsg || 'AI servisi yoğun. Lütfen tekrar deneyin.';
      } else if (status === 429) {
        msg = 'Günlük AI limitine ulaşıldı.';
      } else {
        msg = serverMsg || 'Analiz sırasında bir hata oluştu.';
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      shadow="md"
      p="xl"
      radius="lg"
      withBorder
      style={{
        background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%)',
        border: '1px solid rgba(79, 70, 229, 0.2)',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Dekoratif Ikon */}
      <div style={{ position: 'absolute', right: -20, top: -20, opacity: 0.05 }}>
        <IconBrain size={120} />
      </div>

      <Group justify="space-between" mb="lg">
        <Stack gap={0}>
          <Group gap="xs">
            <ThemeIcon variant="light" color="indigo" radius="md" size="lg">
              <IconBook size={20} />
            </ThemeIcon>
            <Title order={4} style={{ color: 'var(--mantine-color-indigo-7)' }}>Müşteri Hikayesi & Stratejik Narratoloji</Title>
            <Badge color="indigo" variant="filled" size="sm" leftSection={<IconSparkles size={10} />}>
              AI MASTER
            </Badge>
          </Group>
          <Text size="xs" c="dimmed" mt={4}>Davranışsal geçmişten türetilen derin psikolojik profil ve satın alma yolculuğu.</Text>
        </Stack>

        <Button
          variant="gradient"
          gradient={{ from: 'indigo', to: 'violet' }}
          leftSection={loading ? <Loader size={14} color="white" /> : <IconRefresh size={16} />}
          onClick={fetchNarrative}
          disabled={loading}
          radius="md"
        >
          {loading ? 'Analiz Ediliyor...' : narrative ? 'Analizi Yenile' : 'Hikayeyi Oluştur'}
        </Button>
      </Group>

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" variant="light" mb="md" radius="md">
          {error}
        </Alert>
      )}

      {!narrative && !loading && !error && (
        <Center py="xl">
          <Stack align="center" gap="sm">
            <ThemeIcon size={50} radius="xl" variant="light" color="gray">
              <IconTarget size={30} />
            </ThemeIcon>
            <Text c="dimmed" size="sm" fs="italic">Bu müşterinin satın alma motivasyonlarını ve sadakat sırlarını keşfetmek için butona tıklayın.</Text>
          </Stack>
        </Center>
      )}

      {narrative && (
        <ScrollArea.Autosize mah={400} type="hover">
          <Stack gap="md">
            <Divider label="AI Analiz Sonucu" labelPosition="center" />
            <Text 
              size="sm" 
              style={{ 
                lineHeight: 1.8, 
                whiteSpace: 'pre-wrap', 
                color: 'var(--mantine-color-dark-8)',
                fontWeight: 500
              }}
            >
              {cleanAIText(narrative)}
            </Text>
          </Stack>
        </ScrollArea.Autosize>
      )}
    </Card>
  );
};
