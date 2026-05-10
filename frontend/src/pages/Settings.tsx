import { useState, useEffect } from 'react'
import {
  Container,
  Paper,
  Tabs,
  Title,
  Text,
  Group,
  TextInput,
  Select,
  Switch,
  Button,
  Stack,
  Divider,
  Grid,
  Badge,
  Alert,
  Avatar,
  Box,
  LoadingOverlay,
  SimpleGrid,
  Radio,
  SegmentedControl,
} from '@mantine/core'
import {
  IconUser,
  IconBell,
  IconPalette,
  IconDeviceFloppy,
  IconAlertCircle,
  IconCheck,
  IconWorld,
  IconHelpCircle,
  IconExternalLink,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import apiClient from '../api/client'
import { useThemeStore, ColorScheme } from '../stores/themeStore'
import '../styles/Settings.css'

export default function Settings() {
  const [activeTab, setActiveTab] = useState<string | null>('account')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [userProfile, setUserProfile] = useState<any>(null)
  const [currency, setCurrency] = useState('TRY')
  const [language, setLanguage] = useState('tr')
  const { activeTheme, colorScheme, setActiveTheme, setColorScheme } = useThemeStore()

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const data = await apiClient.getSettings()
      const profileData = await apiClient.getProfile() // Fetch profile data

      if (profileData) {
        setFullName(`${profileData.first_name || ''} ${profileData.last_name || ''}`.trim())
        setEmail(profileData.email || '')
        setUserProfile(profileData)
      }
      
      if (data.localization) {
        setCurrency(data.localization.currency || 'TRY')
        setLanguage(data.localization.language || 'tr')
      }
      if (data.appearance) {
        // appearance handled by themeStore
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      notifications.show({
        title: 'Hata',
        message: 'Ayarlar yüklenirken bir sorun oluştu.',
        color: 'red',
        icon: <IconAlertCircle size={16} />,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const currentSettings = await apiClient.getSettings()
      const updatedSettings = {
        ...currentSettings,
        localization: { 
          ...currentSettings.localization,
          currency, 
          language, 
          date_format: language === 'tr' ? 'DD.MM.YYYY' : 'MM/DD/YYYY' 
        },
        appearance: { 
          ...currentSettings.appearance,
          primary_color: activeTheme === 'marketCRM' ? '#0f766e' : '#4f46e5' 
        },
      }
      
      await apiClient.updateSettings(updatedSettings)
      
      notifications.show({
        title: 'Başarılı',
        message: 'Tercihleriniz başarıyla kaydedildi.',
        color: 'green',
        icon: <IconCheck size={16} />,
      })
    } catch (error) {
      console.error('Failed to save settings:', error)
      notifications.show({
        title: 'Hata',
        message: 'Ayarlar kaydedilirken bir hata oluştu.',
        color: 'red',
        icon: <IconAlertCircle size={16} />,
      })
    } finally {
      setSaving(false)
    }
  }

  const handleUpdatePassword = async () => {
    if (!newPassword || !confirmPassword) {
      notifications.show({
        title: 'Hata',
        message: 'Lütfen tüm şifre alanlarını doldurun',
        color: 'red',
      })
      return
    }

    if (newPassword !== confirmPassword) {
      notifications.show({
        title: 'Hata',
        message: 'Şifreler eşleşmiyor',
        color: 'red',
      })
      return
    }

    try {
      setLoading(true)
      await apiClient.updateProfile({ password: newPassword })
      notifications.show({
        title: 'Başarılı',
        message: 'Şifreniz güncellendi',
        color: 'green',
      })
      setNewPassword('')
      setConfirmPassword('')
    } catch (error) {
      notifications.show({
        title: 'Hata',
        message: 'Şifre güncellenirken bir hata oluştu',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateProfile = async () => {
    try {
      setLoading(true)
      const parts = fullName.split(' ')
      const firstName = parts[0]
      const lastName = parts.slice(1).join(' ')
      
      await apiClient.updateProfile({ first_name: firstName, last_name: lastName })
      notifications.show({
        title: 'Başarılı',
        message: 'Profil bilgileriniz güncellendi',
        color: 'green',
      })
    } catch (error) {
      notifications.show({
        title: 'Hata',
        message: 'Profil güncellenirken bir hata oluştu',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container size="xl" py="md" className="settings-container">
      <Box style={{ position: 'relative' }}>
        <LoadingOverlay visible={loading} zIndex={10} overlayProps={{ radius: 'sm', blur: 2 }} />
        
        <Group justify="space-between" mb="xl">
          <div>
            <Title order={2} className="settings-title">Kullanıcı Ayarları</Title>
            <Text c="dimmed" size="sm">Profilinizi ve kişisel tercihlerinizi buradan yönetebilirsiniz.</Text>
          </div>
          <Button 
            leftSection={<IconDeviceFloppy size={18} />} 
            onClick={handleSave} 
            loading={saving}
            className="save-button"
            radius="md"
          >
            Değişiklikleri Kaydet
          </Button>
        </Group>

        <Paper radius="md" p={0} withBorder className="settings-paper">
          <Tabs value={activeTab} onChange={setActiveTab} orientation="vertical" variant="pills" classNames={{
            root: 'settings-tabs-root',
            list: 'settings-tabs-list',
            tab: 'settings-tab',
            panel: 'settings-panel'
          }}>
            <Tabs.List>
              <Tabs.Tab value="account" leftSection={<IconUser size={18} />}>
                Profil Bilgileri
              </Tabs.Tab>
              <Tabs.Tab value="localization" leftSection={<IconWorld size={18} />}>
                Bölgesel Tercihler
              </Tabs.Tab>
              <Tabs.Tab value="appearance" leftSection={<IconPalette size={18} />}>
                Görünüm
              </Tabs.Tab>
              <Tabs.Tab value="notifications" leftSection={<IconBell size={18} />}>
                Bildirimler
              </Tabs.Tab>
              <Tabs.Tab value="help" leftSection={<IconHelpCircle size={18} />}>
                Yardım & Destek
              </Tabs.Tab>
            </Tabs.List>

            {/* Account Tab */}
            <Tabs.Panel value="account">
              <Stack gap="lg">
                <Title order={4}>Profil ve Güvenlik</Title>
                <Divider />
                
                <Group>
                  <Avatar size={80} radius="xl" color="blue" src={null}>
                    {fullName.charAt(0).toUpperCase() || 'U'}
                  </Avatar>
                  <div>
                    <Text fw={600} size="lg">{fullName}</Text>
                    <Text size="sm" c="dimmed">{email}</Text>
                    <Badge mt={4} color="blue" variant="light">AKTİF KULLANICI</Badge>
                  </div>
                </Group>

                <Grid mt="md">
                  <Grid.Col span={{ base: 12, md: 6 }}>
                    <TextInput 
                      label="Ad Soyad" 
                      placeholder="Adınız ve soyadınız" 
                      value={fullName}
                      onChange={(e) => setFullName(e.currentTarget.value)}
                      radius="md" 
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, md: 6 }}>
                    <TextInput 
                      label="Email Adresi" 
                      value={email} 
                      disabled 
                      radius="md" 
                      description="E-posta adresi değiştirilemez."
                    />
                  </Grid.Col>
                </Grid>

                <Button 
                  variant="light" 
                  color="blue" 
                  radius="md" 
                  style={{ width: 'fit-content' }}
                  onClick={handleUpdateProfile}
                  loading={loading}
                >
                  Profil Bilgilerini Güncelle
                </Button>

                <Divider label="Şifre Değiştirme" labelPosition="center" my="sm" />
                
                <Grid>
                  <Grid.Col span={{ base: 12, md: 6 }}>
                    <TextInput 
                      label="Yeni Şifre" 
                      placeholder="••••••••" 
                      type="password" 
                      radius="md" 
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.currentTarget.value)}
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, md: 6 }}>
                    <TextInput 
                      label="Şifre Tekrar" 
                      placeholder="••••••••" 
                      type="password" 
                      radius="md" 
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.currentTarget.value)}
                    />
                  </Grid.Col>
                </Grid>
                
                <Button 
                  variant="light" 
                  color="indigo" 
                  radius="md" 
                  style={{ width: 'fit-content' }}
                  onClick={handleUpdatePassword}
                  loading={loading}
                >
                  Şifreyi Güncelle
                </Button>
              </Stack>
            </Tabs.Panel>

            {/* Localization Tab */}
            <Tabs.Panel value="localization">
              <Stack gap="lg">
                <Title order={4}>Bölgesel ve Dil Tercihleri</Title>
                <Divider />
                
                <Grid>
                  <Grid.Col span={{ base: 12, md: 6 }}>
                    <Select
                      label="Tercih Edilen Para Birimi"
                      description="Raporlardaki parasal değerlerin gösterim formatı."
                      data={[
                        { value: 'TRY', label: 'Türk Lirası (₺)' },
                        { value: 'USD', label: 'ABD Doları ($)' },
                        { value: 'EUR', label: 'Euro (€)' },
                      ]}
                      value={currency}
                      onChange={(val) => setCurrency(val || 'TRY')}
                      radius="md"
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, md: 6 }}>
                    <Select
                      label="Arayüz Dili"
                      description="Uygulama metinlerinin dili."
                      data={[
                        { value: 'tr', label: 'Türkçe' },
                        { value: 'en', label: 'English' },
                      ]}
                      value={language}
                      onChange={(val) => setLanguage(val || 'tr')}
                      radius="md"
                    />
                  </Grid.Col>
                </Grid>

                <Alert variant="light" color="blue" radius="md" icon={<IconWorld size={16} />}>
                  Bu ayarlar sadece sizin oturumunuzu ve raporlardaki kişisel görünümünüzü etkiler.
                </Alert>
              </Stack>
            </Tabs.Panel>

            {/* Appearance Tab */}
            <Tabs.Panel value="appearance">
              <Stack gap="lg">
                <Title order={4}>Arayüz Görünümü</Title>
                <Text size="sm" c="dimmed">Tema ve renk düzenini buradan özelleştirebilirsiniz.</Text>
                <Divider />

                <Text fw={600} size="sm">Tema Seçimi</Text>
                <SimpleGrid cols={{ base: 1, sm: 2 }}>
                  <Paper
                    withBorder
                    p="lg"
                    radius="md"
                    data-active-theme={activeTheme === 'default' ? 'indigo' : ''}
                    className={`theme-card ${activeTheme === 'default' ? 'theme-card-active' : ''}`}
                    onClick={() => setActiveTheme('default')}
                    style={{
                      cursor: 'pointer',
                      borderColor: activeTheme === 'default' ? '#6366f1' : undefined,
                    }}
                  >
                    <Group gap="sm" mb="sm">
                      <Radio checked={activeTheme === 'default'} readOnly />
                      <Text fw={600}>Varsayılan (İndigo)</Text>
                    </Group>
                    <Group gap={4}>
                      <Box w={20} h={20} style={{ borderRadius: 4, backgroundColor: '#4f46e5' }} />
                      <Box w={20} h={20} style={{ borderRadius: 4, backgroundColor: '#6366f1' }} />
                      <Box w={20} h={20} style={{ borderRadius: 4, backgroundColor: '#eef2ff' }} />
                    </Group>
                    <Text size="xs" c="dimmed" mt={4}>Inter + Outfit • Keskin ve profesyonel</Text>
                  </Paper>

                  <Paper
                    withBorder
                    p="lg"
                    radius="md"
                    data-active-theme={activeTheme === 'marketCRM' ? 'teal' : ''}
                    className={`theme-card ${activeTheme === 'marketCRM' ? 'theme-card-active' : ''}`}
                    onClick={() => setActiveTheme('marketCRM')}
                    style={{
                      cursor: 'pointer',
                      borderColor: activeTheme === 'marketCRM' ? '#0f766e' : undefined,
                    }}
                  >
                    <Group gap="sm" mb="sm">
                      <Radio checked={activeTheme === 'marketCRM'} readOnly />
                      <Text fw={600}>MarketCRM (Teal)</Text>
                    </Group>
                    <Group gap={4}>
                      <Box w={20} h={20} style={{ borderRadius: 4, backgroundColor: '#0f766e' }} />
                      <Box w={20} h={20} style={{ borderRadius: 4, backgroundColor: '#14b8a6' }} />
                      <Box w={20} h={20} style={{ borderRadius: 4, backgroundColor: '#f59e0b' }} />
                    </Group>
                    <Text size="xs" c="dimmed" mt={4}>Poppins + Open Sans • Yumuşak ve modern</Text>
                  </Paper>
                </SimpleGrid>

                <Divider />

                <Text fw={600} size="sm">Renk Düzeni</Text>
                <SegmentedControl
                  value={colorScheme}
                  onChange={(val) => setColorScheme(val as ColorScheme)}
                  data={[
                    { value: 'light', label: 'Aydınlık' },
                    { value: 'dark', label: 'Karanlık' },
                  ]}
                />

                <Divider />

                <Text fw={600} size="sm">Yazı Tipi Önizlemesi</Text>
                <Paper withBorder p="md" radius="md" bg="var(--mantine-color-gray-0)">
                  <Text
                    size="xl"
                    fw={700}
                    style={{ fontFamily: activeTheme === 'marketCRM' ? "'Poppins', sans-serif" : "'Outfit', sans-serif" }}
                  >
                    Merhaba, CRM'inize Hoş Geldiniz
                  </Text>
                  <Text
                    size="sm"
                    mt={4}
                    style={{ fontFamily: activeTheme === 'marketCRM' ? "'Open Sans', sans-serif" : "'Inter', sans-serif" }}
                  >
                    Bu tema ile müşterilerinizi daha iyi yönetin. Satışlarınızı takip edin, raporları analiz edin.
                  </Text>
                  <Text size="xs" c="dimmed" mt={8}>
                    {activeTheme === 'marketCRM' ? 'Poppins + Open Sans' : 'Outfit + Inter'}
                  </Text>
                </Paper>
              </Stack>
            </Tabs.Panel>

            {/* Notifications Tab */}
            <Tabs.Panel value="notifications">
              <Stack gap="lg">
                <Title order={4}>Bildirim ve Uyarı Tercihleri</Title>
                <Divider />
                
                <Stack>
                  <Group justify="space-between">
                    <div>
                      <Text fw={500}>E-posta Özeti</Text>
                      <Text size="xs" c="dimmed">Günlük kampanya ve satış özetlerini e-posta ile al.</Text>
                    </div>
                    <Switch defaultChecked radius="md" />
                  </Group>
                  <Divider variant="dashed" />
                  <Group justify="space-between">
                    <div>
                      <Text fw={500}>Churn Uyarıları</Text>
                      <Text size="xs" c="dimmed">Müşteri churn risklerinde ani artış olduğunda bildirim gönder.</Text>
                    </div>
                    <Switch defaultChecked radius="md" />
                  </Group>
                  <Divider variant="dashed" />
                  <Group justify="space-between">
                    <div>
                      <Text fw={500}>Kampanya Önerileri</Text>
                      <Text size="xs" c="dimmed">Yeni akıllı kampanya önerileri oluştuğunda haber ver.</Text>
                    </div>
                    <Switch radius="md" />
                  </Group>
                </Stack>
              </Stack>
            </Tabs.Panel>

            {/* Help Tab */}
            <Tabs.Panel value="help">
              <Stack gap="lg">
                <Title order={4}>Yardım ve Destek</Title>
                <Divider />
                
                <Text size="sm">Yardıma mı ihtiyacınız var? XPlusCRM kullanım dökümantasyonuna ve destek kanallarına buradan ulaşabilirsiniz.</Text>
                
                <Stack gap="md">
                  <Paper withBorder p="md" radius="md" className="help-card">
                    <Group justify="space-between">
                      <Group>
                        <ThemeIcon color="blue" variant="light" size="lg">
                          <IconHelpCircle size={20} />
                        </ThemeIcon>
                        <div>
                          <Text fw={600}>Kullanım Kılavuzu</Text>
                          <Text size="xs" c="dimmed">CRM modülleri ve analizlerin nasıl yorumlanacağını öğrenin.</Text>
                        </div>
                      </Group>
                      <Button variant="subtle" rightSection={<IconExternalLink size={14} />}>Görüntüle</Button>
                    </Group>
                  </Paper>

                  <Paper withBorder p="md" radius="md" className="help-card">
                    <Group justify="space-between">
                      <Group>
                        <ThemeIcon color="teal" variant="light" size="lg">
                          <IconDeviceFloppy size={20} />
                        </ThemeIcon>
                        <div>
                          <Text fw={600}>Sürüm Notları</Text>
                          <Text size="xs" c="dimmed">XPlusCRM v1.2.0 - Son güncellemeler ve yenilikler.</Text>
                        </div>
                      </Group>
                      <Button variant="subtle" rightSection={<IconExternalLink size={14} />}>Detaylar</Button>
                    </Group>
                  </Paper>
                </Stack>

                <Box mt="xl">
                  <Text size="xs" c="dimmed" ta="center">XPlus Intelligence System © 2026</Text>
                  <Text size="xs" c="dimmed" ta="center">Software Version: 1.2.0-stable</Text>
                </Box>
              </Stack>
            </Tabs.Panel>
          </Tabs>
        </Paper>
      </Box>
    </Container>
  )
}

function ThemeIcon({ children, color, variant, size }: { children: React.ReactNode, color: string, variant: string, size: string }) {
  return (
    <Box 
      style={{ 
        backgroundColor: variant === 'light' ? `var(--mantine-color-${color}-light)` : 'transparent',
        color: `var(--mantine-color-${color}-filled)`,
        width: size === 'lg' ? 40 : 32,
        height: size === 'lg' ? 40 : 32,
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      {children}
    </Box>
  )
}
