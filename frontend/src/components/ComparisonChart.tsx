import { useRef, useEffect, memo } from 'react'
import { axisFormatter } from '../utils/format'
import * as echarts from 'echarts/core'
import type { EChartsCoreOption, EChartsType } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer,
])

interface ComparisonChartProps {
  title: string
  subTitle?: string
  data: {
    [year: string]: number[]
  }
  valuePrefix?: string
  years: number[] // e.g. [2026, 2025, 2024]
  colors?: string[]
}

function ComparisonChart({ title, subTitle, data, valuePrefix = '', years, colors = ['#3b82f6', '#9ca3af', '#e5e7eb'] }: ComparisonChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<EChartsType | null>(null)

  useEffect(() => {
    if (!chartRef.current) return

    let chart = echarts.getInstanceByDom(chartRef.current)
    if (!chart) {
      chart = echarts.init(chartRef.current)
    }
    chartInstance.current = chart

    const handleResize = () => chart?.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart?.dispose()
      chartInstance.current = null
    }
  }, [])

  useEffect(() => {
    if (!chartInstance.current) return

    // Sort years descending for legend but order in bar group is handled by series order
    // Typically: Current Year first or last? 
    // Image shows: Orange bars (current year?) vs Others.
    // Let's render series in order of 'years' prop.
    
    const monthNames = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
    
    const series = years.map((y, idx) => ({
        name: y.toString(),
        type: 'bar',
        // Handle both number and string keys from backend
        data: data[y] || data[y.toString()] || new Array(12).fill(0),
        itemStyle: {
            color: colors[idx % colors.length],
            borderRadius: [4, 4, 0, 0] as any
        },
        barGap: '20%',
        barCategoryGap: '40%'
    }))

    const option: EChartsCoreOption = {
      title: {
          text: title,
          subtext: subTitle,
          left: 'left',
          textStyle: { fontSize: 16, fontWeight: 700, color: '#111827' },
          subtextStyle: { fontSize: 13, color: '#6b7280' }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderColor: 'transparent',
        padding: [12, 16],
        textStyle: { color: '#1f2937', fontSize: 13 },
        extraCssText: 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border-radius: 12px;',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
            let tooltip = `<div style="margin-bottom: 8px; font-weight: 600; color: #111827;">${params[0].axisValue}</div>`;
            params.forEach((item: any) => {
                const val = item.value;
                // Format: 1.234.567 (no decimals)
                const formattedVal = typeof val === 'number' 
                    ? val.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) 
                    : val;
                
                tooltip += `
                   <div style="display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 4px;">
                       <div style="display: flex; align-items: center; gap: 6px;">
                           ${item.marker}
                           <span style="color: #4b5563;">${item.seriesName}</span>
                       </div>
                       <span style="font-weight: 600; color: #111827;">${valuePrefix}${formattedVal}</span>
                   </div>
                `;
            });
            return tooltip;
        }
      },
      legend: {
          data: years.map(y => y.toString()),
          right: 0,
          top: 0,
          icon: 'circle',
          itemGap: 15
      },
      grid: {
        left: '2%',
        right: '2%',
        bottom: '5%',
        top: '20%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: monthNames,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#6b7280', fontSize: 12 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } },
        axisLabel: { color: '#6b7280', formatter: axisFormatter }
      },
      series: series as any
    }

    chartInstance.current.setOption(option)
  }, [data, title, subTitle, years, colors, valuePrefix])

  return <div ref={chartRef} style={{ width: '100%', height: '100%', minHeight: '300px' }} />
}

// React.memo ile gereksiz re-render önleme
export default memo(ComparisonChart)
