import { Paper, Group, Text, Loader, ThemeIcon, Stack } from '@mantine/core';
import { IconSettings, IconCheck, IconAlertCircle } from '@tabler/icons-react';

interface ToolCallBadgeProps {
  name: string;
  status: 'start' | 'running' | 'result';
  result?: any;
}

export const ToolCallBadge: React.FC<ToolCallBadgeProps> = ({ name, status, result }) => {
  const getLabel = (n: string) => {
    switch (n) {
      case 'get_rfm_summary': return 'RFM Analizi Yapılıyor';
      case 'get_customer_profile': return 'Müşteri Profili İnceleniyor';
      case 'schedule_campaign': return 'Kampanya Planlanıyor';
      case 'list_segment_customers': return 'Segment Üyeleri Listeleniyor';
      case 'search_products': return 'Ürün Araması Yapılıyor';
      default: return `İşlem: ${n}`;
    }
  };

  const isError = result?.status === 'error' || result?.error;

  return (
    <Paper withBorder p="xs" radius="md" style={{ background: '#f8fafc', borderColor: '#e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
      <Group gap="xs">
        <ThemeIcon 
          variant="light" 
          color={isError ? 'red' : status === 'result' ? 'teal' : 'indigo'} 
          size="sm"
        >
          {status === 'result' ? (
            isError ? <IconAlertCircle size={14} /> : <IconCheck size={14} />
          ) : (
            <IconSettings size={14} style={{ animation: 'spin 2s linear infinite' }} />
          )}
        </ThemeIcon>
        
        <Stack gap={0} style={{ flex: 1 }}>
          <Text size="xs" fw={800} c="dark.9">{getLabel(name)}</Text>
          {status === 'result' ? (
            <Text size="xs" c={isError ? 'red' : 'teal'} fw={700}>
              {isError ? 'Hata oluştu' : 'Tamamlandı'}
            </Text>
          ) : (
            <Group gap={4}>
              <Loader size={12} color="indigo" type="bars" />
              <Text size="xs" fw={600} c="indigo.9">Asistan verileri topluyor ve analiz ediyor...</Text>
            </Group>
          )}
        </Stack>
      </Group>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Paper>
  );
};
