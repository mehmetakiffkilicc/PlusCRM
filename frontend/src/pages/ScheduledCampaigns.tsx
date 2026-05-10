import React, { useEffect, useState } from 'react'
import { 
  Container, Title, Text, Paper, Table, Badge, Group, 
  ActionIcon, Button, Stack, Card, SimpleGrid,
  Menu, Tooltip, Alert, LoadingOverlay
} from '@mantine/core'
import { 
  IconCalendar, IconDotsVertical, IconPlayerPlay, IconX, 
  IconTrash, IconCheck, IconMail, IconPhone, IconBrandWhatsapp,
  IconClock, IconAlertCircle, IconHistory
} from '@tabler/icons-react'
import apiClient from '../api/client'
import { notifications } from '@mantine/notifications'

interface ScheduledCampaign {
  id: number
  title: string
  description: string
  segment: string
  channel: 'email' | 'sms' | 'whatsapp'
  scheduled_at: string
  status: 'pending' | 'completed' | 'cancelled'
  created_at: string
}

export default function ScheduledCampaigns() {
  const [campaigns, setCampaigns] = useState<ScheduledCampaign[]>([])
  const [loading, setLoading] = useState(true)
  const [executingId, setExecutingId] = useState<number | null>(null)

  const fetchCampaigns = async () => {
    try {
      setLoading(true)
      const res = await (apiClient as any).getScheduledCampaigns()
      setCampaigns(res.campaigns || [])
    } catch (err) {
      console.error(err)
      notifications.show({
        title: 'Hata',
        message: 'Kampanyalar yüklenirken bir sorun oluştu.',
        color: 'red'
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCampaigns()
  }, [])

  const handleRunNow = async (id: number) => {
    try {
      setExecutingId(id)
      await (apiClient as any).runScheduledCampaign(id)
      notifications.show({
        title: 'Başarılı',
        message: 'Kampanya başarıyla yürütüldü.',
        color: 'green',
        icon: <IconCheck size={16} />
      })
      fetchCampaigns()
    } catch (err) {
      notifications.show({
        title: 'Hata',
        message: 'Kampanya yürütülürken bir sorun oluştu.',
        color: 'red'
      })
    } finally {
      setExecutingId(null)
    }
  }

  const handleCancel = async (id: number) => {
    try {
      await (apiClient as any).deleteScheduledCampaign(id, true) // POST for cancel
      notifications.show({
        title: 'İptal Edildi',
        message: 'Kampanya iptal edildi.',
        color: 'orange'
      })
      fetchCampaigns()
    } catch (err) {
      notifications.show({
        title: 'Hata',
        message: 'Kampanya iptal edilemedi.',
        color: 'red'
      })
    }
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm('Bu kampanyayı silmek istediğinize emin misiniz?')) return
    try {
      await (apiClient as any).deleteScheduledCampaign(id, false) // DELETE for actual delete
      notifications.show({
        title: 'Silindi',
        message: 'Kampanya sistemden kaldırıldı.',
        color: 'gray'
      })
      fetchCampaigns()
    } catch (err) {
      notifications.show({
        title: 'Hata',
        message: 'Kampanya silinemedi.',
        color: 'red'
      })
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending': return <Badge color="blue" variant="light" leftSection={<IconClock size={12} />}>Beklemede</Badge>
      case 'completed': return <Badge color="green" variant="light" leftSection={<IconCheck size={12} />}>Tamamlandı</Badge>
      case 'cancelled': return <Badge color="gray" variant="light" leftSection={<IconX size={12} />}>İptal Edildi</Badge>
      default: return <Badge color="gray">{status}</Badge>
    }
  }

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'email': return <IconMail size={16} color="var(--mantine-color-blue-6)" />
      case 'sms': return <IconPhone size={16} color="var(--mantine-color-teal-6)" />
      case 'whatsapp': return <IconBrandWhatsapp size={16} color="var(--mantine-color-green-6)" />
      default: return null
    }
  }

  const pendingCount = campaigns.filter(c => c.status === 'pending').length
  const completedCount = campaigns.filter(c => c.status === 'completed').length

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        <Group justify="space-between">
          <Stack gap={0}>
            <Title order={2}>AI Kampanya Takvimi</Title>
            <Text c="dimmed">Planlanmış pazarlama aksiyonlarını izleyin ve yönetin.</Text>
          </Stack>
          <Button 
            variant="light" 
            leftSection={<IconHistory size={18} />} 
            onClick={fetchCampaigns}
            loading={loading}
          >
            Yenile
          </Button>
        </Group>

        <SimpleGrid cols={{ base: 1, sm: 3 }}>
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <Text size="sm" c="dimmed" fw={700}>Toplam Planlanan</Text>
              <IconCalendar size={20} color="gray" />
            </Group>
            <Title order={2} mt="xs">{campaigns.length}</Title>
          </Card>
          <Card shadow="sm" padding="lg" radius="md" withBorder style={{ borderLeft: '4px solid var(--mantine-color-blue-5)' }}>
            <Group justify="space-between">
              <Text size="sm" c="dimmed" fw={700}>Bekleyen</Text>
              <IconClock size={20} color="var(--mantine-color-blue-5)" />
            </Group>
            <Title order={2} mt="xs" c="blue">{pendingCount}</Title>
          </Card>
          <Card shadow="sm" padding="lg" radius="md" withBorder style={{ borderLeft: '4px solid var(--mantine-color-green-5)' }}>
            <Group justify="space-between">
              <Text size="sm" c="dimmed" fw={700}>Tamamlanan (Bu Ay)</Text>
              <IconCheck size={20} color="var(--mantine-color-green-5)" />
            </Group>
            <Title order={2} mt="xs" c="green">{completedCount}</Title>
          </Card>
        </SimpleGrid>

        <Paper withBorder radius="md" p={0} style={{ overflow: 'hidden' }} pos="relative">
          <LoadingOverlay visible={loading} overlayProps={{ blur: 1 }} />
          <Table verticalSpacing="md" highlightOnHover>
            <Table.Thead style={{ backgroundColor: '#f8fafc' }}>
              <Table.Tr>
                <Table.Th>Kampanya Detayı</Table.Th>
                <Table.Th>Segment</Table.Th>
                <Table.Th>Kanal</Table.Th>
                <Table.Th>Planlanan Tarih</Table.Th>
                <Table.Th>Durum</Table.Th>
                <Table.Th style={{ width: 100 }}></Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {campaigns.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={6} style={{ textAlign: 'center', padding: '100px 0' }}>
                    <Stack align="center" gap="xs">
                      <IconCalendar size={48} color="lightgray" />
                      <Text c="dimmed">Henüz planlanmış bir kampanya bulunmuyor.</Text>
                      <Text size="sm" c="dimmed">Kampanya Önerileri veya AI Asistan üzerinden planlama yapabilirsiniz.</Text>
                    </Stack>
                  </Table.Td>
                </Table.Tr>
              ) : (
                campaigns.map((item) => (
                  <Table.Tr key={item.id}>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text fw={700} size="sm">{item.title}</Text>
                        <Text size="xs" c="dimmed" lineClamp={1}>{item.description}</Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="dot" color="blue">{item.segment}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {getChannelIcon(item.channel)}
                        <Text size="sm" style={{ textTransform: 'capitalize' }}>{item.channel}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text size="sm" fw={500}>{new Date(item.scheduled_at).toLocaleDateString('tr-TR')}</Text>
                        <Group gap={4}>
                          <IconClock size={12} color="gray" />
                          <Text size="xs" c="dimmed">{new Date(item.scheduled_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}</Text>
                        </Group>
                      </Stack>
                    </Table.Td>
                    <Table.Td>{getStatusBadge(item.status)}</Table.Td>
                    <Table.Td>
                      <Group gap="xs" justify="flex-end">
                        {item.status === 'pending' && (
                          <Tooltip label="Şimdi Çalıştır">
                            <ActionIcon 
                              color="green" 
                              variant="light" 
                              onClick={() => handleRunNow(item.id)}
                              loading={executingId === item.id}
                            >
                              <IconPlayerPlay size={16} />
                            </ActionIcon>
                          </Tooltip>
                        )}
                        <Menu position="bottom-end" shadow="md">
                          <Menu.Target>
                            <ActionIcon variant="subtle" color="gray">
                              <IconDotsVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            {item.status === 'pending' && (
                              <Menu.Item 
                                leftSection={<IconX size={14} />} 
                                color="orange"
                                onClick={() => handleCancel(item.id)}
                              >
                                İptal Et
                              </Menu.Item>
                            )}
                            <Menu.Item 
                              leftSection={<IconTrash size={14} />} 
                              color="red"
                              onClick={() => handleDelete(item.id)}
                            >
                              Sil
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Paper>

        <Alert icon={<IconAlertCircle size={16} />} title="Kampanya İşleme" color="blue" variant="light">
          Planlanmış kampanyalar sistem tarafından otomatik olarak işlenmektedir. Zamanı gelen bir kampanyayı beklememek istiyorsanız "Şimdi Çalıştır" butonunu kullanabilirsiniz.
        </Alert>
      </Stack>
    </Container>
  )
}
