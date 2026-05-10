import { useState, useEffect, useRef, memo } from 'react'
import { axisFormatter } from '../utils/format'
import * as echarts from 'echarts/core'
import type { EChartsCoreOption, EChartsType } from 'echarts/core'
import { LineChart, BarChart, PieChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import apiClient from '../api/client'
import InlineSpinner from './InlineSpinner'

// Register only what we use to keep bundle size small.
echarts.use([
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  DataZoomComponent,
  CanvasRenderer,
])

export interface ChartProps {
  dataSourceId?: string // Opsiyonel yaptık
  manualData?: { labels: string[], values: number[] } // Manuel veri girişi için
  type: 'line' | 'bar' | 'pie' | 'scatter'
  xAxis?: string
  yAxis?: string
  aggregation?: 'sum' | 'average' | 'count' | 'min' | 'max'
  title?: string
  height?: string
  axisType?: 'time' | 'category' // New prop
}

interface QueryData {
  labels: string[]
  values: number[]
}

function Chart({ 
  dataSourceId, 
  manualData,
  type, 
  xAxis, 
  yAxis, 
  aggregation,
  title,
  height = '100%',
  axisType
}: ChartProps) {
  const [data, setData] = useState<QueryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<EChartsType | null>(null)

  // Veri Kaynağı Değiştiğinde
  useEffect(() => {
    if (manualData) {
      setData(manualData)
      setLoading(false)
    } else if (dataSourceId && xAxis && yAxis && aggregation) {
      loadData()
    }
  }, [dataSourceId, xAxis, yAxis, aggregation, manualData])

  // Grafik Init & Cleanup
  useEffect(() => {
    if (loading) return
    if (!chartRef.current) return

    // Varsa mevcut instance'ı al, yoksa oluştur
    let chart = echarts.getInstanceByDom(chartRef.current)
    if (!chart) {
      chart = echarts.init(chartRef.current)
    }
    chartInstance.current = chart

    // Resize handler
    const handleResize = () => {
      chart?.resize()
    }
    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      chart?.dispose()
      chartInstance.current = null
    }
  }, [loading]) // Loading bitince ref render olur ve init çalışır

  // Veri ve Ayar Güncelleme
  useEffect(() => {
    if (!chartInstance.current || !data) return

    const option: EChartsCoreOption = getChartOption()
    
    // Safety check: Option boşsa veya hata varsa set etme
    if (Object.keys(option).length > 0) {
        try {
            chartInstance.current.setOption(option, true) // true = not merge, reset
        } catch (e) {
            // Chart render hatası sessizce ele alınır
        }
    }
    
    // Zoom olaylarını dinle (Sadece line grafiği için gerekirse)
    if (type === 'line') {
       chartInstance.current.off('dataZoom')
       chartInstance.current.on('dataZoom', () => {
         // Gerekirse zoom sonrası işlemler buraya
       })
    }
  }, [data, type, title, loading]) // Loading eklendi ki init sonrası hemen çizsin

  const loadData = async () => {
    try {
      setLoading(true)
      setError('')
      
      const result = await apiClient.query(
        dataSourceId!,
        yAxis,
        aggregation,
        xAxis
      )
      
      setData(result)
    } catch (err: any) {
      setError('Veri yüklenemedi')
    } finally {
      setLoading(false)
    }
  }

  const getChartOption = (): EChartsCoreOption => {
    if (!data) return {}

    const commonTooltip: any = {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: 'transparent',
      borderWidth: 0,
      padding: [12, 16],
      textStyle: { color: '#1f2937', fontSize: 13 },
      confine: true,
      extraCssText: 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border-radius: 12px;',
    }

    const commonGrid = { left: '3%', right: '4%', top: title ? 60 : 20, bottom: type === 'line' ? '25%' : '5%', containLabel: true }

    // Türkçe Tarih Formatlayıcı
    const dateLabelFormatter = (value: number, index: number) => {
        const date = new Date(value);
        const monthNames = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
        const shortMonthNames = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
        
        // ECharts otomatik olarak tick'leri belirler. Biz sadece formatlıyoruz.
        // Eğer saat bilgisi varsa (00:00 değilse) saati göster
        if (date.getHours() !== 0 || date.getMinutes() !== 0) {
             return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        }
        
        // Sadece gün ve ay göster (13 Oca)
        return `${date.getDate()} ${shortMonthNames[date.getMonth()]}`;
    };

    switch (type) {
      case 'line':
        // Check if we want Category axis (e.g. for Monthly view with pre-formatted labels)
        if (axisType === 'category') {
             return {
              title: title ? { text: title, left: 'center', textStyle: { fontSize: 14 } } : undefined,
              tooltip: { 
                trigger: 'axis', 
                ...commonTooltip,
                formatter: function (params: any) {
                  const label = params[0].name;
                  const val = params[0].value;
                  return `<div style="font-weight: 500; color: #6b7280; margin-bottom: 4px">${label}</div>
                          <div style="font-weight: 700; color: #111827">₺${val.toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>`;
                }
              },
              grid: { ...commonGrid, bottom: '25%' },
              xAxis: {
                type: 'category',
                data: data.labels,
                boundaryGap: false, // Line starts at axis
                axisLabel: { color: '#6b7280', fontSize: 11, margin: 12 },
                axisLine: { show: false },
                axisTick: { show: false }
              },
              yAxis: { 
                type: 'value',
                axisLabel: { color: '#6b7280' },
                splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } }
              },
              series: [
                {
                  data: data.values,
                  type: 'line',
                  smooth: true,
                  showSymbol: false, 
                  symbolSize: 8,
                  itemStyle: { color: '#3b82f6' },
                  lineStyle: { width: 1.5 },
                  areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                      { offset: 1, color: 'rgba(59, 130, 246, 0)' }
                    ])
                  },
                },
              ],
            }
        }

        // Default Time Series Logic
        // Line chart için veriyi [timestamp, value] formatına çeviriyoruz
        const timeSeriesData = data.labels.map((label, i) => {
            return [new Date(label).getTime(), data.values[i]];
        }).filter(d => !isNaN(d[0] as number) && d[1] !== null) 
          .sort((a, b) => (a[0] as number) - (b[0] as number));

        // Veri aralığını hesapla (gün sayısı)
        const dataRange = timeSeriesData.length > 1 
          ? ((timeSeriesData[timeSeriesData.length - 1][0] as number) - (timeSeriesData[0][0] as number)) / (1000 * 60 * 60 * 24)
          : 30;

        return {
          title: title ? { text: title, left: 'center', textStyle: { fontSize: 14 } } : undefined,
          tooltip: { 
            trigger: 'axis', 
            ...commonTooltip,
            formatter: function (params: any) {
              const date = new Date(params[0].value[0]);
              const val = params[0].value[1];
              const dateStr = date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
              return `<div style="font-weight: 500; color: #6b7280; margin-bottom: 4px">${dateStr}</div>
                      <div style="font-weight: 700; color: #111827">₺${val.toLocaleString('tr-TR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>`;
            }
          },
          grid: { ...commonGrid, bottom: '25%' }, 
          xAxis: {
            type: 'time', 
            boundaryGap: false as any,
            min: 'dataMin', 
            max: 'dataMax',
            axisLabel: { 
                formatter: (value: number) => {
                  const date = new Date(value);
                  const shortMonthNames = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
                  if (dataRange > 365) {
                    return `${shortMonthNames[date.getMonth()]} ${date.getFullYear().toString().slice(2)}`;
                  } else if (dataRange > 60) {
                    return shortMonthNames[date.getMonth()];
                  } else {
                    return `${date.getDate()} ${shortMonthNames[date.getMonth()]}`;
                  }
                },
                color: '#6b7280',
                rotate: 0, 
                hideOverlap: true,
                fontSize: 11,
                margin: 12
            },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false }
          },
          yAxis: {
            type: 'value',
            axisLabel: { color: '#6b7280', formatter: axisFormatter },
            splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } }
          },
          dataZoom: [
            {
              type: 'slider',
              show: true,
              xAxisIndex: [0],
              start: 0,
              end: 100,
              bottom: 0,
              height: 24,
              borderColor: '#e5e7eb',
              backgroundColor: '#f9fafb',
              fillerColor: 'rgba(59, 130, 246, 0.15)',
              handleStyle: { color: '#3b82f6', borderColor: '#3b82f6' },
              dataBackground: {
                lineStyle: { color: '#93c5fd' },
                areaStyle: { color: 'rgba(147, 197, 253, 0.3)' }
              },
              selectedDataBackground: {
                lineStyle: { color: '#3b82f6' },
                areaStyle: { color: 'rgba(59, 130, 246, 0.2)' }
              },
              textStyle: { color: '#6b7280', fontSize: 10 },
              labelFormatter: (value: number) => {
                const date = new Date(value);
                const shortMonths = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
                return `${date.getDate()} ${shortMonths[date.getMonth()]}`;
              }
            },
            { type: 'inside', start: 0, end: 100 }
          ],
          series: [
            {
              data: timeSeriesData, 
              type: 'line',
              smooth: true,
              showSymbol: timeSeriesData.length < 2, 
              symbolSize: 8,
              itemStyle: { color: '#3b82f6' },
              lineStyle: { width: 1 },
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                  { offset: 1, color: 'rgba(59, 130, 246, 0)' }
                ])
              },
            },
          ],
        }

      case 'bar':
        return {
          title: title ? { text: title, left: 'center' } : undefined,
          tooltip: { trigger: 'axis', ...commonTooltip },
          grid: commonGrid,
          xAxis: {
            type: 'category',
            data: data.labels,
            axisLabel: { rotate: 45, color: '#6b7280' },
            axisLine: { show: false },
            axisTick: { show: false },
          },
          yAxis: { 
             type: 'value',
             splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } }
          },
          series: [
            {
              data: data.values,
              type: 'bar',
              itemStyle: { color: '#10b981', borderRadius: [4, 4, 0, 0] },
            },
          ],
        }

      case 'pie':
        return {
          title: title ? { text: title, left: 'center' } : undefined,
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', ...commonTooltip },
          series: [
            {
              name: yAxis || 'Data',
              type: 'pie',
              radius: ['40%', '70%'],
              avoidLabelOverlap: false,
              itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
              },
              label: { show: false, position: 'center' },
              emphasis: {
                label: { show: true, fontSize: 20, fontWeight: 'bold' }
              },
              data: data.labels.map((label, i) => ({
                name: label,
                value: data.values[i],
              })),
            },
          ],
        }

      case 'scatter':
        // Scatter için de numeric/time dönüşümü gerekebilir ama şimdilik basic bırakalım
        return {
          title: title ? { text: title, left: 'center' } : undefined,
          tooltip: { trigger: 'item', ...commonTooltip },
          grid: commonGrid,
          xAxis: { type: 'category', data: data.labels },
          yAxis: { type: 'value' },
          series: [
            {
              data: data.values,
              type: 'scatter',
              symbolSize: 10,
              itemStyle: { color: '#f59e0b' },
            },
          ],
        }

      default:
        return {}
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <InlineSpinner size={28} thickness={3} />
      </div>
    )
  }

  if (error) {
    return <div style={{display:'flex', justifyContent:'center', alignItems:'center', height: '100%', color: '#ef4444'}}>{error}</div>
  }

  return (
    <div
      ref={chartRef}
      style={{
        width: '100%',
        height: height,
        minHeight: '250px',
      }}
    />
  )
}

export default memo(Chart)
