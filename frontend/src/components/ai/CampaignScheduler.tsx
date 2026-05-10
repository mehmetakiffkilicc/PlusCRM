import React, { useState, useEffect } from 'react'
import { Modal, TextInput, Textarea, Select, Button, Group, Stack, Text, Alert } from '@mantine/core'
import { IconCalendar, IconSend, IconAlertCircle, IconCheck } from '@tabler/icons-react'
import apiClient from '../../api/client'
import { notifications as mantineNotifications } from '@mantine/notifications'

interface CampaignSchedulerProps {
  opened: boolean
  onClose: () => void
  initialData?: {
    title?: string
    description?: string
    segment?: string
    channel?: string
  }
}

export const CampaignScheduler: React.FC<CampaignSchedulerProps> = ({ 
  opened, 
  onClose, 
  initialData 
}) => {
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    segment: 'Tüm Müşteriler',
    channel: 'email',
    scheduled_at: ''
  })

  useEffect(() => {
    if (opened && initialData) {
      setFormData(prev => ({
        ...prev,
        title: initialData.title || prev.title,
        description: initialData.description || prev.description,
        segment: initialData.segment || prev.segment,
        channel: initialData.channel || prev.channel || 'email',
        // Varsayılan yarın bu saat
        scheduled_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16)
      }))
      setSuccess(false)
    }
  }, [opened, initialData])

  const handleSchedule = async () => {
    setLoading(true)
    try {
      await apiClient.scheduleCampaign(formData)
      setSuccess(true)
      mantineNotifications.show({
        title: 'Başarılı',
        message: 'Kampanya başarıyla planlandı.',
        color: 'teal',
        icon: <IconCheck size={18} />
      })
      setTimeout(() => {
        onClose()
      }, 1500)
    } catch (error) {
      console.error('Planlama hatası:', error)
      mantineNotifications.show({
        title: 'Hata',
        message: 'Kampanya planlanırken bir sorun oluştu.',
        color: 'red',
        icon: <IconAlertCircle size={18} />
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <IconCalendar size={20} color="var(--mantine-color-blue-6)" />
          <Text fw={700}>Akıllı Kampanya Planlayıcı</Text>
        </Group>
      }
      size="md"
      radius="md"
    >
      {success ? (
        <Alert icon={<IconCheck size={16} />} title="Kampanya Planlandı!" color="teal" variant="light" mb="md">
            Kampanyanız başarıyla sıraya alındı. Takvim sayfasından takip edebilirsiniz.
        </Alert>
      ) : (
        <Stack gap="md">
          <TextInput
            label="Kampanya Başlığı"
            placeholder="Örn: Hafta Sonu Özel İndirimi"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            required
          />

          <Textarea
            label="Kampanya Mesajı/Açıklaması"
            placeholder="Müşterilere gidecek olan metin..."
            minRows={4}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
          />

          <Group grow>
            <Select
              label="Hedef Segment"
              data={[
                { value: 'Tüm Müşteriler', label: 'Tüm Müşteriler' },
                { value: 'Sampiyonlar', label: 'Şampiyonlar' },
                { value: 'Sadik Musteriler', label: 'Sadık Müşteriler' },
                { value: 'Risk Altindakiler', label: 'Risk Altındakiler' },
                { value: 'Kayip', label: 'Kayıp Müşteriler' }
              ]}
              value={formData.segment}
              onChange={(val) => setFormData({ ...formData, segment: val || 'Tüm Müşteriler' })}
            />

            <Select
              label="Gönderim Kanalı"
              data={[
                { value: 'email', label: 'E-posta' },
                { value: 'sms', label: 'SMS' },
                { value: 'push', label: 'Anlık Bildirim' }
              ]}
              value={formData.channel}
              onChange={(val) => setFormData({ ...formData, channel: val || 'email' })}
            />
          </Group>

          <TextInput
            label="Planlanan Tarih ve Saat"
            type="datetime-local"
            value={formData.scheduled_at}
            onChange={(e) => setFormData({ ...formData, scheduled_at: e.target.value })}
            required
          />

          <Button 
            leftSection={<IconSend size={18} />} 
            onClick={handleSchedule}
            loading={loading}
            fullWidth
            mt="md"
          >
            Kampanyayı Planla
          </Button>
        </Stack>
      )}
    </Modal>
  )
}
