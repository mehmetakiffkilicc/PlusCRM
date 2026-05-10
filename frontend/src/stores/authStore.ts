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
  user: { id: 'demo-user', email: 'demo@MarketFlow.com' },
  token: 'demo-token',
  isAuthenticated: true,
  login: (user, token) => {
    localStorage.setItem('auth_token', token)
    set({ user, token, isAuthenticated: true })
  },
  logout: () => {
    // Logout disabled in demo mode
    console.log('Logout disabled in demo mode')
  },
  setUser: (user) => set({ user })
}))

export default useAuthStore

