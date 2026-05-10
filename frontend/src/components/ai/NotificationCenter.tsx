import React, { useEffect, useState } from 'react'
import { Drawer, Text, ScrollArea, LoadingOverlay, Badge, Group, ActionIcon, Stack, Paper, Title, Button } from '@mantine/core'
import { IconBell, IconCheck, IconInfoCircle, IconAlertTriangle, IconAlertCircle, IconChecklist, IconSparkles } from '@tabler/icons-react'
import useNotificationStore, { AINotification } from '../../stores/notificationStore'
import useDashboardStore from '../../stores/dashboardStore'
import { CampaignScheduler } from './CampaignScheduler'
import { CampaignVariantProducer } from './CampaignVariantProducer'
import { useDisclosure } from '@mantine/hooks'

interface NotificationCenterProps {
  opened: boolean
  onClose: () => void
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ opened, onClose }) => {
  const { notifications, loading, fetchNotifications, markAsRead, unreadCount } = useNotificationStore()
  const { selectedDataSourceId } = useDashboardStore()
  const [schedulerOpened, { open: openScheduler, close: closeScheduler }] = useDisclosure(false)
  const [variantOpened, { open: openVariant, close: closeVariant }] = useDisclosure(false)
  const [selectedNotifForAction, setSelectedNotifForAction] = useState<AINotification | null>(null)

  useEffect(() => {
    if (opened) {
      fetchNotifications()
    }
  }, [opened])

  const getIcon = (type: string) => {
    switch (type) {
      case 'critical': return <IconAlertCircle size={18} color="var(--mantine-color-red-6)" />
      case 'warning': return <IconAlertTriangle size={18} color="var(--mantine-color-orange-6)" />
      case 'success': return <IconCheck size={18} color="var(--mantine-color-teal-6)" />
      default: return <IconInfoCircle size={18} color="var(--mantine-color-blue-6)" />
    }
  }

  const getTimeAgo = (dateStr: string) => {
    const d = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Az önce'
    if (diffMins < 60) return `${diffMins} dk önce`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} sa önce`
    return d.toLocaleDateString('tr-TR')
  }

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconBell size={20} />
          <Title order={4}>AI Bildirim Merkezi</Title>
          {unreadCount > 0 && <Badge color="red" variant="filled" size="sm">{unreadCount}</Badge>}
        </Group>
      }
      position="right"
      size="md"
      padding="md"
    >
      <LoadingOverlay visible={loading} overlayProps={{ blur: 1 }} />
      
      <ScrollArea h="calc(100vh - 80px)" offsetScrollbars>
        {notifications.length === 0 ? (
          <Stack align="center" mt="50" gap="xs">
            <IconChecklist size={40} color="gray" />
            <Text c="dimmed">Henüz bir bildiriminiz yok.</Text>
          </Stack>
        ) : (
          <Stack gap="sm" mb="xl">
            {notifications.map((notif) => (
              <Paper 
                key={notif.id} 
                p="sm" 
                withBorder 
                radius="md" 
                style={{ 
                  backgroundColor: notif.is_read ? 'transparent' : 'var(--mantine-color-blue-0)',
                  borderColor: notif.is_read ? undefined : 'var(--mantine-color-blue-2)',
                  transition: 'background-color 0.2s ease'
                }}
              >
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    {getIcon(notif.type)}
                    <Text fw={700} size="sm">{notif.title}</Text>
                  </Group>
                  <Text size="xs" c="dimmed">{getTimeAgo(notif.created_at)}</Text>
                </Group>
                
                <Text size="sm" mb="xs" c="gray.7">{notif.message}</Text>
                               {!notif.is_read && (
                    <Stack gap="xs" mt="xs">
                      {notif.metadata?.campaign_draft && (
                        <Paper withBorder p="xs" radius="sm" style={{ backgroundColor: 'var(--mantine-color-indigo-0)', borderColor: 'var(--mantine-color-indigo-2)' }}>
                          <Group gap="xs" mb={5}>
                            <IconSparkles size={14} color="var(--mantine-color-indigo-6)" />
                            <Text size="xs" fw={700} c="indigo.7">AI Kampanya Taslağı</Text>
                          </Group>
                          <Text size="xs" lineClamp={2}>{notif.metadata.campaign_draft.offer}</Text>
                        </Paper>
                      )}

                      <Group gap="xs">
                        {notif.metadata?.link && (
                          <Button
                            size="compact-xs"
                            variant="light"
                            color="blue"
                            leftSection={<IconChecklist size={12} />}
                            onClick={() => {
                              window.location.hash = `#/${notif.metadata.link}`;
                              onClose();
                            }}
                          >
                            Analize Git
                          </Button>
                        )}
                        
                        {notif.metadata?.campaign_draft && (
                          <Button 
                            size="compact-xs" 
                            variant="gradient" 
                            gradient={{ from: 'indigo', to: 'violet' }}
                            leftSection={<IconSparkles size={12} />}
                            onClick={() => {
                              setSelectedNotifForAction(notif)
                              openVariant()
                            }}
                          >
                            Hemen Uygula
                          </Button>
                        )}

                        {!notif.metadata?.campaign_draft && (notif.type === 'critical' || notif.type === 'warning') && (
                          <Button 
                            size="compact-xs" 
                            variant="light" 
                            color="red" 
                            leftSection={<IconSparkles size={12} />}
                            onClick={() => {
                              setSelectedNotifForAction(notif)
                              openVariant()
                            }}
                          >
                            AI İçerik Üret
                          </Button>
                        )}
                        
                        <ActionIcon 
                          size="sm" 
                          variant="light" 
                          color="blue" 
                          onClick={() => markAsRead(notif.id)}
                          title="Okundu olarak işaretle"
                        >
                          <IconCheck size={14} />
                        </ActionIcon>
                      </Group>
                    </Stack>
                )}
              </Paper>
            ))}
          </Stack>
        )}
      </ScrollArea>

      <CampaignScheduler 
        opened={schedulerOpened} 
        onClose={closeScheduler} 
        initialData={{
          title: selectedNotifForAction?.metadata?.campaign_draft?.title || selectedNotifForAction?.title || 'Anomali Bazlı Kampanya',
          description: selectedNotifForAction?.metadata?.campaign_draft?.offer || `Anomali tespiti sonrası önerilen aksiyon: ${selectedNotifForAction?.message}`,
          segment: selectedNotifForAction?.metadata?.campaign_draft?.segment || (selectedNotifForAction?.metadata?.anomaly?.segment as string) || 'Risk Altindakiler'
        }}
      />

      <CampaignVariantProducer
        opened={variantOpened}
        onClose={closeVariant}
        campaignDetail={{
          title: selectedNotifForAction?.metadata?.campaign_draft?.title || selectedNotifForAction?.title,
          base_offer: selectedNotifForAction?.metadata?.campaign_draft?.offer || selectedNotifForAction?.message,
          segment: selectedNotifForAction?.metadata?.campaign_draft?.segment || 'Hedef Segment',
          goal: "Anomali Giderme ve Satış Artışı"
        }}
      />
    </Drawer>
  )
}
