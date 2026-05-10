import { useMemo, memo, lazy, Suspense } from 'react'

const Chart = lazy(() => import('./Chart'))

interface RevenueChartProps {
  data: { month: string; sales: number }[]
  dailyData?: { date: string; sales: number }[]
  title: string
  height?: string
}

function RevenueChart({ data, dailyData, title, height = '350px' }: RevenueChartProps) {
  // Günlük veri varsa HER ZAMAN onu kullan (zoom için gerekli)
  // Yoksa aylık veriye geri dön
  const { chartData, axisType } = useMemo(() => {
    if (dailyData && dailyData.length > 0) {
      return {
        chartData: {
            labels: dailyData.map(d => d.date),
            values: dailyData.map(d => d.sales)
        },
        axisType: 'time' as const
      }
    }
    
    // Monthly Data -> Format labels to "Ocak", "Şubat" etc.
    // Backend sends "2026-01", "2026-02".
    const monthNames = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
    
    return {
       chartData: {
          labels: data.map(d => {
             // d.month is "YYYY-MM" or "YYYY-MM-DD"? Usually "YYYY-MM" for monthly
             try {
                const parts = d.month.split('-');
                if (parts.length >= 2) {
                    const mIndex = parseInt(parts[1], 10) - 1;
                    if (mIndex >= 0 && mIndex < 12) {
                        // Short Year? "Ocak 26"
                        return `${monthNames[mIndex]} ${parts[0].slice(2)}`;
                    }
                }
                return d.month;
             } catch (e) { return d.month }
          }),
          values: data.map(d => d.sales)
       },
       axisType: 'category' as const
    }
  }, [data, dailyData])

  // Custom Tick Formatter for Chart.tsx if needed, but we formatted labels above.
  // Actually, let's update labels logic to handle YYYY-MM-DD
  const processedChartData = useMemo(() => {
      const monthNames = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
      
      if (!chartData) return { labels: [], values: [] };

      // dailyData varsa (time axis) etiketleri ham bırak — Chart.tsx new Date(label) ile parse eder
      if (axisType === 'time') {
          return {
              labels: chartData.labels,  // YYYY-MM-DD formatında ham
              values: chartData.values
          };
      }

      // Category axis için formatla
      const sourceData = data;

      return {
        values: chartData.values,
        labels: sourceData.map(d => {
             try {
                const parts = d.month.split('-');
                if (parts.length === 3) {
                    const day = parseInt(parts[2], 10);
                    const mIndex = parseInt(parts[1], 10) - 1;
                    const yearShort = parts[0].slice(2);
                    if (mIndex >= 0 && mIndex < 12) {
                        return `${day} ${monthNames[mIndex]} ${yearShort}`;
                    }
                }
                if (parts.length >= 2) {
                    const mIndex = parseInt(parts[1], 10) - 1;
                    if (mIndex >= 0 && mIndex < 12) {
                        return `${monthNames[mIndex]} ${parts[0].slice(2)}`;
                    }
                }
                return d.month;
             } catch (e) { return d.month }
        })
      }
  }, [chartData, data, axisType])

  return (
    <Suspense
      fallback={
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          Grafik yükleniyor…
        </div>
      }
    >
      <Chart
        type="line"
        manualData={processedChartData} 
        title={title}
        height={height}
        axisType={axisType}
      />
    </Suspense>
  )
}

export default memo(RevenueChart)

