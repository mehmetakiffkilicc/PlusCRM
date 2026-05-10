import React, { useState, useEffect } from 'react';
import { Paper, Group, Text, Title, Button, Stack, ThemeIcon, Box, Transition, Skeleton, Badge, Alert } from '@mantine/core';
import { IconSparkles, IconTrendingUp, IconAlertTriangle, IconBolt, IconTrendingDown, IconRefresh } from '@tabler/icons-react';
import { useChatStore } from '../../stores/chatStore';
import useUIStore from '../../stores/uiStore';
import { aiClient } from '../../api/aiClient';
import useDashboardStore from '../../stores/dashboardStore';

interface MorningBriefingProps {
    data: any; // Dashboard analytics data (fallback)
    loading: boolean;
}

export const MorningBriefing = ({ data, loading }: MorningBriefingProps) => {
    const { sendMessage, startNewSession, activeSessionId } = useChatStore();
    const { setChatOpened } = useUIStore();
    const { selectedDataSourceId } = useDashboardStore();
    const [mounted, setMounted] = useState(false);
    const [brief, setBrief] = useState<any>(null);
    const [briefLoading, setBriefLoading] = useState(false);
    const [briefError, setBriefError] = useState(false);

    useEffect(() => {
        setMounted(true);
        if (selectedDataSourceId) {
            fetchBrief();
        }
    }, [selectedDataSourceId]);

    const fetchBrief = async () => {
        setBriefLoading(true);
        setBriefError(false);
        try {
            const result = await aiClient.getWeeklyBrief(selectedDataSourceId!);
            setBrief(result);
        } catch (error) {
            console.error("Morning brief fetch failed:", error);
            setBriefError(true);
        } finally {
            setBriefLoading(false);
        }
    };

    if (briefError) return (
        <Alert
            icon={<IconAlertTriangle size={16} />}
            title="AI Brifingi Yüklenemedi"
            color="orange"
            mb="xl"
            withCloseButton={false}
        >
            <Group justify="space-between" align="center">
                <Text size="sm">Haftalık AI brifingi şu an alınamıyor.</Text>
                <Button size="xs" variant="light" color="orange" leftSection={<IconRefresh size={14} />} onClick={fetchBrief}>
                    Tekrar Dene
                </Button>
            </Group>
        </Alert>
    );

    if (loading || briefLoading || !data) return (
        <Paper p="xl" radius="lg" mb="xl" withBorder>
            <Stack gap="xs">
                <Skeleton height={20} width="30%" mb="xs" />
                <Skeleton height={15} width="90%" />
                <Skeleton height={15} width="80%" />
            </Stack>
        </Paper>
    );

    const handleDeepDive = async () => {
        setChatOpened(true);
        if (!activeSessionId) await startNewSession();
        await sendMessage("Bugünün detaylı brifingini ver. Anomali tespiti ve stratejik önerilerini paylaş.");
    };

    const revenueChange = brief?.revenue_summary?.change_pct ?? 0;
    const isRevenuePositive = revenueChange > 0;
    const summaryText = brief?.top_highlights?.[0] || `Bu hafta ciroda %${Math.abs(revenueChange).toFixed(1)} ${isRevenuePositive ? 'iyileşme' : 'daralma'} var.`;

    return (
        <Transition mounted={mounted} transition="slide-down" duration={800} timingFunction="ease">
            {(styles) => (
                <Paper 
                    p="xl" 
                    radius="lg" 
                    mb="xl"
                    style={{ 
                        ...styles,
                        background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                        color: 'white',
                        position: 'relative',
                        overflow: 'hidden',
                        boxShadow: '0 10px 25px -5px rgba(79, 70, 229, 0.3)'
                    }}
                >
                    <Box style={{ 
                        position: 'absolute', 
                        right: -30, 
                        bottom: -30, 
                        opacity: 0.1, 
                        transform: 'rotate(15deg)' 
                    }}>
                        <IconSparkles size={180} />
                    </Box>

                    <div style={{ position: 'relative', zIndex: 1 }}>
                        <Group justify="space-between" align="center">
                            <Stack gap="xs" style={{ flex: 1 }}>
                                <Group gap="xs">
                                    <ThemeIcon variant="white" color="indigo" size="md" radius="xl">
                                        <IconBolt size={16} />
                                    </ThemeIcon>
                                    <Text size="xs" fw={800} tt="uppercase" lts="1px" style={{ color: 'rgba(255,255,255,0.8)' }}>
                                        AI Strateji Brifingi
                                    </Text>
                                    {brief?.ai_score && (
                                        <Badge color="white" variant="light" size="sm" radius="sm" style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
                                            PM SKOR: {brief.ai_score}
                                        </Badge>
                                    )}
                                </Group>
                                
                                <Title order={2} style={{ fontWeight: 800, fontSize: '1.75rem', lineHeight: 1.2 }}>
                                    Günaydın, Yönetici. <span style={{ color: '#fbbf24' }}>Güne Hazır Mısın?</span>
                                </Title>
                                
                                <Text size="md" fw={500} style={{ color: 'rgba(255,255,255,0.95)', maxWidth: 750, lineHeight: 1.6 }}>
                                    {summaryText} <br />
                                    <span style={{ fontSize: '0.9rem', opacity: 0.85, fontWeight: 400 }}>
                                        Ciro trendi {isRevenuePositive ? 'pozitif' : 'negatif'} yönde (%{Math.abs(revenueChange).toFixed(1)}). 
                                        {brief?.order_summary && ` Toplam sipariş hacmi %${brief.order_summary.change_pct} oranında değişti.`}
                                    </span>
                                </Text>

                                <Group mt="md" gap="sm">
                                    <Paper px="md" py="xs" radius="xl" bg="rgba(255,255,255,0.15)" style={{ border: '1px solid rgba(255,255,255,0.2)' }}>
                                        <Group gap="xs">
                                            {isRevenuePositive ? <IconTrendingUp size={16} color="#4ade80" /> : <IconTrendingDown size={16} color="#fda4af" />}
                                            <Text size="xs" fw={700}>Ciro Sağlığı: %{brief?.ai_score || '75'}</Text>
                                        </Group>
                                    </Paper>
                                    <Paper px="md" py="xs" radius="xl" bg="rgba(255,255,255,0.15)" style={{ border: '1px solid rgba(255,255,255,0.2)' }}>
                                        <Group gap="xs">
                                            <IconSparkles size={16} color="#fbbf24" />
                                            <Text size="xs" fw={700}>3 Stratejik İçgörü Mevcut</Text>
                                        </Group>
                                    </Paper>
                                </Group>
                            </Stack>

                            <Button 
                                variant="white" 
                                color="indigo"
                                leftSection={<IconSparkles size={18} />}
                                radius="xl"
                                size="lg"
                                onClick={handleDeepDive}
                                style={{ 
                                    boxShadow: '0 8px 20px rgba(0,0,0,0.15)',
                                    height: '56px',
                                    padding: '0 28px',
                                    fontWeight: 700
                                }}
                            >
                                Detaylara Bak
                            </Button>
                        </Group>
                    </div>
                </Paper>
            )}
        </Transition>
    );
};
