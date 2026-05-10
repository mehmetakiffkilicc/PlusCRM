import React from 'react';
import { Button, Loader } from '@mantine/core';
import { IconBrain } from '@tabler/icons-react';
import { useChatStore } from '../../stores/chatStore';
import useUIStore from '../../stores/uiStore';

interface AISummaryButtonProps {
  onClick?: () => void;
  contextType?: string;
  contextId?: string | number;
  variant?: string;
  label?: string;
  /** Bağlamsal veri — LLM'e context olarak gönderilir */
  contextData?: object;
}

export const AISummaryButton = ({
  onClick,
  contextType,
  contextId,
  variant = 'light',
  label = 'AI ile Yorumla',
  contextData,
}: AISummaryButtonProps) => {
  const { sendMessage, startNewSession, activeSessionId, isStreaming, attachPageContext } = useChatStore();
  const { setChatOpened } = useUIStore();

  const handleClick = async () => {
    if (onClick) {
      onClick();
      return;
    }

    // 1. Context yükle
    if (contextType) {
      attachPageContext(contextType, {
        context_type: contextType,
        context_id: contextId,
        ...(contextData || {}),
      });
    }

    // 2. Ana asistanı aç
    setChatOpened(true);

    // 3. Oturum yoksa yeni oluştur
    if (!activeSessionId) {
      await startNewSession();
    }

    // 4. Otomatik mesaj gönder
    const autoPrompt = contextType
      ? `${contextType} sayfasındaki verileri analiz et ve kısa bir yorum yap.${contextId ? ` (ID: ${contextId})` : ''}`
      : 'Bu sayfadaki verileri analiz edip önemli bulgular hakkında yorum yap.';

    await sendMessage(autoPrompt);
  };

  return (
    <Button
      leftSection={
        isStreaming
          ? <Loader size={14} color="white" />
          : <IconBrain size={16} />
      }
      variant={variant as any}
      color="indigo"
      onClick={handleClick}
      disabled={isStreaming}
      style={{
        background: variant === 'filled'
          ? 'linear-gradient(135deg, #4f46e5, #2563eb)'
          : undefined,
      }}
    >
      {isStreaming ? 'Analiz ediliyor...' : label}
    </Button>
  );
};
