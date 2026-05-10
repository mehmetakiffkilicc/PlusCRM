import React, { useState, useEffect } from 'react';
import { Card, Text, Group, Stack, Badge, ThemeIcon, Button, Loader, Paper, Title, Box } from '@mantine/core';
import { IconSparkles, IconPhoneCall, IconMail, IconArrowRight, IconAlertCircle, IconCheck, IconGift } from '@tabler/icons-react';
import { aiClient } from '../../api/aiClient';

interface AINBAWidgetProps {
    customerId: string;
    customerData: any;
    dataSourceId: string | number;
}

export const AINBAWidget = ({ customerId, customerData, dataSourceId }: AINBAWidgetProps) => {
    const [loading, setLoading] = useState(false);
    const [actions, setActions] = useState<any[]>([]);

    useEffect(() => {
        const fetchNBA = async () => {
            if (!customerId) return;
            setLoading(true);
            try {
                const res = await aiClient.getCustomerNBA(customerId, dataSourceId);
                if (res.actions) {
                    // İkon haritalama
                    const actionsWithIcons = res.actions.map((action: any) => ({
                        ...action,
                        icon: action.type === 'call' ? <IconPhoneCall size={16} /> : 
                              action.type === 'discount' ? <IconGift size={16} /> : 
                              <IconMail size={16} />
                    }));
                    setActions(actionsWithIcons);
                }
            } catch (err) {
                console.error("NBA Error:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchNBA();
    }, [customerId, dataSourceId]);

    if (loading) return <Paper p="md" withBorder radius="md" style={{ display: 'flex', justifyContent: 'center' }}><Loader size="sm" color="violet" /></Paper>;

    return (
        <Card withBorder radius="md" p="md" bg="violet.0" style={{ borderLeft: '4px solid #7c3aed' }}>
            <Group justify="space-between" mb="md">
                <Group gap="xs">
                    <ThemeIcon color="violet" variant="filled" size="sm" radius="xl">
                        <IconSparkles size={14} />
                    </ThemeIcon>
                    <Title order={6} c="violet.9">AI: Next Best Action (NBA)</Title>
                </Group>
                <Badge variant="light" color="violet" size="xs">Canlı Analiz</Badge>
            </Group>

            <Stack gap="sm">
                {actions.map((action, idx) => (
                    <Paper key={idx} p="xs" radius="sm" withBorder bg="white">
                        <Group gap="xs" align="flex-start" wrap="nowrap">
                            <ThemeIcon 
                                color={action.priority === 'high' ? 'red' : action.priority === 'medium' ? 'violet' : 'gray'} 
                                variant="light" 
                                size="md"
                            >
                                {action.icon}
                            </ThemeIcon>
                            <Box style={{ flex: 1 }}>
                                <Group justify="space-between" mb={2}>
                                    <Text size="sm" fw={700}>{action.title}</Text>
                                    <Badge size="xs" color={action.priority === 'high' ? 'red' : 'gray'}>
                                        {action.priority === 'high' ? 'Öncelikli' : 'Normal'}
                                    </Badge>
                                </Group>
                                <Text size="xs" c="dimmed">{action.description}</Text>
                                <Group mt="xs" justify="flex-end">
                                    <Button variant="subtle" size="compact-xs" rightSection={<IconArrowRight size={12} />}>
                                        Aksiyonu Başlat
                                    </Button>
                                </Group>
                            </Box>
                        </Group>
                    </Paper>
                ))}
            </Stack>
        </Card>
    );
};
