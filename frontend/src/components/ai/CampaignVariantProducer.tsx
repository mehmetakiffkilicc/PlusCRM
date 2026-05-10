import React, { useState } from 'react';
import { Modal, Button, Text, Group, Stack, Card, Badge, ActionIcon, Tooltip, LoadingOverlay, Tabs, Textarea } from '@mantine/core';
import { IconCopy, IconCheck, IconSparkles, IconMessage, IconMail, IconBell, IconRefresh } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { aiClient } from '../../api/aiClient';

interface CampaignVariantProducerProps {
  opened: boolean;
  onClose: () => void;
  campaignDetail: any;
}

export const CampaignVariantProducer: React.FC<CampaignVariantProducerProps> = ({ opened, onClose, campaignDetail }) => {
  const [loading, setLoading] = useState(false);
  const [variants, setVariants] = useState<{ sms: string[]; email: string[]; push: string[] } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const generateVariants = async () => {
    setLoading(true);
    try {
      const response = await aiClient.generateCampaignVariants(campaignDetail);
      if (response && response.variants) {
        setVariants(response.variants);
      } else if (response && response.error) {
        notifications.show({
          title: 'Varyant Üretilemedi',
          message: response.error,
          color: 'red'
        });
      }
    } catch (error: any) {
      console.error("Varyant üretimi başarısız:", error);
      notifications.show({
        title: 'Sistem Hatası',
        message: error.message || 'AI servislerine erişilemedi. Lütfen internet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconSparkles size={20} color="#6366f1" />
          <Text fw={700}>AI Kampanya Varyant Üretici</Text>
        </Group>
      }
      size="xl"
      radius="md"
    >
      <LoadingOverlay visible={loading} overlayProps={{ blur: 2 }} />
      
      {!variants ? (
        <Stack align="center" py="xl">
          <IconSparkles size={48} color="#e0e7ff" />
          <Text c="dimmed" ta="center">
            Kampanyanız için yapay zeka tarafından optimize edilmiş mesaj varyantları oluşturun.
          </Text>
          <Button 
            leftSection={<IconSparkles size={18} />}
            onClick={generateVariants}
            variant="gradient"
            gradient={{ from: 'indigo', to: 'cyan' }}
          >
            Varyantları Oluştur
          </Button>
        </Stack>
      ) : (
        <Tabs defaultValue="sms" color="indigo">
          <Tabs.List grow>
            <Tabs.Tab value="sms" leftSection={<IconMessage size={16} />}>SMS</Tabs.Tab>
            <Tabs.Tab value="email" leftSection={<IconMail size={16} />}>Email</Tabs.Tab>
            <Tabs.Tab value="push" leftSection={<IconBell size={16} />}>Push</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="sms" pt="md">
            <Stack gap="sm">
              {(variants?.sms || []).map((text, i) => (
                <Card key={i} withBorder padding="md" radius="md">
                  <Group justify="space-between" mb="xs">
                    <Badge variant="light" color="blue">Varyant {i + 1}</Badge>
                    <Tooltip label={copied === `sms-${i}` ? 'Kopyalandı!' : 'Kopyala'}>
                      <ActionIcon 
                        variant="subtle" 
                        color={copied === `sms-${i}` ? 'green' : 'gray'}
                        onClick={() => copyToClipboard(text, `sms-${i}`)}
                      >
                        {copied === `sms-${i}` ? <IconCheck size={16} /> : <IconCopy size={16} />}
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                  <Text size="sm">{text}</Text>
                  <Text size="xs" c="dimmed" mt="xs" ta="right">{text.length} Karakter</Text>
                </Card>
              ))}
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="email" pt="md">
            <Stack gap="sm">
              {(variants?.email || []).map((mail: any, i) => {
                const subject = typeof mail === 'object' ? (mail.subject || 'Konu Belirtilmedi') : 'Kampanya Duyurusu';
                const body = typeof mail === 'object' ? (mail.body || '') : String(mail);
                
                return (
                  <Card key={i} withBorder padding="md" radius="md">
                    <Group justify="space-between" mb="xs">
                      <Badge variant="light" color="indigo">Varyant {i + 1}</Badge>
                      <Group gap={5}>
                        <Tooltip label="Gövdeyi Kopyala">
                          <ActionIcon variant="subtle" color="gray" onClick={() => copyToClipboard(body, `email-body-${i}`)}>
                            <IconCopy size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </Group>
                    <Text size="sm" fw={700} mb={4}>Konu: {subject}</Text>
                    <Textarea 
                      variant="unstyled" 
                      size="sm" 
                      readOnly 
                      value={body} 
                      autosize 
                      minRows={3}
                      styles={{ input: { padding: 0, color: '#475569', fontSize: '13px' } }}
                    />
                  </Card>
                );
              })}
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="push" pt="md">
            <Stack gap="sm">
              {(variants?.push || []).map((text, i) => (
                <Card key={i} withBorder padding="md" radius="md">
                  <Group justify="space-between" mb="xs">
                    <Badge variant="light" color="cyan">Varyant {i + 1}</Badge>
                    <ActionIcon variant="subtle" color="gray" onClick={() => copyToClipboard(text, `push-${i}`)}>
                      <IconCopy size={16} />
                    </ActionIcon>
                  </Group>
                  <Text size="sm">{text}</Text>
                </Card>
              ))}
            </Stack>
          </Tabs.Panel>

          <Group justify="flex-end" mt="xl">
            <Button variant="subtle" color="gray" onClick={() => setVariants(null)} leftSection={<IconRefresh size={16} />}>
              Yeniden Üret
            </Button>
            <Button onClick={onClose}>Kapat</Button>
          </Group>
        </Tabs>
      )}
    </Modal>
  );
};
