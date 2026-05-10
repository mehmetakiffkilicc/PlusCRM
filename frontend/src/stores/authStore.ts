import { create } from 'zustand'

interface User {
  id: string
  email: string
}

interface AuthStore {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (user: User, token: string) => void
  logout: () => void
  setUser: (user: User) => void
}

const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: localStorage.getItem('auth_token'),
  isAuthenticated: !!localStorage.getItem('auth_token'),
  login: (user, token) => {
    localStorage.setItem('auth_token', token)
    set({ user, token, isAuthenticated: true })
  },
  logout: () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('chat-storage')
    localStorage.removeItem('dashboard-storage')
    localStorage.removeItem('notification-storage')
    set({ user: null, token: null, isAuthenticated: false })
  },
  setUser: (user) => set({ user })
}))

export default useAuthStore
