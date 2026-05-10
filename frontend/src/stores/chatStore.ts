import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { notifications } from '@mantine/notifications';
import { aiClient } from '../api/aiClient';
import apiClient from '../api/client';

type AISession = {
  id: string;
  title: string;
  model: string;
  created_at: string;
};

type AIMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_calls: any[];
  created_at: string;
};

interface ChatStore {
  sessions: AISession[];
  activeSessionId: string | null;
  messages: AIMessage[];
  isStreaming: boolean;
  streamingContent: string;
  toolCall: { name: string; status: 'start' | 'running' | 'result'; result?: any } | null;
  pageContext: { pageName: string; payload: object } | null;
  cancelFn: (() => void) | null;
  lastCreatedDashboardId: number | null;
  pendingNavigation: { path: string; label: string } | null;

  startNewSession: () => Promise<void>;
  sendMessage: (text: string, contextRef?: object) => Promise<void>;
  loadSession: (id: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  cancelStream: () => void;
  attachPageContext: (pageName: string, payload: object) => void;
  clearLastCreatedDashboard: () => void;
  clearPendingNavigation: () => void;
  usageStats: {
    today_queries: number;
    query_limit: number;
    monthly_tokens: number;
    token_limit: number;
    active_model: string;
    fallback_active: boolean;
  } | null;
  fetchUsageStats: () => Promise<void>;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeSessionId: null,
      messages: [],
      isStreaming: false,
      streamingContent: '',
      toolCall: null,
      pageContext: null,
      cancelFn: null,
      lastCreatedDashboardId: null,
      pendingNavigation: null,
      usageStats: null,

      fetchUsageStats: async () => {
        try {
          const data = await apiClient.getAIUsageStats();
          set({ usageStats: data });
        } catch (err) {
          console.error('Kullanım istatistikleri çekilemedi:', err);
        }
      },

       startNewSession: async () => {
         try {
           const data = await aiClient.createNewSession();
           if (!data?.id) {
             throw new Error('Oturum ID alınamadı');
           }
           const newSession: AISession = {
             id: data.id,
             title: data.title || 'Yeni Sohbet',
             model: '',
             created_at: new Date().toISOString(),
           };
           set((state) => ({
             sessions: [newSession, ...state.sessions],
             activeSessionId: data.id,
             messages: [],
             streamingContent: '',
             toolCall: null,
           }));
           return data.id;
         } catch (err: any) {
           console.error('Yeni oturum oluşturulamadı:', err);
           notifications.show({
             title: 'Bağlantı Hatası',
             message: 'AI servisi şu an başlatılamıyor. Lütfen API anahtarlarını kontrol edin veya daha sonra tekrar deneyin.',
             color: 'red'
           });
           throw err;
         }
       },

       sendMessage: async (text: string, contextRef?: object) => {
         const { activeSessionId, pageContext, cancelFn: existingCancel } = get();

         // Mevcut stream varsa iptal et
         if (existingCancel) existingCancel();

         // Session ID kontrolü
         if (!activeSessionId) {
           const errorMsg: AIMessage = {
             id: `err-${Date.now()}`,
             role: 'assistant',
             content: '⚠️ Aktif oturum bulunamadı. Lütfen yeni bir sohbet başlatın.',
             tool_calls: [],
             created_at: new Date().toISOString(),
           };
           set((state) => ({
             messages: [...state.messages, errorMsg],
           }));
           return;
         }

         const context = contextRef || pageContext?.payload || {};

         // Kullanıcı mesajını hemen göster
         const userMsg: AIMessage = {
           id: `temp-${Date.now()}`,
           role: 'user',
           content: text,
           tool_calls: [],
           created_at: new Date().toISOString(),
         };

         set((state) => ({
           messages: [...state.messages, userMsg],
           isStreaming: true,
           streamingContent: '',
           toolCall: null,
         }));

         const cancel = aiClient.streamChat(
           activeSessionId,
           text,
           context,
           // onToken
           (token: string) => {
             set((state) => ({
               streamingContent: state.streamingContent + token,
             }));
           },
           // onError
           (err: any) => {
             console.error('Stream hatası:', err);
             const errorMsg: AIMessage = {
               id: `err-${Date.now()}`,
               role: 'assistant',
               content: `⚠️ Bir hata oluştu: ${err.message || 'Bilinmeyen hata'}. Lütfen bağlantınızı veya API yapılandırmanızı kontrol edin.`,
               tool_calls: [],
               created_at: new Date().toISOString(),
             };
             set((state) => ({
               messages: [...state.messages, errorMsg],
               isStreaming: false, 
               cancelFn: null, 
               toolCall: null 
             }));
           },
           // onFinish
           () => {
             const { streamingContent, toolCall } = get();
             const content = streamingContent?.trim();
             set((state) => ({
               messages: content
                 ? [...state.messages, {
                     id: `resp-${Date.now()}`,
                     role: 'assistant' as const,
                     content,
                     tool_calls: toolCall ? [{ name: toolCall.name, result: toolCall.result }] : [],
                     created_at: new Date().toISOString(),
                   }]
                 : [...state.messages, {
                     id: `resp-${Date.now()}`,
                     role: 'assistant' as const,
                     content: 'Yanıt alınamadı. Lütfen tekrar deneyin.',
                     tool_calls: [],
                     created_at: new Date().toISOString(),
                   }],
               isStreaming: false,
               streamingContent: '',
               toolCall: null,
               cancelFn: null,
             }));
           },
           // onTool
           (type, data) => {
             if (type === 'start') {
               set({ toolCall: { name: data, status: 'start' } });
             } else if (type === 'running') {
               set({ toolCall: { name: data, status: 'running' } });
             } else if (type === 'result') {
               set({ toolCall: { name: data.tool, status: 'result', result: data.result } });
               // Dinamik dashboard oluşturulduğunda ID'yi yakala
               if (data.tool === 'create_dynamic_dashboard') {
                 try {
                   const parsed = typeof data.result === 'string' ? JSON.parse(data.result) : data.result;
                   if (parsed?.status === 'success' && parsed?.id) {
                     set({ lastCreatedDashboardId: parsed.id });
                   }
                 } catch {}
               }

               // Navigasyon isteği yakala
               if (data.tool === 'navigate_to_page') {
                 try {
                   const parsed = typeof data.result === 'string' ? JSON.parse(data.result) : data.result;
                   if (parsed?.status === 'success' && parsed?.path) {
                     set({ pendingNavigation: { path: parsed.path, label: parsed.label || parsed.path } });
                   }
                 } catch {}
               }
             }
           }
         );

         set({ cancelFn: cancel || null });
       },

      loadSession: async (id: string) => {
        try {
          const data = await aiClient.getSessionHistory(id);
          set({
            activeSessionId: id,
            messages: (data?.messages || []).map((m: any) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              tool_calls: m.tool_calls || [],
              created_at: m.created_at || '',
            })),
            streamingContent: '',
            toolCall: null,
          });
        } catch (err) {
          console.error('Oturum yüklenemedi:', err);
          notifications.show({
            title: 'Hata',
            message: 'Sohbet geçmişi yüklenirken bir sorun oluştu.',
            color: 'red'
          });
        }
      },

      deleteSession: async (id: string) => {
        try {
          const token = localStorage.getItem('auth_token');
          const headers: Record<string, string> = { 'Content-Type': 'application/json' };
          if (token) headers['Authorization'] = `Bearer ${token}`;

          let url = import.meta.env.VITE_API_URL || '/api';
          if (!url.endsWith('/api')) url = url.endsWith('/') ? url + 'api' : url + '/api';

          await fetch(`${url}/ai/sohbet/${id}/`, { method: 'DELETE', headers });

          set((state) => ({
            sessions: state.sessions.filter((s) => s.id !== id),
            activeSessionId: state.activeSessionId === id ? null : state.activeSessionId,
            messages: state.activeSessionId === id ? [] : state.messages,
          }));
        } catch (err) {
          console.error('Oturum silinemedi:', err);
        }
      },

      cancelStream: () => {
        const { cancelFn } = get();
        if (cancelFn) cancelFn();
        set({ isStreaming: false, cancelFn: null, streamingContent: '' });
      },

      attachPageContext: (pageName: string, payload: object) => {
        set({ pageContext: { pageName, payload } });
      },

      clearLastCreatedDashboard: () => {
        set({ lastCreatedDashboardId: null });
      },

      clearPendingNavigation: () => {
        set({ pendingNavigation: null });
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
      }),
    }
  )
);
