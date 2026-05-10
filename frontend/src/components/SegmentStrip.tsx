import { HoverCard, Group, Text, Stack, Divider } from '@mantine/core'
import { IconTrophy, IconStar, IconAlertTriangle } from '@tabler/icons-react'
import InlineSpinner from './InlineSpinner'
import '../styles/SegmentStrip.css'

interface SegmentData {
  count: number
  revenue: number
  avgRevenue: number
  customerPercent: number
  revenuePercent: number
  segments: string
}

interface SegmentGroups {
  degerli: SegmentData | null
  potansiyel: SegmentData | null
  risk: SegmentData | null
}

interface SegmentStripProps {
  segmentGroups: SegmentGroups
  loading: boolean
}

const SEGMENT_CONFIG = [
  {
    key: 'degerli' as const,
    label: 'Değerli Müşteriler',
    shortLabel: 'Değerli',
    icon: IconTrophy,
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    tooltipColor: '#059669',
    shadowColor: 'rgba(16, 185, 129, 0.25)',
  },
  {
    key: 'potansiyel' as const,
    label: 'Potansiyel Müşteriler',
    shortLabel: 'Potansiyel',
    icon: IconStar,
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    tooltipColor: '#2563eb',
    shadowColor: 'rgba(59, 130, 246, 0.25)',
  },
  {
    key: 'risk' as const,
    label: 'Risk Altındaki Müşteriler',
    shortLabel: 'Risk',
    icon: IconAlertTriangle,
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    tooltipColor: '#dc2626',
    shadowColor: 'rgba(239, 68, 68, 0.25)',
  },
]

export default function SegmentStrip({ segmentGroups, loading }: SegmentStripProps) {
  return (
    <div className="segment-strip">
      {SEGMENT_CONFIG.map((seg) => {
        const data = segmentGroups[seg.key]
        const Icon = seg.icon

        return (
          <HoverCard
            key={seg.key}
            width={260}
            shadow="lg"
            withArrow
            position="bottom"
            openDelay={80}
            closeDelay={100}
          >
            <HoverCard.Target>
              <div
                className="segment-item"
                style={{ background: seg.gradient, boxShadow: `0 4px 14px ${seg.shadowColor}` }}
              >
                <div className="segment-item__left">
                  <Icon size={20} stroke={2} />
                  <span className="segment-item__label">{seg.shortLabel}</span>
                </div>
                <div className="segment-item__count">
                  {loading ? (
                    <InlineSpinner size={20} thickness={2} color="rgba(255,255,255,0.8)" />
                  ) : (
                    (data?.count || 0).toLocaleString('tr-TR')
                  )}
                </div>
              </div>
            </HoverCard.Target>

            <HoverCard.Dropdown>
              {data ? (
                <Stack gap="xs" p={4}>
                  <Text fw={700} size="sm" c={seg.tooltipColor}>{seg.label}</Text>
                  <Divider />
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">Toplam Ciro</Text>
                    <Text size="xs" fw={600}>
                      ₺{data.revenue.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">Ort. Ciro / Müşteri</Text>
                    <Text size="xs" fw={600}>
                      ₺{data.avgRevenue.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">Müşteri Oranı</Text>
                    <Text size="xs" fw={600}>%{data.customerPercent.toFixed(1)}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">Ciro Payı</Text>
                    <Text size="xs" fw={600}>%{data.revenuePercent.toFixed(1)}</Text>
                  </Group>
                  {data.segments && (
                    <Text
                      size="xs"
                      c="dimmed"
                      mt={4}
                      pt={8}
                      style={{ borderTop: '1px solid var(--mantine-color-gray-2)' }}
                    >
                      {data.segments}
                    </Text>
                  )}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">Veri bulunamadı</Text>
              )}
            </HoverCard.Dropdown>
          </HoverCard>
        )
      })}
    </div>
  )
}
