import { create } from 'zustand'

interface UIState {
  chatOpened: boolean
  setChatOpened: (opened: boolean) => void
}

const useUIStore = create<UIState>((set) => ({
  chatOpened: false,
  setChatOpened: (opened) => set({ chatOpened: opened }),
}))


export default useUIStore
