import React, { useState } from 'react';
import { TextInput, ActionIcon, Kbd, Group, Text, Box, Transition, Paper, Stack, UnstyledButton } from '@mantine/core';
import { useHotkeys } from '@mantine/hooks';
import { useNavigate } from 'react-router-dom';
import { 
    IconSearch, IconSparkles, IconCommand, IconArrowRight, IconLayoutDashboard,
    IconUsers, IconFilter, IconPoint, IconBox 
} from '@tabler/icons-react';
import { useChatStore } from '../../stores/chatStore';
import useUIStore from '../../stores/uiStore';

const ROUTE_MAP: Record<string, string> = {
    'ana sayfa': '/',
    'dashboard': '/',
    'rfm': '/rfm-analizi',
    'churn': '/churn-analizi',
    'segmentasyon': '/segmentasyon',
    'kampanya': '/kampanyalar',
    'öneri': '/kampanya-onerileri',
    'müşteri portalı': '/musteri-portali',
    'ürün': '/urunler',
    'marka raporu': '/marka-raporu',
    'kategori': '/kategori-raporu',
    'kohort': '/kohort-analizi',
    'birliktelik': '/urun-birliktelik',
    'sadakat': '/marka-sadakati',
    'enflasyon': '/enflasyon-profil',
    'rakip': '/rakip-riski',
    'hane': '/hane-analizi',
     'ayarlar': '/ayarlar',

     'takvim': '/ai-takvim',
    'panel': '/ai-paneller',
    'briefing': '/',
    'brifing': '/',
    'mba': '/urun-birliktelik',
    'market basket': '/urun-birliktelik',
    'baskın hane': '/hane-analizi',
    'stokçu': '/enflasyon-profil',
};

const SMART_FILTERS: Record<string, string> = {
    'şampiyon': '/musteri-portali?segment=01-)%20Şampiyonlar',
    'sadık': '/musteri-portali?segment=02-)%20Sadık%20Müşteriler',
    'risk': '/musteri-portali?segment=05-)%20Riskli%20Müşteriler',
    'onaylı': '/musteri-portali?approval=onaylı',
    'onaysız': '/musteri-portali?approval=onaysız',
    'bireysel': '/musteri-portali?type=Bireysel',
    'kurumsal': '/musteri-portali?type=Kurumsal',
    'yeni': '/musteri-portali?segment=04-)%20Yeni%20Müşteriler',
    'istanbul': '/musteri-portali?region=İstanbul',
    'ankara': '/musteri-portali?region=Ankara',
    'izmir': '/musteri-portali?region=İzmir',
    'vip': '/musteri-portali?segment=01-)%20Şampiyonlar',
     'kayıp': '/musteri-portali?segment=06-)%20Kaybedilmiş%20Müşteriler',
     'aksiyon': '/kampanya-onerileri',
    'vazgeçen': '/churn-analizi',
    'growth': '/',
};


export const Omnibox = () => {
    const [query, setQuery] = useState('');
    const [isFocused, setIsFocused] = useState(false);
    const navigate = useNavigate();
    const { sendMessage, startNewSession, activeSessionId } = useChatStore();
    const { setChatOpened } = useUIStore();

    useHotkeys([
        ['mod+K', () => {
            const el = document.getElementById('global-omnibox');
            el?.focus();
        }],
    ]);

    const handleSearch = async () => {
        const text = query.trim().toLowerCase();
        if (!text) return;

        setQuery('');
        
        // 1. Navigasyon tespiti (Gelişmiş niyet tespiti)
        const navigationKeywords = ['git', 'aç', 'bak', 'göster', 'götür', 'incele', 'listele', 'neler var'];
        const isNavigationIntent = navigationKeywords.some(kw => text.includes(kw)) || text.length < 15;

        const navigationTarget = Object.entries(ROUTE_MAP).find(([key]) => 
            text.includes(key)
        );

        if (navigationTarget && isNavigationIntent) {
            navigate(navigationTarget[1]);
            setIsFocused(false);
            return;
        }

        // 1.5 Smart Filter Tespiti
        const matchedFilter = Object.entries(SMART_FILTERS).find(([kw]) => text.includes(kw));
        if (matchedFilter && isNavigationIntent) {
            navigate(matchedFilter[1]);
            setIsFocused(false);
            return;
        }

        // 2. Chat araması
        if (setChatOpened) setChatOpened(true);

        // Oturum yoksa yeni oluştur
        if (!activeSessionId) {
            await startNewSession();
        }
        
        await sendMessage(text);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    };

    return (
        <Box style={{ position: 'relative', width: '100%', maxWidth: 400 }}>
            <TextInput
                id="global-omnibox"
                placeholder="Verileri sorgulayın veya işlem yapın..."
                value={query}
                onChange={(e) => setQuery(e.currentTarget.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                radius="xl"
                size="md"
                styles={{
                    input: {
                        backgroundColor: '#f8fafc',
                        border: isFocused ? '1px solid #6366f1' : '1px solid #e2e8f0',
                        paddingLeft: 46,
                        fontSize: '0.9rem',
                        transition: 'all 0.2s ease',
                        boxShadow: isFocused ? '0 0 0 3px rgba(99,102,241,0.1)' : 'none',
                    }
                }}
                leftSection={
                    <IconSparkles 
                        size={20} 
                        color={isFocused ? '#6366f1' : '#94a3b8'} 
                        style={{ transition: 'color 0.2s' }}
                    />
                }
                rightSection={
                    <Group gap={4} pr={8}>
                        {query ? (
                            <ActionIcon 
                                variant="filled" 
                                color="indigo" 
                                radius="xl" 
                                size="sm"
                                onClick={handleSearch}
                            >
                                <IconArrowRight size={14} />
                            </ActionIcon>
                        ) : (
                            <Group gap={4} visibleFrom="sm" style={{ opacity: isFocused ? 0 : 1, transition: 'opacity 0.2s' }}>
                                <Kbd size="xs"><IconCommand size={10} style={{ verticalAlign: 'middle' }} /></Kbd>
                                <Kbd size="xs">K</Kbd>
                            </Group>
                        )}
                    </Group>
                }
            />
            
            <Transition mounted={isFocused} transition="pop-top-left" duration={200}>
                {(styles) => (
                    <Paper 
                        shadow="md" 
                        p="xs" 
                        withBorder 
                        style={{ 
                            ...styles, 
                            position: 'absolute', 
                            top: 48, 
                            left: 0, 
                            right: 0, 
                            zIndex: 1000,
                            borderRadius: 12,
                            background: 'white'
                        }}
                    >
                        <Text size="xs" fw={700} c="dimmed" mb={8} px={8} tt="uppercase">
                            {query ? 'Eşleşen Sayfalar ve Aramalar' : 'Önerilen Sorgular'}
                        </Text>
                        <Stack gap={2}>
                            {(query 
                                ? Object.keys(ROUTE_MAP).filter(key => key.includes(query.toLowerCase())).slice(0, 3) 
                                : [
                                    "şampiyonlar",
                                        "sadık müşteriler",
                                        "onaylı müşteriler",
                                        "riskli müşterileri göster",
                                        "Kampanya önerisi üret"
                                    ]
                            ).map((s, i) => (
                                <UnstyledButton 
                                    key={i} 
                                    onClick={() => { 
                                        setQuery(s); 
                                        if (query) handleSearch();
                                    }}
                                    style={{ 
                                        padding: '8px 12px', 
                                        borderRadius: 8, 
                                        fontSize: '0.85rem',
                                        width: '100%',
                                        textAlign: 'left'
                                    }}
                                    className="omnibox-suggestion"
                                >
                                    <Group gap="xs">
                                        {ROUTE_MAP[s as keyof typeof ROUTE_MAP] ? (
                                            <IconLayoutDashboard size={14} color="#6366f1" />
                                        ) : SMART_FILTERS[s as keyof typeof SMART_FILTERS] ? (
                                            <IconFilter size={14} color="#10b981" />
                                        ) : (
                                            <IconSparkles size={14} color="#f59e0b" />
                                        )}
                                        <Text size="sm">{s}</Text>
                                    </Group>
                                </UnstyledButton>
                            ))}
                        </Stack>
                    </Paper>
                )}
            </Transition>

            <style>{`
                .omnibox-suggestion:hover {
                    background-color: #f1f5f9;
                }
            `}</style>
        </Box>
    );
};
