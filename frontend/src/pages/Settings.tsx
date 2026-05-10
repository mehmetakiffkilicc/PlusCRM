import { Container, Paper, Title, Text, Button, Stack, Group, ThemeIcon, Box } from '@mantine/core'
import { IconLock, IconArrowLeft } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'

export default function Settings() {
  const navigate = useNavigate()

  return (
    <Container size="sm" py={100}>
      <Paper radius="md" p={40} withBorder style={{ textAlign: 'center' }}>
        <Stack align="center" gap="xl">
          <ThemeIcon size={80} radius={100} color="orange" variant="light">
            <IconLock size={40} />
          </ThemeIcon>
          
          <div>
            <Title order={2} mb="xs">Ayarlar Bölümü Kilitlidir</Title>
            <Text c="dimmed">
              Demo modunda sistem ayarları ve profil değişiklikleri devre dışı bırakılmıştır. 
              Bu alan sadece tam sürümde erişilebilirdir.
            </Text>
          </div>

          <Divider w="100%" />

          <Group>
            <Button 
              variant="light" 
              leftSection={<IconArrowLeft size={18} />}
              onClick={() => navigate('/')}
            >
              Dashboard'a Dön
            </Button>
          </Group>

          <Text size="xs" c="dimmed" mt="xl">
            MarketFlow Project - Developed by Akif
          </Text>
        </Stack>
      </Paper>
    </Container>
  )
}

function Divider({ w }: { w: string }) {
    return <Box style={{ width: w, height: '1px', backgroundColor: 'var(--mantine-color-gray-2)' }} />
}

