import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface FilterState {
  search?: string
  startDate?: string
  endDate?: string
  minAmount?: number
  maxAmount?: number
  status?: string[]
  paymentMethod?: string[]
  year?: number
  month?: number // 1-12
  customerType?: 'Bireysel' | 'Kurumsal'
  approvalStatus?: 'Onaylı' | 'Onaysız'
  region?: string
}

interface DataSource {
  id: string
  name: string
  type: string
}

interface DashboardStore {
  // Global Selection
  selectedDataSourceId: string
  dataSources: DataSource[]

  // Date Filters
  selectedYear: number | undefined
  selectedMonth: number | undefined
  selectedStartDate: string | undefined
  selectedEndDate: string | undefined
  availableYears: number[]
  availableMonths: number[]
  availableCustomerTypes: string[]
  availableApprovalStatuses: string[]
  availableRegions: string[]

  // Product/Segment Filters
  selectedSegments: string[]
  selectedCategories: string[]
  selectedBrands: string[]

  // Advanced Filters
  selectedCustomerType: 'Bireysel' | 'Kurumsal' | undefined
  selectedApprovalStatus: 'Onaylı' | 'Onaysız' | undefined
  selectedRegion: string | undefined

  // UI Actions
  returnTo: { path: string; filters?: any } | null
  setSelectedDataSourceId: (id: string) => void
  setDataSources: (sources: DataSource[]) => void
  setSelectedYear: (year: number | undefined) => void
  setSelectedMonth: (month: number | undefined) => void
  setDateRange: (start: string | undefined, end: string | undefined) => void
  setAvailableYears: (years: number[]) => void
  setAvailableMonths: (months: number[]) => void
  setAvailableCustomerTypes: (types: string[]) => void
  setAvailableApprovalStatuses: (statuses: string[]) => void
  setAvailableRegions: (regions: string[]) => void

  setSelectedSegments: (segments: string[]) => void
  setSelectedCategories: (categories: string[]) => void
  setSelectedBrands: (brands: string[]) => void

  setSelectedCustomerType: (type: 'Bireysel' | 'Kurumsal' | undefined) => void
  setSelectedApprovalStatus: (status: 'Onaylı' | 'Onaysız' | undefined) => void
  setSelectedRegion: (region: string | undefined) => void

  setReturnTo: (path: string, filters?: any) => void
  clearReturnTo: () => void
  // Reset
  resetFilters: () => void
}

const useDashboardStore = create<DashboardStore>()(
  persist(
    (set) => ({
  selectedDataSourceId: '',
  dataSources: [],

  selectedYear: undefined,
  selectedMonth: undefined,
  selectedStartDate: undefined,
  selectedEndDate: undefined,
  availableYears: [],
  availableMonths: [],
  availableCustomerTypes: [],
  availableApprovalStatuses: [],
  availableRegions: [],

  selectedSegments: [],
  selectedCategories: [],
  selectedBrands: [],

  selectedCustomerType: undefined,
  selectedApprovalStatus: undefined,
  selectedRegion: undefined,

  returnTo: null,

  setSelectedDataSourceId: (id) => set({ selectedDataSourceId: id }),
  setDataSources: (sources) => set({ dataSources: sources }),

  setSelectedYear: (year) => set({ selectedYear: year }),
  setSelectedMonth: (month) => set({ selectedMonth: month }),
  setDateRange: (start, end) => set({ selectedStartDate: start, selectedEndDate: end }),
  setAvailableYears: (years) => set({ availableYears: years }),
  setAvailableMonths: (months) => set({ availableMonths: months }),
  setAvailableCustomerTypes: (types) => set({ availableCustomerTypes: types }),
  setAvailableApprovalStatuses: (statuses) => set({ availableApprovalStatuses: statuses }),
  setAvailableRegions: (regions) => set({ availableRegions: regions }),

  setSelectedSegments: (segments) => set({ selectedSegments: segments }),
  setSelectedCategories: (categories) => set({ selectedCategories: categories }),
  setSelectedBrands: (brands) => set({ selectedBrands: brands }),

  setSelectedCustomerType: (type) => set({ selectedCustomerType: type }),
  setSelectedApprovalStatus: (status) => set({ selectedApprovalStatus: status }),
  setSelectedRegion: (region) => set({ selectedRegion: region }),

  setReturnTo: (path, filters) => set({ returnTo: { path, filters } }),
  clearReturnTo: () => set({ returnTo: null }),

  resetFilters: () => set({
    selectedYear: undefined,
    selectedMonth: undefined,
    selectedStartDate: undefined,
    selectedEndDate: undefined,
    selectedSegments: [],
    selectedCategories: [],
    selectedBrands: [],
    selectedCustomerType: undefined,
    selectedApprovalStatus: undefined,
    selectedRegion: undefined
  })
}),
    {
      name: 'dashboard-storage',
      partialize: (state) => ({
        selectedDataSourceId: state.selectedDataSourceId,
        selectedYear: state.selectedYear,
        selectedMonth: state.selectedMonth,
        selectedStartDate: state.selectedStartDate,
        selectedEndDate: state.selectedEndDate,
        selectedSegments: state.selectedSegments,
        selectedCategories: state.selectedCategories,
        selectedBrands: state.selectedBrands,
        selectedCustomerType: state.selectedCustomerType,
        selectedApprovalStatus: state.selectedApprovalStatus,
        selectedRegion: state.selectedRegion,
      }),
    }
  )
)

export default useDashboardStore
