import { useRef, useMemo, memo } from 'react'

const isDev = import.meta.env.DEV

interface DonutChartProps {
  categoryData: Array<{ name: string; revenue: number; count?: number; level?: string }>
  otherItems: Array<{ name: string; revenue: number; count?: number }>
  totalRevenueForDisplay: number
  hoveredSlice: string | null
  showOthersBreakdown: boolean
  viewMode: 'category' | 'brand'
  colors: string[]
  onHoveredSliceChange: (slice: string | null) => void
  onShowOthersBreakdownChange: (show: boolean) => void
  onSliceClick: (item: { name: string; level?: string }) => void
  onHoverPrefetch?: (item: { name: string; level?: string }) => void
  pieLegendRef: React.RefObject<HTMLDivElement>
  pieOthersRef: React.RefObject<HTMLDivElement>
}

function DonutChart({
  categoryData,
  otherItems, // We don't rely only on this, we split internal categoryData too
  totalRevenueForDisplay,
  hoveredSlice,
  showOthersBreakdown,
  viewMode,
  colors,
  onHoveredSliceChange,
  onShowOthersBreakdownChange,
  onSliceClick,
  onHoverPrefetch,
  pieLegendRef,
  pieOthersRef
}: DonutChartProps) {

  const chartHoverPrefetchTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Logic: Top 5 + Others
  // Split the raw categoryData into:
  // 1. finalData (max 6 items: Top 5 + Others) for the CHARTS
  // 2. othersList (the remaining items) for the LEGEND breakdown
  const { finalData, othersList } = useMemo(() => {
      // 1. Sort all by revenue descending
      const sorted = [...categoryData].sort((a, b) => b.revenue - a.revenue)
      
      // If 6 or fewer items, no need for "Others". Just show all.
      if (sorted.length <= 6) {
          return { finalData: sorted, othersList: [] }
      }

      // 2. Take Top 5 for the chart
      const top5 = sorted.slice(0, 5)
      
      // 3. The rest go into Others
      const others = sorted.slice(5)
      const othersRevenue = others.reduce((sum, item) => sum + item.revenue, 0)
      
      // Construct the data for the chart (Top 5 + aggregated Others)
      // Note: We use 'Diğer' as the name to match the check in click handler
      const chartData = [...top5, { name: 'Diğer', revenue: othersRevenue }]
      
      return { 
          finalData: chartData,
          othersList: others
      }
  }, [categoryData])

  const categoryDataTotal = finalData.reduce((sum, item) => sum + item.revenue, 0)

  const formatMoneyShort = (value: number) => {
    if (value >= 1000000) return `₺${(value / 1000000).toFixed(2)}M`
    if (value >= 1000) return `₺${(value / 1000).toFixed(1)}K`
    return `₺${value.toFixed(0)}`
  }

  const percentOfTotal = (value: number) => (categoryDataTotal ? (value / categoryDataTotal) * 100 : 0)

  // Calculate rendering percentages (Visual clamping for small/large Others)
  const getRenderPercentages = (items: Array<{ name: string; revenue: number }>) => {
    const others = items.find((i) => i.name === 'Diğer')
    
    // No others or Others is small -> Standard Proportional
    if (!others) return new Map<string, number>()
    
    const trueOthersPct = percentOfTotal(others.revenue)
    
    // Visual Requirement: If 'Diğer' is dominant (> 7%), clamp it visually to 7%
    // so other top items remain visible segments on the chart.
    const renderOthersPct = trueOthersPct > 7 ? 7 : trueOthersPct

    const nonOthers = items.filter((i) => i.name !== 'Diğer')
    
    // Distribute the remaining visual space
    const remainingVisualSpace = 100 - renderOthersPct
    const nonOthersTotalRevenue = nonOthers.reduce((sum, i) => sum + i.revenue, 0)

    const map = new Map<string, number>()
    map.set('Diğer', renderOthersPct)

    if (nonOthersTotalRevenue === 0) {
       map.set('Diğer', 100)
       return map
    }

    for (const item of nonOthers) {
      const shareOfRemainder = item.revenue / nonOthersTotalRevenue
      map.set(item.name, shareOfRemainder * remainingVisualSpace)
    }

    return map
  }

  // Handle click on slice or legend item
  const handleItemClick = (item: { name: string; level?: string }) => {
    // If user clicks 'Diğer', toggle the breakdown list
    if (item.name === 'Diğer') {
         // Force toggle to true if it matches
         onShowOthersBreakdownChange(!showOthersBreakdown)
    } else {
         // Standard filtering click
         onSliceClick(item)
    }
  }

  const renderClassicDonut = () => {
    const tooltipData: Array<{ name: string; revenue: number; percentage: number; count?: number; labelX: number; labelY: number }> = []
    let angleCursor = 0

    const renderPctMap = getRenderPercentages(finalData)

    const cx = 120
    const cy = 120
    const r = 92
    const strokeW = 30
    const c = 2 * Math.PI * r
    const gapLen = 2
    let cumLen = 0

    return (
      <svg className="pie-chart-svg" viewBox="0 0 240 240" style={{ overflow: 'visible' }}>
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#eef2f7"
          strokeWidth={strokeW}
        />

        {finalData.map((item, idx) => {
          const truePercentage = percentOfTotal(item.revenue)
          const renderPercentage = renderPctMap.get(item.name) ?? truePercentage
          const angle = (renderPercentage / 100) * 360
          const midAngle = angleCursor + (angle / 2)
          angleCursor += angle

          const labelR2 = 118
          const labelX = cx + labelR2 * Math.cos((midAngle - 90) * Math.PI / 180)
          const labelY = cy + labelR2 * Math.sin((midAngle - 90) * Math.PI / 180)

          tooltipData.push({
            name: item.name,
            revenue: item.revenue,
            percentage: truePercentage,
            count: item.count,
            labelX,
            labelY
          })

          const segLen = (renderPercentage / 100) * c
          if (segLen <= 0) return null

          // Dash array calculation for donut segments
          const dash = Math.min(c, Math.max(2, segLen - gapLen))
          const offset = cumLen + gapLen / 2
          cumLen += segLen

          const isHover = hoveredSlice === item.name
          const dim = hoveredSlice && !isHover
          const isOthers = item.name === 'Diğer'
          const strokeColor = isOthers ? '#94a3b8' : colors[idx % colors.length]

          return (
            <circle
              key={item.name}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={strokeColor}
              strokeWidth={isHover ? strokeW + 3 : strokeW}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${c - dash}`}
              strokeDashoffset={c * 0.25 - offset}
              className="pie-path"
              data-category={item.name}
              style={{
                transition: 'all 0.18s ease',
                opacity: dim ? 0.22 : (isOthers ? 0.78 : 1),
                cursor: 'pointer',
                filter: isHover && !isOthers ? 'drop-shadow(0 10px 24px rgba(2,6,23,0.14))' : 'none'
              }}
              onMouseEnter={() => {
                onHoveredSliceChange(item.name)
                // Optional prefetch logic can go here
                if (chartHoverPrefetchTimerRef.current) clearTimeout(chartHoverPrefetchTimerRef.current)
                if (onHoverPrefetch) {
                   chartHoverPrefetchTimerRef.current = setTimeout(() => onHoverPrefetch(item), 120)
                }
              }}
              onMouseLeave={() => {
                onHoveredSliceChange(null)
                if (chartHoverPrefetchTimerRef.current) {
                   clearTimeout(chartHoverPrefetchTimerRef.current)
                   chartHoverPrefetchTimerRef.current = null
                }
              }}
              onClick={() => handleItemClick(item)}
            />
          )
        })}

        {/* Center Text */}
        <circle cx={cx} cy={cy} r={60} fill="#ffffff" />
        <text x={cx} y={cy - 8} textAnchor="middle" style={{ fontSize: '10px', fill: '#9ca3af', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>TOPLAM</text>
        <text x={cx} y={cy + 14} textAnchor="middle" style={{ fontSize: '15px', fill: '#111827', fontWeight: 700 }}>
          {totalRevenueForDisplay >= 1000000
            ? `₺${(totalRevenueForDisplay / 1000000).toFixed(1)} Mn TL`
            : totalRevenueForDisplay >= 1000 
                ? `₺${(totalRevenueForDisplay / 1000).toFixed(0)} Bin TL`
                : `₺${totalRevenueForDisplay.toFixed(0)}`
          }
        </text>

        {/* Tooltips - Rendered last to be on top */}
        {hoveredSlice && tooltipData.map((tooltip, idx) => {
          if (tooltip.name !== hoveredSlice) return null
          
          // Tooltip Layout
          const tooltipHeight = tooltip.count ? 90 : 70
          const tooltipY = tooltip.labelY - (tooltipHeight / 2)
          
          return (
            <g key={`tooltip-${idx}`} className="pie-tooltip-group" style={{ pointerEvents: 'none' }}>
              <rect
                x={tooltip.labelX - 65}
                y={tooltipY}
                width="130"
                height={tooltipHeight}
                fill="white"
                stroke="#d1d5db"
                strokeWidth="1.5"
                rx="6"
                className="pie-tooltip"
                style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.1))' }}
              />
              <text
                x={tooltip.labelX}
                y={tooltipY + 18}
                textAnchor="middle"
                className="pie-label-name"
                style={{ fontWeight: 600, fontSize: '12px', fill: '#111827' }}
              >
                {tooltip.name.length > 15 ? tooltip.name.substring(0, 15) + '...' : tooltip.name}
              </text>
              <text
                x={tooltip.labelX}
                y={tooltipY + 38}
                textAnchor="middle"
                className="pie-label-value"
                style={{ fill: '#10b981', fontWeight: 600, fontSize: '13px' }}
              >
                {formatMoneyShort(tooltip.revenue)}
              </text>
              <text
                x={tooltip.labelX}
                y={tooltipY + 56}
                textAnchor="middle"
                className="pie-label-percentage"
                style={{ fill: '#6b7280', fontSize: '11px' }}
              >
                {tooltip.percentage.toFixed(1)}% Pay
              </text>
              {tooltip.count && (
                <text
                  x={tooltip.labelX}
                  y={tooltipY + 74}
                  textAnchor="middle"
                  style={{ fill: '#6b7280', fontSize: '10px' }}
                >
                  {tooltip.count} Satış
                </text>
              )}
            </g>
          )
        })}
      </svg>
    )
  }

  if (categoryData.length === 0 && totalRevenueForDisplay === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
        Görüntülenecek veri bulunamadı
      </div>
    )
  }

  // Determine which list to show in legend
  const legendItems = showOthersBreakdown ? othersList : finalData

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      
      {/* Chart Section */}
      <div className="pie-chart-container" style={{ position: 'relative', margin: '0 auto', width: '240px', height: '240px', flexShrink: 0 }}>
        {renderClassicDonut()}
      </div>

      {/* Legend Section */}
      <div className="pie-chart-legend" ref={pieLegendRef} style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, overflowY: 'auto', minHeight: 0, paddingRight: '4px' }}>
        
        {/* Back Button (Only visible when viewing Others breakdown) */}
        {showOthersBreakdown && (
            <div 
                onClick={() => onShowOthersBreakdownChange(false)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 0 16px 0',
                    cursor: 'pointer',
                    color: '#3b82f6',
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    borderBottom: '1px solid #e5e7eb',
                    marginBottom: '8px'
                }}
            >
                <div style={{ padding: '4px', background: '#eff6ff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                     <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="19" y1="12" x2="5" y2="12"></line>
                        <polyline points="12 19 5 12 12 5"></polyline>
                     </svg>
                </div>
                <span>Geri Dön</span>
            </div>
        )}

        {legendItems.map((item, idx) => {
          const pct = percentOfTotal(item.revenue)
          
          // Is this item the 'Diğer' slice in the main view?
          const isOthersSlice = item.name === 'Diğer'
          
          // Clickable Logic:
          // 1. If it's the "Diğer" slice (in main view), it is clickable to Enter Breakdown.
          // 2. If we are IN breakdown, all items are effectively clickable (standard filter)? No, usually just display. 
          //    But if you want them to act as filters, we keep standard onSliceClick.
          // 3. If standard Top 5 slice, it is clickable to Filter.
          
          let isClickable = true
          // If we are in breakdown, these are normal items (hidden leftovers), so they act like normal categories -> Clickable
          
          const isActive = hoveredSlice === item.name
          const legendColor = isOthersSlice ? '#94a3b8' : colors[idx % colors.length]

          return (
            <div 
                key={item.name} 
                className={`pie-legend-row ${isActive ? 'is-active' : ''}`}
                onMouseEnter={() => {
                  onHoveredSliceChange(item.name)
                }}
                onMouseLeave={() => {
                  onHoveredSliceChange(null)
                }}
                onClick={() => handleItemClick(item)}
                style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    padding: '12px 0', 
                    borderBottom: '1px solid #f3f4f6',
                    cursor: isClickable ? 'pointer' : 'default',
                    opacity: hoveredSlice && hoveredSlice !== item.name ? 0.5 : 1,
                    transition: 'all 0.2s',
                    backgroundColor: isActive ? '#f9fafb' : 'transparent',
                    borderRadius: '8px',
                    paddingLeft: '8px',
                    paddingRight: '8px'
                }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
                  {/* Dot */}
                  <div style={{ 
                      width: '10px', 
                      height: '10px', 
                      borderRadius: '50%', 
                      background: legendColor,
                      flexShrink: 0
                  }} />
                  
                  {/* Name and Value */}
                  <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                      <span style={{ 
                          fontSize: '0.8rem', 
                          fontWeight: 700, 
                          color: '#374151', 
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                      }}>
                          {item.name}
                      </span>
                      <span style={{ 
                          fontSize: '0.75rem', 
                          color: '#9ca3af',
                          marginTop: '2px'
                      }}>
                          {formatMoneyShort(item.revenue)}
                      </span>
                  </div>
              </div>

              {/* Percentage */}
              <div style={{ 
                  fontSize: '0.9rem', 
                  fontWeight: 800, 
                  color: '#111827',
                  flexShrink: 0,
                  marginLeft: '8px'
              }}>
                  {pct.toFixed(1)}%
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// React.memo ile gereksiz re-render önleme
export default memo(DonutChart)
