import React, { useState, useEffect } from 'react';

function cleanAIText(text: string): string {
  return text
    .replace(/<tool_code>[\s\S]*?<\/tool_code>/gi, '')
    .replace(/<tool_output>[\s\S]*?<\/tool_output>/gi, '')
    .replace(/<\/?tool_code>/gi, '')
    .replace(/<\/?tool_output>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
import { Card, Text, Group, Button, Loader, Alert, Badge } from '@mantine/core';
import { IconSparkles, IconRefresh, IconAlertCircle } from '@tabler/icons-react';
import { aiClient } from '../../api/aiClient';

interface AIInsightCardProps {
  contextType?: string;
  contextId?: string;
  dataSourceId?: string | number;
  title?: string;
  /** Opsiyonel: dışarıdan direkt text geçilirse API çağrısı yapılmaz */
  staticText?: string;
  /** Opsiyonel: Dışarıdan gelen gerçek veri (KPI, tablo verisi vb.) */
  data?: any;
}

export const AIInsightCard = ({
  contextType,
  contextId,
  dataSourceId,
  title = 'AI Yorumu',
  staticText,
  data,
}: AIInsightCardProps) => {
  const [summary, setSummary] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    setSummary('');

    try {
      const contextSummary = data ? (typeof data === 'string' ? data : JSON.stringify(data)) : `context_type: ${contextType || 'general'}, context_id: ${contextId || 'none'}`;
      
      const payload: any = {
        text: contextSummary,
        context_type: contextType,
        context_id: contextId,
        data_source_id: dataSourceId || contextId,
      };
      
      aiClient.streamQuickSummary(
        payload,
        (token) => {
          setSummary(prev => prev + token);
        },
        (err) => {
          setError(err.message || 'AI yorumu alınamadı.');
          setLoading(false);
        },
        () => {
          setLoading(false);
        }
      );
    } catch (err: any) {
      setError('Bağlantı hatası oluştu.');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (staticText) {
      setSummary(staticText);
    }
    // İlk yüklemede otomatik çekmiyoruz — kullanıcı "Yükle" butonuna basacak
  }, [staticText]);

  return (
    <Card
      shadow="sm"
      p="md"
      radius="md"
      withBorder
      style={{
        background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.03) 0%, rgba(124, 58, 237, 0.03) 100%)',
        border: '1px solid rgba(79, 70, 229, 0.15)',
      }}
    >
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <IconSparkles size={16} color="#4f46e5" />
          <Text fw={800} size="sm" c="indigo.7">{title}</Text>
          <Badge size="xs" color="indigo" variant="light">AI</Badge>
        </Group>

        <Button
          size="xs"
          variant="light"
          color="indigo"
          leftSection={loading ? <Loader size={10} color="indigo" /> : <IconRefresh size={12} />}
          onClick={fetchSummary}
          disabled={loading}
          fw={700}
        >
          {loading ? 'Yükleniyor...' : summary ? 'Yenile' : 'Yükle'}
        </Button>
      </Group>

      {error && (
        <Alert icon={<IconAlertCircle size={14} />} color="orange" variant="light" p="xs" radius="md">
          <Text size="xs" fw={500}>{error}</Text>
        </Alert>
      )}

      {!error && summary && (
        <Text size="sm" c="dark.8" style={{ lineHeight: 1.8, whiteSpace: 'pre-wrap', fontWeight: 500 }}>
          {cleanAIText(summary)}
        </Text>
      )}

      {!error && !summary && !loading && (
        <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
          Bu bölüm için AI yorumu almak üzere "Yükle" butonuna tıklayın.
        </Text>
      )}
    </Card>
  );
};
