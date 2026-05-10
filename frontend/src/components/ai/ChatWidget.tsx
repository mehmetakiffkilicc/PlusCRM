import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Affix,
  Button,
  Modal,
  Stack,
  ScrollArea,
  TextInput,
  Group,
  Text,
  Box,
  Loader,
  ActionIcon,
  Tooltip,
  Badge,
  Paper,
  Divider,
  Indicator,

} from '@mantine/core';
import {
  IconMessageChatbot,
  IconSend,
  IconPlus,
  IconX,
  IconBrain,
  IconUser,
  IconLayoutDashboard,
  IconExternalLink,
} from '@tabler/icons-react';
import { useChatStore } from '../../stores/chatStore';
import useUIStore from '../../stores/uiStore';
import { ToolCallBadge } from './ToolCallBadge';
import { useNavigate } from 'react-router-dom';

/** Gemini bazen tool call'ları text içinde <tool_code>…</tool_code> olarak yazar.
 *  Bu blokları ve diğer sistem tag'lerini kullanıcıya göstermeden temizler. */
function cleanMessageContent(text: string): string {
  if (!text) return '';
  return text
    // <tool_code>...</tool_code> bloklarını kaldır (çok satırlı)
    .replace(/<tool_code>[\s\S]*?<\/tool_code>/gi, '')
    // <tool_output>...</tool_output> bloklarını kaldır
    .replace(/<tool_output>[\s\S]*?<\/tool_output>/gi, '')
    // Kalan tekil tag'leri kaldır
    .replace(/<\/?tool_code>/gi, '')
    .replace(/<\/?tool_output>/gi, '')
    // Boş satırları fazla biriktirme (3+ satır → 2 satır)
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** BUG-AI-005: UI üzerindeki hassas verileri (PII) maskeler.
 * Hem kullanıcı hem de asistan mesajları için ek güvenlik sağlar. */
function maskPIIContent(text: string): string {
  if (!text) return '';
  return text
    // Kredi Kartı: 13-16 hane arası rakam grupları
    .replace(/\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b/g, ' **** **** **** **** ')
    .replace(/\b\d{4}[ -]?\d{6}[ -]?\d{5}\b/g, ' **** ****** ***** ')
    // TCKN: 11 hane (Türkçe Kimlik No standartına uygun basit denetim)
    .replace(/\b\d{11}\b/g, ' *********** ')
    // Email: Standart e-posta formatı
    .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, ' [EMAIL_MASKED] ')
    // Telefon: +90, 05xx, vb. formatları
    .replace(/(\+90|0)?\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}/g, ' [PHONE_MASKED] ');
}

export const ChatWidget = () => {
  const { chatOpened, setChatOpened } = useUIStore();
  const [inputValue, setInputValue] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const {
    sessions,
    activeSessionId,
    messages,
    isStreaming,
    streamingContent,
    toolCall,
    lastCreatedDashboardId,
    pendingNavigation,
    startNewSession,
    sendMessage,
    loadSession,
    cancelStream,
    clearLastCreatedDashboard,
    clearPendingNavigation,
  } = useChatStore();

  // Custom components for ReactMarkdown to style tables and other elements
  const markdownComponents = {
    table: ({ children }: any) => (
      <div style={{ overflowX: 'auto', margin: '16px 0', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
        {children}
      </thead>
    ),
    th: ({ children }: any) => (
      <th style={{ padding: '12px 10px', textAlign: 'left', fontWeight: 800, color: '#475569' }}>
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td style={{ padding: '10px', borderBottom: '1px solid #f1f5f9', color: '#1e293b', fontWeight: 500 }}>
        {children}
      </td>
    ),
    ul: ({ children }: any) => (
      <ul style={{ paddingLeft: '20px', margin: '8px 0', listStyleType: 'disc' }}>{children}</ul>
    ),
    ol: ({ children }: any) => (
      <ol style={{ paddingLeft: '20px', margin: '8px 0', listStyleType: 'decimal' }}>{children}</ol>
    ),
    li: ({ children }: any) => (
      <li style={{ marginBottom: '4px' }}>{children}</li>
    ),
    p: ({ children }: any) => (
      <p style={{ margin: '8px 0', lineHeight: 1.7 }}>{children}</p>
    ),
    strong: ({ children }: any) => (
      <strong style={{ fontWeight: 800, color: '#4f46e5' }}>{children}</strong>
    )
  };

  // Sub-render logic for message bubble
  const renderMessageContent = (msg: any) => {
    const isAssistant = msg.role === 'assistant';
    const content = isAssistant 
      ? maskPIIContent(cleanMessageContent(msg.content)) 
      : maskPIIContent(msg.content);

    if (isAssistant) {
      return (
        <div className="markdown-body" style={{ 
          fontSize: '14px', 
          color: '#1e293b',
          width: '100%'
        }}>
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]} 
            components={markdownComponents as any}
          >
            {content}
          </ReactMarkdown>
        </div>
      );
    }

    return (
      <Text
        size="md"
        c="white"
        style={{ 
          whiteSpace: 'pre-wrap', 
          lineHeight: 1.7, 
          fontWeight: 600,
          color: 'white' 
        }}
      >
        {content}
      </Text>
    );
  };

  // Yeni mesaj gelince alta kaydır
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, streamingContent]);

  /** BUG-AI-NAV: Otonom Navigasyon. 
   * AI "yönlendiriyorum" dediğinde kullanıcıdan buton onayı beklemeden 
   * 1.5sn sonra otomatik geçiş yapar. */
  useEffect(() => {
    if (!pendingNavigation) return;

    const timer = setTimeout(() => {
      // Eğer hala pendingNavigation varsa yönlendir
      if (pendingNavigation) {
        navigate(pendingNavigation.path);
        clearPendingNavigation();
        setChatOpened(false);
      }
    }, 1500); // 1.5 saniye gecikme

    return () => clearTimeout(timer);
  }, [pendingNavigation, navigate, clearPendingNavigation, setChatOpened]);

  const handleSend = async () => {
    const text = inputValue.trim();
    if (!text || isStreaming) return;
    setInputValue('');

    // Oturum yoksa yeni oluştur
    if (!activeSessionId) {
      try {
        await startNewSession();
      } catch (err) {
        // Oturum oluşturulamadı, mesaj gönderme
        return;
      }
    }
    await sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <Affix position={{ bottom: 20, right: 20 }} zIndex={2200}>
        <Tooltip label="AI Strateji Asistanı" position="left" withArrow>
          <Indicator size={16} offset={5} color="indigo" processing disabled={isStreaming === false}>
            <ActionIcon
              size={60}
              radius="xl"
              variant="filled"
              color="indigo"
              onClick={() => setChatOpened(true)}
              style={{
                boxShadow: '0 10px 25px -5px rgba(79, 70, 229, 0.4), 0 8px 10px -6px rgba(79, 70, 229, 0.4)',
                border: '1px solid rgba(255,255,255,0.1)'
              }}
            >
              <IconMessageChatbot size={32} />
            </ActionIcon>
          </Indicator>
        </Tooltip>
      </Affix>


      {/* Sohbet Popup (Modal) */}
      <Modal
        opened={chatOpened}
        onClose={() => setChatOpened(false)}
        centered
        zIndex={2300}
        title={
          <Group gap="xs">
            <IconBrain size={20} color="#4f46e5" />
            <Text fw={800} size="sm" c="dark.9">AI Strateji Asistanı</Text>
            {isStreaming && <Loader size="xs" color="indigo" />}
          </Group>
        }
        padding="0"
        size="lg"
        radius="lg"
        overlayProps={{
          backgroundOpacity: 0.4,
          blur: 4,
        }}
        styles={{
          header: { 
            borderBottom: '1px solid var(--mantine-color-gray-2)',
            padding: '16px 20px',
            background: '#ffffff',
            color: '#0f172a'
          },
          body: { 
            display: 'flex', 
            flexDirection: 'column', 
            height: '600px', 
            padding: 0,
            background: '#ffffff'
          },
          content: {
            background: '#ffffff',
            border: '1px solid var(--mantine-color-gray-3)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            overflow: 'hidden'
          }
        }}
      >
        {/* data-mantine-color-scheme ile modal içeriğini light mode'a zorluyoruz */}
        <Stack gap={0} style={{ height: '100%', position: 'relative' }} data-mantine-color-scheme="light">
          {/* Üst: Oturum toolbar */}
          <Group px="md" py="xs" justify="space-between" style={{ borderBottom: '1px solid var(--mantine-color-gray-1)', background: '#fcfcfd' }}>
            <Text size="xs" c="gray.6" fw={600} tt="uppercase" lts="0.3px">
              {sessions.length > 0
                ? `${sessions.length} AKTİF OTURUM`
                : 'HENÜZ OTURUM YOK'}
            </Text>
            <Button
              size="xs"
              variant="light"
              color="indigo"
              radius="md"
              leftSection={<IconPlus size={12} />}
              onClick={startNewSession}
              fw={700}
            >
              Yeni Sohbet
            </Button>
          </Group>

          {/* Oturum listesi (kompakt) */}
          {sessions.length > 0 && (
            <ScrollArea style={{ maxHeight: 80, flexShrink: 0 }} px="md" py={8} bg="#fcfcfd">
              <Group gap={6} wrap="wrap">
                {sessions.slice(0, 5).map((s) => (
                  <Badge
                    key={s.id}
                    variant={s.id === activeSessionId ? 'filled' : 'light'}
                    color="indigo"
                    radius="md"
                    style={{ cursor: 'pointer', fontSize: 10, height: 22 }}
                    onClick={() => loadSession(s.id)}
                  >
                    {s.title?.slice(0, 20) || 'Oturum'}
                  </Badge>
                ))}
              </Group>
            </ScrollArea>
          )}

          <Divider color="gray.1" />

          {/* Mesaj alanı */}
          <ScrollArea
            style={{ flex: 1, background: '#ffffff' }}
            viewportRef={scrollRef}
            px="md"
            py="md"
          >
            {messages.length === 0 && !isStreaming ? (
              <Box style={{ textAlign: 'center', paddingTop: 80, paddingBottom: 40 }}>
                <Box mb="xl" style={{ 
                  background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(124, 58, 237, 0.08))',
                  width: 84,
                  height: 84,
                  borderRadius: '28px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto',
                  border: '1px solid rgba(79, 70, 229, 0.15)',
                  boxShadow: '0 12px 24px -6px rgba(79, 70, 229, 0.15)'
                }}>
                  <IconBrain size={44} color="#4f46e5" />
                </Box>
                <Text fw={900} size="xl" mb="xs" c="dark.9" style={{ letterSpacing: '-0.8px' }}>Yapay Zeka Strateji Ortağınız</Text>
                <Text c="gray.8" size="sm" maw={320} mx="auto" style={{ lineHeight: 1.6, fontWeight: 600 }}>
                  Satış verileriniz, müşteri segmentleriniz ve kampanya performansınız hakkında dilediğinizi sorabilirsiniz.
                </Text>
                <Group justify="center" mt="xl" gap="sm">
                  <Badge variant="outline" color="indigo" size="md" radius="md">Churn Tahmini</Badge>
                  <Badge variant="outline" color="blue" size="md" radius="md">RFM Analizi</Badge>
                  <Badge variant="outline" color="violet" size="md" radius="md">Kampanya Önerisi</Badge>
                </Group>
              </Box>
            ) : (
              <Stack gap="xl">
                {messages.map((msg) => (
                  <Box
                    key={msg.id}
                    style={{
                      display: 'flex',
                      justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <Group gap="sm" align="flex-start" style={{ maxWidth: '92%', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                      <Box
                        style={{
                          width: 34,
                          height: 34,
                          borderRadius: '11px',
                          background: msg.role === 'user' ? 'linear-gradient(135deg, #4f46e5, #4338ca)' : '#f8fafc',
                          border: msg.role === 'user' ? 'none' : '1px solid #e2e8f0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          boxShadow: '0 2px 5px rgba(0,0,0,0.06)'
                        }}
                      >
                        {msg.role === 'user'
                          ? <IconUser size={18} color="white" />
                          : <IconBrain size={18} color="#4f46e5" />}
                      </Box>
                      <Paper
                        p="md"
                        radius="lg"
                        style={{
                          background: msg.role === 'user'
                            ? 'linear-gradient(135deg, #4f46e5, #6366f1)'
                            : '#f8fafc',
                          border: '1px solid ' + (msg.role === 'user' ? '#4f46e5' : '#e2e8f0'),
                          boxShadow: '0 4px 12px -2px rgba(0,0,0,0.04)',
                        }}
                      >
                        {renderMessageContent(msg)}
                      </Paper>
                    </Group>
                  </Box>
                ))}

                {/* Streaming mesajı veya Hata Gösterimi */}
                {isStreaming && (
                  <Box style={{ display: 'flex', justifyContent: 'flex-start' }}>
                    <Group gap="sm" align="flex-start" style={{ maxWidth: '92%' }}>
                      <Box
                        style={{
                          width: 34,
                          height: 34,
                          borderRadius: '11px',
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <IconBrain size={18} color="#4f46e5" />
                      </Box>
                      <Stack gap="xs" style={{ flex: 1, maxWidth: '100%' }}>
                        {toolCall && <ToolCallBadge {...toolCall} />}
                        <Paper
                          p="md"
                          radius="lg"
                          style={{
                            background: '#f8fafc',
                            border: '1px solid #e2e8f0',
                            minWidth: 100,
                            boxShadow: '0 4px 12px -2px rgba(0,0,0,0.04)',
                          }}
                        >
                          {streamingContent ? (
                            <div className="markdown-body" style={{ 
                              fontSize: '14px', 
                              color: '#1e293b',
                              width: '100%',
                              fontWeight: 500
                            }}>
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm]} 
                                components={markdownComponents as any}
                              >
                                {maskPIIContent(cleanMessageContent(streamingContent))}
                              </ReactMarkdown>
                               {(toolCall?.status === 'start' || toolCall?.status === 'running') ? (
                                 <Group gap={6} display="inline-flex" style={{ verticalAlign: 'middle', marginTop: '8px' }}>
                                   <Loader size={12} color="indigo" type="dots" />
                                   <Text size="xs" c="indigo.9" fw={700} style={{ fontStyle: 'italic' }}>
                                      Veriler analiz ediliyor...
                                   </Text>
                                 </Group>
                               ) : (
                                 <span style={{ 
                                   display: 'inline-block',
                                   width: '2px',
                                   height: '1.2em',
                                   background: '#4f46e5',
                                   marginLeft: '2px',
                                   verticalAlign: 'middle',
                                   animation: 'blink 1s infinite'
                                 }} />
                               )}
                            </div>
                          ) : (
                            <Group gap="xs">
                                <Loader size="xs" color="indigo" type="dots" />
                                <Text size="xs" c="dimmed" fw={600}>Strateji hazırlanıyor...</Text>
                            </Group>
                          )}
                        </Paper>
                      </Stack>
                    </Group>
                  </Box>
                )}
              </Stack>
            )}
          </ScrollArea>

          <Divider color="gray.1" />

          {/* Dinamik Panel Oluşturuldu Bildirimi */}
          {lastCreatedDashboardId && (
            <Paper
              px="md"
              py="sm"
              style={{
                background: 'linear-gradient(135deg, #f0f9ff, #e0f2fe)',
                borderTop: '1px solid #7dd3fc',
                borderBottom: '1px solid #7dd3fc',
                borderRadius: 0,
                flexShrink: 0,
              }}
            >
              <Group justify="space-between" align="center">
                <Group gap="xs">
                  <IconLayoutDashboard size={18} color="#0369a1" />
                  <Text size="xs" fw={800} c="blue.9">Özel analiz paneli hazır!</Text>
                </Group>
                <Group gap={6}>
                  <Button
                    size="xs"
                    variant="filled"
                    color="blue"
                    radius="md"
                    rightSection={<IconExternalLink size={12} />}
                    onClick={() => {
                      navigate(`/ai-paneller/${lastCreatedDashboardId}`);
                      clearLastCreatedDashboard();
                      setChatOpened(false);
                    }}
                  >
                    Görüntüle
                  </Button>
                  <ActionIcon size="sm" variant="subtle" color="gray" onClick={clearLastCreatedDashboard} radius="md">
                    <IconX size={14} />
                  </ActionIcon>
                </Group>
              </Group>
            </Paper>
          )}

          {/* Navigasyon Bildirimi */}
          {pendingNavigation && (
            <Paper
              px="md"
              py="sm"
              style={{
                background: 'linear-gradient(135deg, #f5f3ff, #ede9fe)',
                borderTop: '1px solid #c4b5fd',
                borderBottom: '1px solid #c4b5fd',
                borderRadius: 0,
                flexShrink: 0,
              }}
            >
              <Group justify="space-between" align="center">
                <Group gap="xs">
                  <IconExternalLink size={18} color="#5b21b6" />
                  <Text size="xs" fw={800} c="violet.9">Hemen yönlendirebilirim:</Text>
                  <Badge color="violet" variant="filled" size="sm">{pendingNavigation.label}</Badge>
                </Group>
                <Group gap={6}>
                  <Button
                    size="xs"
                    variant="filled"
                    color="violet"
                    radius="md"
                    onClick={() => {
                      navigate(pendingNavigation.path);
                      clearPendingNavigation();
                      setChatOpened(false);
                    }}
                  >
                    Sayfaya Git
                  </Button>
                  <ActionIcon size="sm" variant="subtle" color="gray" onClick={clearPendingNavigation} radius="md">
                    <IconX size={14} />
                  </ActionIcon>
                </Group>
              </Group>
            </Paper>
          )}

          {/* Input alanı */}
          <Box px="md" py="md" style={{ flexShrink: 0, background: '#ffffff', borderTop: '1px solid #f1f5f9' }}>
            {isStreaming && (
              <Button
                size="xs"
                variant="subtle"
                color="red"
                leftSection={<IconX size={12} />}
                onClick={cancelStream}
                mb="xs"
                fullWidth
                radius="md"
              >
                Analizi Durdur
              </Button>
            )}
            <Group gap="xs">
              <TextInput
                placeholder="Verileriniz hakkında bir soru sorun..."
                value={inputValue}
                onChange={(e) => setInputValue(e.currentTarget.value)}
                onKeyDown={handleKeyDown}
                disabled={isStreaming}
                style={{ flex: 1 }}
                radius="xl"
                size="md"
                styles={{
                  input: {
                    backgroundColor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    color: '#0f172a',
                    fontWeight: 600,
                    paddingRight: '45px',
                    '::placeholder': { color: '#64748b' }
                  }
                }}
                rightSection={
                  isStreaming
                    ? <Loader size="xs" color="indigo" />
                    : (
                      <ActionIcon
                        variant="filled"
                        color="indigo"
                        radius="xl"
                        size="md"
                        onClick={handleSend}
                        disabled={!inputValue.trim()}
                        style={{ marginRight: '8px' }}
                      >
                        <IconSend size={16} />
                      </ActionIcon>
                    )
                }
              />
            </Group>
            <Text size="10px" c="gray.8" mt={8} ta="center" fw={700}>
               Asistan verileri analiz ederken hata yapabilir. Lütfen önemli verileri kontrol edin.
            </Text>
          </Box>
        </Stack>
      </Modal>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>

    </>
  );
};
