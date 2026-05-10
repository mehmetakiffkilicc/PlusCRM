import { useState, useEffect, useMemo, memo } from 'react'
import {
  IconChevronLeft, IconX, IconUser, IconShieldCheck,
  IconMapPin, IconCalendarMonth, IconCalendar,
  IconArrowRight, IconCircleCheck
} from '@tabler/icons-react'

interface FilterPanelProps {
  availableYears?: number[]
  availableMonths?: number[]
  segments?: string[]
  categories?: string[]
  brands?: string[]
  resetKey?: string | number
  onFilterChange: (filters: FilterState) => void
  showYearFilter?: boolean
  showMonthFilter?: boolean
  showSegmentFilter?: boolean
  showCategoryFilter?: boolean
  showBrandFilter?: boolean
  showDateRangeFilter?: boolean
  initialFilters?: FilterState
  showCustomerTypeFilter?: boolean
  showApprovalStatusFilter?: boolean
  showRegionFilter?: boolean
  showApplyButton?: boolean
  availableCustomerTypes?: string[]
  availableApprovalStatuses?: string[]
  availableRegions?: string[]
}

export interface FilterState {
  year?: number
  month?: number
  segments?: string[]
  categories?: string[]
  brands?: string[]
  startDate?: string
  endDate?: string
  customerType?: 'Bireysel' | 'Kurumsal'
  approvalStatus?: 'Onaylı' | 'Onaysız'
  region?: string
}

function FilterPanel({
  availableYears = [],
  availableMonths = [],
  segments = [],
  categories = [],
  brands = [],
  resetKey,
  onFilterChange,
  showYearFilter = true,
  showMonthFilter = true,
  showSegmentFilter = false,
  showCategoryFilter = false,
  showBrandFilter = false,
  showDateRangeFilter = false,
  showCustomerTypeFilter = false,
  showApprovalStatusFilter = false,
  showRegionFilter = false,
  showApplyButton = false,
  initialFilters = {},
  availableCustomerTypes = [],
  availableApprovalStatuses = [],
  availableRegions = []
}: FilterPanelProps) {
  const displayCustomerTypes = availableCustomerTypes
  const displayApprovalStatuses = availableApprovalStatuses
  const displayRegions = availableRegions

  const normalizeFilters = (input: FilterState) => {
    const normalized: FilterState = {}
    if (input.year) normalized.year = input.year
    if (input.month) normalized.month = input.month
    if (input.startDate) normalized.startDate = input.startDate
    if (input.endDate) normalized.endDate = input.endDate
    if (input.customerType) normalized.customerType = input.customerType
    if (input.approvalStatus) normalized.approvalStatus = input.approvalStatus
    if (input.region) normalized.region = input.region

    if (input.segments && input.segments.length) normalized.segments = [...input.segments].sort()
    if (input.categories && input.categories.length) normalized.categories = [...input.categories].sort()
    if (input.brands && input.brands.length) normalized.brands = [...input.brands].sort()

    return normalized
  }

  const [filters, setFilters] = useState<FilterState>(() => normalizeFilters(initialFilters))
  const [committedFilters, setCommittedFilters] = useState<FilterState>(() => normalizeFilters(initialFilters))
  const [showYearDropdown, setShowYearDropdown] = useState(false)
  const [showMonthDropdown, setShowMonthDropdown] = useState(false)
  const [showSegmentDropdown, setShowSegmentDropdown] = useState(false)
  const [showCustomerTypeDropdown, setShowCustomerTypeDropdown] = useState(false)
  const [showApprovalStatusDropdown, setShowApprovalStatusDropdown] = useState(false)
  const [showRegionDropdown, setShowRegionDropdown] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)

  const isDirty = useMemo(() => {
    if (!showApplyButton) return false
    const normalizedFilters = normalizeFilters(filters)
    const normalizedCommitted = normalizeFilters(committedFilters)
    return JSON.stringify(normalizedFilters) !== JSON.stringify(normalizedCommitted)
  }, [filters, committedFilters, showApplyButton])

  const monthNames = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 
                     'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

  const currentYear = new Date().getFullYear()
  const defaultYears = availableYears
  const defaultMonths = availableMonths.length > 0 ? availableMonths : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

  const updateFilters = (newFilters: FilterState) => {
    const normalizedNew = normalizeFilters(newFilters)
    const normalizedOld = normalizeFilters(filters)
    if (JSON.stringify(normalizedNew) === JSON.stringify(normalizedOld)) return
    setFilters(normalizedNew)
    if (!showApplyButton) onFilterChange(normalizedNew)
  }

  const handleApply = () => {
    const normalized = normalizeFilters(filters)
    setCommittedFilters(normalized)
    onFilterChange(normalized)
  }

  // Prop senkronizasyonu: Dışarıdan gelen initialFilters değişikliklerini takip et
  useEffect(() => {
    const normalizedInitial = normalizeFilters(initialFilters)
    
    // Eğer dışarıdan gelen (prop) filtreler bizim son uyguladığımızdan farklıysa senkronize et
    if (JSON.stringify(normalizedInitial) !== JSON.stringify(committedFilters)) {
      setFilters(normalizedInitial)
      setCommittedFilters(normalizedInitial)
      // Dropdown'ları kapat
      setShowYearDropdown(false)
      setShowMonthDropdown(false)
      setShowSegmentDropdown(false)
      setShowCustomerTypeDropdown(false)
      setShowApprovalStatusDropdown(false)
      setShowRegionDropdown(false)
    }
  }, [initialFilters, resetKey])

  return (
    <div style={{
      display: 'flex',
      gap: '8px',
      padding: '8px 12px',
      background: 'white',
      borderRadius: '12px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      flexWrap: 'nowrap',
      alignItems: 'center',
      position: 'relative',
      zIndex: 1001
    }}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        title={isExpanded ? "Filtreleri Gizle" : "Filtreleri Göster"}
        style={{
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          color: '#6b7280',
          padding: '4px',
          display: 'flex',
          alignItems: 'center',
          transition: 'transform 0.3s'
        }}
      >
        <IconChevronLeft size={18} stroke={2} style={{ transition: 'transform 0.3s', transform: isExpanded ? 'rotate(0deg)' : 'rotate(180deg)' }} />
      </button>

      {isExpanded && (
        <>
      {/* Reset Filters */}
      {(isDirty || filters.year || filters.month || filters.startDate || filters.endDate ||
        filters.customerType || filters.approvalStatus || filters.region ||
        (filters.segments && filters.segments.length > 0) ||
        (filters.categories && filters.categories.length > 0) ||
        (filters.brands && filters.brands.length > 0)) && (
        <button
          onClick={() => {
            setShowYearDropdown(false)
            setShowMonthDropdown(false)
            setShowSegmentDropdown(false)
            setShowCustomerTypeDropdown(false)
            setShowApprovalStatusDropdown(false)
            setShowRegionDropdown(false)
            updateFilters({})
          }}
          title="Filtreleri Temizle"
          style={{
            padding: '8px',
            width: '34px',
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            background: 'white',
            color: '#ef4444',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: 600
          }}
        >
          <IconX size={16} stroke={2.5} />
        </button>
      )}

      {/* Customer Type Filter */}
      {showCustomerTypeFilter && (
        <div style={{ position: 'relative', zIndex: showCustomerTypeDropdown ? 9999 : 1 }}>
          <button
            onClick={() => {
              setShowCustomerTypeDropdown(!showCustomerTypeDropdown)
              setShowYearDropdown(false)
              setShowMonthDropdown(false)
              setShowApprovalStatusDropdown(false)
              setShowRegionDropdown(false)
            }}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              background: filters.customerType ? '#6366f1' : 'white',
              color: filters.customerType ? 'white' : '#374151',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500
            }}
          >
             <IconUser size={15} stroke={1.8} style={{ marginRight: 4 }} /> {filters.customerType || 'Müşteri Tipi'}
          </button>
          {showCustomerTypeDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              zIndex: 9999,
              minWidth: '150px'
            }}>
              <div
                  onClick={() => {
                    updateFilters({ ...filters, customerType: undefined })
                    setShowCustomerTypeDropdown(false)
                  }}
                style={{
                  padding: '10px 16px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  background: !filters.customerType ? '#f3f4f6' : 'white'
                }}
              >
                Tümü
              </div>
              {displayCustomerTypes.map(type => (
                <div
                  key={type}
                  onClick={() => {
                    // Type unsafe cast for now as backend might return anything, but we expect specific known strings mostly
                    updateFilters({ ...filters, customerType: type as any })
                    setShowCustomerTypeDropdown(false)
                  }}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    background: filters.customerType === type ? '#f3f4f6' : 'white'
                  }}
                >
                  {type}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Approval Status Filter */}
      {showApprovalStatusFilter && (
        <div style={{ position: 'relative', zIndex: showApprovalStatusDropdown ? 9999 : 1 }}>
          <button
            onClick={() => {
              setShowApprovalStatusDropdown(!showApprovalStatusDropdown)
              setShowCustomerTypeDropdown(false)
              setShowYearDropdown(false)
              setShowMonthDropdown(false)
              setShowRegionDropdown(false)
            }}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              background: filters.approvalStatus ? '#6366f1' : 'white',
              color: filters.approvalStatus ? 'white' : '#374151',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500
            }}
          >
             <IconShieldCheck size={15} stroke={1.8} style={{ marginRight: 4 }} /> {filters.approvalStatus || 'Onay Durumu'}
          </button>
          {showApprovalStatusDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              zIndex: 9999,
              minWidth: '150px'
            }}>
              <div
                  onClick={() => {
                    updateFilters({ ...filters, approvalStatus: undefined })
                    setShowApprovalStatusDropdown(false)
                  }}
                style={{
                  padding: '10px 16px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  background: !filters.approvalStatus ? '#f3f4f6' : 'white'
                }}
              >
                Tümü
              </div>
              {displayApprovalStatuses.map(status => (
                <div
                  key={status}
                  onClick={() => {
                    updateFilters({ ...filters, approvalStatus: status as any })
                    setShowApprovalStatusDropdown(false)
                  }}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    background: filters.approvalStatus === status ? '#f3f4f6' : 'white'
                  }}
                >
                  {status}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Region Filter */}
      {showRegionFilter && (
        <div style={{ position: 'relative', zIndex: showRegionDropdown ? 9999 : 1 }}>
          <button
            onClick={() => {
              setShowRegionDropdown(!showRegionDropdown)
              setShowApprovalStatusDropdown(false)
              setShowCustomerTypeDropdown(false)
              setShowYearDropdown(false)
              setShowMonthDropdown(false)
            }}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              background: filters.region ? '#6366f1' : 'white',
              color: filters.region ? 'white' : '#374151',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500
            }}
          >
            <IconMapPin size={15} stroke={1.8} style={{ marginRight: 4 }} /> {filters.region || 'Bölge'}
          </button>
          {showRegionDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              zIndex: 9999,
              minWidth: '150px',
              maxHeight: '300px', 
              overflowY: 'auto'
            }}>
              <div
                  onClick={() => {
                    updateFilters({ ...filters, region: undefined })
                    setShowRegionDropdown(false)
                  }}
                style={{
                  padding: '10px 16px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  background: !filters.region ? '#f3f4f6' : 'white'
                }}
              >
                Tüm Bölgeler
              </div>
              {displayRegions.map(region => (
                <div
                  key={region}
                  onClick={() => {
                    updateFilters({ ...filters, region: region })
                    setShowRegionDropdown(false)
                  }}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    background: filters.region === region ? '#f3f4f6' : 'white'
                  }}
                >
                  {region}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Month Filter */}
      {showMonthFilter && (
        <div style={{ position: 'relative', zIndex: showMonthDropdown ? 9999 : 1 }}>
          <button
            onClick={() => {
              setShowMonthDropdown(!showMonthDropdown)
              setShowYearDropdown(false)
              setShowSegmentDropdown(false)
              setShowCustomerTypeDropdown(false)
              setShowApprovalStatusDropdown(false)
              setShowRegionDropdown(false)
            }}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              background: filters.month ? '#6366f1' : 'white',
              color: filters.month ? 'white' : '#374151',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500
            }}
          >
            <IconCalendarMonth size={15} stroke={1.8} style={{ marginRight: 4 }} /> {filters.month ? monthNames[filters.month - 1] : 'Tüm Aylar'}
          </button>
          {showMonthDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              zIndex: 9999,
              minWidth: '150px',
              maxHeight: '300px',
              overflowY: 'auto'
            }}>
              <div
                onClick={() => {
                  updateFilters({ ...filters, month: undefined, startDate: undefined, endDate: undefined })
                  setShowMonthDropdown(false)
                }}
                style={{
                  padding: '10px 16px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  background: !filters.month ? '#f3f4f6' : 'white'
                }}
              >
                Tüm Aylar
              </div>
              {defaultMonths.sort((a, b) => a - b).map(month => (
                <div
                  key={month}
                  onClick={() => {
                    updateFilters({ ...filters, month, startDate: undefined, endDate: undefined })
                    setShowMonthDropdown(false)
                  }}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    background: filters.month === month ? '#f3f4f6' : 'white'
                  }}
                >
                  {monthNames[month - 1]}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Year Filter */}
      {showYearFilter && (
        <div style={{ position: 'relative', zIndex: showYearDropdown ? 9999 : 1 }}>
          <button
            onClick={() => {
              setShowYearDropdown(!showYearDropdown)
              setShowMonthDropdown(false)
              setShowSegmentDropdown(false)
              setShowCustomerTypeDropdown(false)
              setShowApprovalStatusDropdown(false)
              setShowRegionDropdown(false)
            }}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              background: filters.year ? '#6366f1' : 'white',
              color: filters.year ? 'white' : '#374151',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500
            }}
          >
             <IconCalendar size={15} stroke={1.8} style={{ marginRight: 4 }} /> {filters.year || 'Tüm Yıllar'}
          </button>
          {showYearDropdown && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              zIndex: 9999,
              minWidth: '150px'
            }}>
              <div
                  onClick={() => {
                    updateFilters({ ...filters, year: undefined, startDate: undefined, endDate: undefined })
                    setShowYearDropdown(false)
                  }}
                style={{
                  padding: '10px 16px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  background: !filters.year ? '#f3f4f6' : 'white'
                }}
              >
                Tüm Yıllar
              </div>
              {defaultYears.sort((a, b) => b - a).map(year => (
                <div
                  key={year}
                  onClick={() => {
                    updateFilters({ ...filters, year, startDate: undefined, endDate: undefined })
                    setShowYearDropdown(false)
                  }}
                  style={{
                    padding: '10px 16px',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    background: filters.year === year ? '#f3f4f6' : 'white'
                  }}
                >
                  {year}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Date Range Filter */}
      {showDateRangeFilter && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="date"
              value={filters.startDate || ''}
              onChange={(e) => updateFilters({ ...filters, startDate: e.target.value || undefined, year: undefined, month: undefined })}
              style={{
                padding: '8px 12px',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '0.875rem',
                color: filters.startDate ? '#374151' : '#9ca3af',
                minWidth: '130px'
              }}
            />
          </div>
          <IconArrowRight size={14} stroke={2} color="#9ca3af" />
          <div style={{ position: 'relative' }}>
            <input
              type="date"
              value={filters.endDate || ''}
              onChange={(e) => updateFilters({ ...filters, endDate: e.target.value || undefined, year: undefined, month: undefined })}
              style={{
                padding: '8px 12px',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '0.875rem',
                color: filters.endDate ? '#374151' : '#9ca3af',
                minWidth: '130px'
              }}
            />
          </div>
        </div>
      )}

      {showApplyButton && isDirty && (
        <button
          onClick={handleApply}
          title="Filtreleri Uygula"
          style={{
            padding: '8px 18px',
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            border: 'none',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            color: 'white',
            cursor: 'pointer',
            fontSize: '0.85rem',
            fontWeight: 600,
            boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
            whiteSpace: 'nowrap',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 4px 12px rgba(99,102,241,0.4)'}
          onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 2px 8px rgba(99,102,241,0.3)'}
        >
          <IconCircleCheck size={16} stroke={2} />
          Uygula
        </button>
      )}
        </>
      )}
    </div>
  )
}

// React.memo ile gereksiz re-render önleme
export default memo(FilterPanel)
