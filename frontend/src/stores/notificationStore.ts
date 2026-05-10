import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import apiClient from '../api/client'

export interface AINotification {
  id: number
  title: string
  message: string
  type: 'info' | 'warning' | 'success' | 'critical'
  is_read: boolean
  metadata: any
  created_at: string
}

interface NotificationStore {
  notifications: AINotification[]
  loading: boolean
  unreadCount: number
  fetchNotifications: () => Promise<void>
  syncNotifications: (dataSourceId?: number) => Promise<void>
  markAsRead: (id: number) => Promise<void>
  clearAll: () => void
}

const useNotificationStore = create<NotificationStore>()(
  persist(
    (set, get) => ({
      notifications: [],
      loading: false,
      unreadCount: 0,

      fetchNotifications: async () => {
        set({ loading: true })
        try {
          const response = await apiClient.get('/ai/bildirimler/')
          const notifications = response.data.notifications || []
          const unreadCount = notifications.filter((n: AINotification) => !n.is_read).length
          set({ notifications, unreadCount, loading: false })
        } catch (error) {
          console.error('Bildirimler yüklenemedi:', error)
          set({ loading: false })
        }
      },

      syncNotifications: async (dataSourceId = 0) => {
        set({ loading: true })
        try {
          // Önce backend'de anomali taraması yapıp bildirim oluştur
          await apiClient.post('/ai/bildirimler/sync/', { data_source_id: dataSourceId })
          // Sonra güncel listeyi çek
          await get().fetchNotifications()
        } catch (error) {
          console.error('Bildirim senkronizasyon hatası:', error)
          set({ loading: false })
        }
      },

      markAsRead: async (id: number) => {
        try {
          await apiClient.post(`/ai/bildirimler/${id}/okundu/`)
          const notifications = get().notifications.map(n => 
            n.id === id ? { ...n, is_read: true } : n
          )
          const unreadCount = notifications.filter(n => !n.is_read).length
          set({ notifications, unreadCount })
        } catch (error) {
          console.error('Bildirim okundu işaretlenemedi:', error)
        }
      },

      clearAll: () => {
        set({ notifications: [], unreadCount: 0 })
      }
    }),
    {
      name: 'notification-storage',
      partialize: (state) => ({ unreadCount: state.unreadCount }),
    }
  )
)

export default useNotificationStore
