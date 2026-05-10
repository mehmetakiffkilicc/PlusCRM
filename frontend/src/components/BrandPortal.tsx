import { useState, useEffect } from 'react'
import Modal from './Modal'
import apiClient from '../api/client'
import useDashboardStore from '../stores/dashboardStore'
import * as echarts from 'echarts'
import { 
  IconCurrencyLira, IconPackage, IconUsers, IconShoppingCart,
  IconTrendingUp, IconList, IconTrophy, IconChevronRight, IconDownload
} from '@tabler/icons-react'

interface BrandPortalProps {
  isOpen: boolean
  onClose: () => void
  brandName: string
}

interface CategoryHierarchyNode {
  name: string
  sales: number
  children?: CategoryHierarchyNode[]
}

interface BrandDetailData {
  brand: string
  summary: {
    sales: number
    units: number
    receipts: number
    customers: number
    avgTicket: number
  }
  monthlyTrend: { month: string; sales: number; units: number }[]
  categoryHierarchy: CategoryHierarchyNode[]
  topProducts: { name: string; sales: number; units: number }[]
}

function CategoryNode({ node, totalSales, brandName, onExport, level = 0, defaultOpen = true }: { node: CategoryHierarchyNode; totalSales: number; brandName: string; onExport: (nodeName: string, level: number) => Promise<void>; level?: number; defaultOpen?: boolean }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  
  // Update internal state if defaultOpen changes (e.g. from parent toggle)
  useEffect(() => {
    setIsOpen(defaultOpen)
  }, [defaultOpen])

  const [exportingInternally, setExportingInternally] = useState(false)
  const hasChildren = node.children && node.children.length > 0
  const percentage = (node.sales / totalSales) * 100

  const handleExport = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (exportingInternally) return
    setExportingInternally(true)
    try {
      await onExport(node.name, level);
    } finally {
      setExportingInternally(false)
    }
  }

  return (
    <div style={{ marginLeft: level > 0 ? '12px' : '0', marginBottom: '4px' }}>
      <div 
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          fontSize: level === 0 ? '0.85rem' : '0.75rem', 
          padding: '6px 10px',
          background: level === 0 ? '#f8fafc' : 'transparent',
          borderRadius: '6px',
          cursor: hasChildren ? 'pointer' : 'default',
          border: level === 0 ? '1px solid #e2e8f0' : 'none',
          transition: 'background 0.2s',
          gap: '8px',
          width: '100%',
          boxSizing: 'border-box'
        }}
        onMouseOver={e => hasChildren && (e.currentTarget.style.background = '#f1f5f9')}
        onMouseOut={e => hasChildren && (e.currentTarget.style.background = level === 0 ? '#f8fafc' : 'transparent')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, minWidth: 0 }}>
          {hasChildren && (
            <IconChevronRight size={14} style={{ 
              color: '#64748b', 
              transform: isOpen ? 'rotate(90deg)' : 'none', 
              transition: 'transform 0.2s',
              flexShrink: 0 
            }} />
          )}
          <span style={{ 
            color: level === 0 ? '#1e293b' : '#475569', 
            fontWeight: level === 0 ? 600 : 400, 
            whiteSpace: 'nowrap', 
            overflow: 'hidden', 
            textOverflow: 'ellipsis',
            flexShrink: 1
          }}>
            {node.name}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <span style={{ fontWeight: 600, color: '#6366f1', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
            ₺{Math.round(node.sales).toLocaleString('tr-TR')}
          </span>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', minWidth: '32px', textAlign: 'right' }}>
            %{percentage.toFixed(0)}
          </span>
          <button
            onClick={handleExport}
            disabled={exportingInternally}
            style={{
              padding: '4px 10px',
              background: 'white',
              color: '#6366f1',
              border: '1px solid #6366f1',
              borderRadius: '6px',
              fontSize: '0.65rem',
              fontWeight: 600,
              cursor: exportingInternally ? 'wait' : 'pointer',
              opacity: exportingInternally ? 0.6 : 1,
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            onMouseEnter={e => !exportingInternally && (e.currentTarget.style.background = '#f5f6ff')}
            onMouseLeave={e => !exportingInternally && (e.currentTarget.style.background = 'white')}
          >
            {exportingInternally ? (
              <>
                <span style={{ width: 10, height: 10, border: '2px solid #6366f1', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                <span>Bekleyin...</span>
              </>
            ) : (
              <>
                <IconDownload size={14} />
                <span>Dışa Aktar</span>
              </>
            )}
          </button>
        </div>
      </div>
      
      {percentage > 0 && (
        <div style={{ height: '3px', background: '#f1f5f9', borderRadius: '1.5px', overflow: 'hidden', margin: '2px 8px 6px' }}>
          <div style={{ 
            width: `${percentage}%`, 
            height: '100%', 
            background: ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'][level % 5],
            borderRadius: '1.5px'
          }}></div>
        </div>
      )}

      {isOpen && hasChildren && (
        <div style={{ marginTop: '4px', borderLeft: '1px solid #e2e8f0' }}>
          {node.children!.map((child, i) => (
            <CategoryNode key={i} node={child} totalSales={totalSales} brandName={brandName} onExport={onExport} level={level + 1} defaultOpen={defaultOpen} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function BrandPortal({ isOpen, onClose, brandName }: BrandPortalProps) {

  const { 
    selectedDataSourceId, 
    selectedYear, 
    selectedMonth, 
    selectedStartDate, 
    selectedEndDate,
    selectedRegion,
    selectedCustomerType,
    selectedApprovalStatus,
    selectedCategories
  } = useDashboardStore()

  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<BrandDetailData | null>(null)
  const [expandAll, setExpandAll] = useState(true)

  // Export Progress States
  const [isExporting, setIsExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState(0)
  const [exportStep, setExportStep] = useState('')

  const handleExportBrandCustomers = async (categoryName: string, level: number) => {
    if (isExporting) return
    setIsExporting(true)
    setExportProgress(0)
    setExportStep('Müşteri listesi hazırlanıyor... (v7)')
    let progressInterval: any = null
    const startProgress = (target: number, durationMs: number) => {
      if (progressInterval) clearInterval(progressInterval)
      const steps = 20
      const stepMs = durationMs / steps
      let current = exportProgress
      progressInterval = setInterval(() => {
        current = Math.min(current + (target - current) * 0.2, target - 1)
        setExportProgress(Math.round(current))
      }, stepMs)
    }

    try {
      setExportStep('Kategori verileri sorgulanıyor...')
      startProgress(30, 1000)

      const levelName = level === 0 ? 'ana' : level === 1 ? 'alt1' : 'alt2'
      
      setExportStep('Sunucu verileri hazırlıyor...')
      startProgress(70, 4000)

      const response = await apiClient.exportBrandCustomers(brandName, categoryName, levelName as any)
      const blobData = response.data
      
      setExportProgress(90)
      setExportStep('Dosya indiriliyor... (v7)')

      const blob = blobData instanceof Blob ? blobData : new Blob([blobData], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      
      if (blob.size < 100) {
        throw new Error('Sunucudan boş veya geçersiz bir dosya döndü. Lütfen filtrelerinizi kontrol edip tekrar deneyin.')
      }

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      
      // v7: Final clean filename logic. 
      // Removes any UTF-8 prefix issues by ignoring headers and generating a clean, descriptive name.
      const safeBrand = (brandName || 'Marka').replace(/[^a-z0-9]/gi, '_');
      const safeCat = (categoryName || 'Kategori').replace(/[^a-z0-9]/gi, '_');
      const now = new Date();
      const dateStr = `${now.getDate()}-${now.getMonth()+1}-${now.getFullYear()}`;
      const downloadName = `Musteri_Listesi_${safeBrand}_${safeCat}_${dateStr}.xlsx`;

      a.href = url
      a.download = downloadName
      a.setAttribute('download', downloadName)
      
      document.body.appendChild(a)
      a.click()
      
      // Cleanup
      setTimeout(() => {
        if (document.body.contains(a)) document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      }, 15000)

      setExportProgress(100)
      setExportStep('Tamamlandı!')
      setTimeout(() => setIsExporting(false), 2000)

    } catch (err: any) {
      console.error('Export error:', err)
      let errorMsg = 'Bilinmeyen bir hata oluştu'
      
      if (err.response) {
        // Axios error
        const reader = new FileReader()
        reader.onload = () => {
          const text = reader.result as string
          const isHtml = text.trim().startsWith('<')
          alert(isHtml ? `Sunucu hatası (${err.response.status})` : (text || `Sunucu hatası (${err.response.status})`))
        }
        if (err.response.data instanceof Blob) {
          reader.readAsText(err.response.data)
        } else {
          alert(err.message || 'Sunucu hatası')
        }
      } else {
        alert(err.message || errorMsg)
      }
      setIsExporting(false)
    } finally {
      if (progressInterval) clearInterval(progressInterval)
    }
  }

  // Helper to count nodes
  const countNodes = (nodes: CategoryHierarchyNode[]): number => {
    return nodes.reduce((acc, node) => acc + 1 + (node.children ? countNodes(node.children) : 0), 0)
  }

  useEffect(() => {
    if (isOpen && brandName && selectedDataSourceId) {
      loadBrandDetail()
    }
  }, [isOpen, brandName, selectedDataSourceId, selectedYear, selectedMonth, selectedStartDate, selectedEndDate, selectedRegion, selectedCustomerType, selectedApprovalStatus, selectedCategories])

  const loadBrandDetail = async () => {
    setLoading(true)
    setData(null)
    try {
      const filters = {
        brand: brandName,
        year: selectedYear,
        month: selectedMonth,
        start_date: selectedStartDate,
        end_date: selectedEndDate,
        region: selectedRegion,
        customer_type: selectedCustomerType,
        approval_status: selectedApprovalStatus,
        category: selectedCategories
      }
      const result = await apiClient.getBrandDetail(selectedDataSourceId!, filters)
      setData(result)
      
      // Smart expand: if nodes > 100, collapse by default
      if (result.categoryHierarchy) {
        const totalNodes = countNodes(result.categoryHierarchy)
        if (totalNodes > 100) {
          setExpandAll(false)
        } else {
          setExpandAll(true)
        }
      }
    } catch (error) {
      console.error('Error loading brand detail:', error)
    } finally {
      setLoading(false)
    }
  }

  // Charts Initialization
  useEffect(() => {
    if (!loading && data && isOpen) {
      // Trend Chart
      const trendDom = document.getElementById('brand-trend-chart')
      if (trendDom) {
        const trendChart = echarts.init(trendDom)
        trendChart.setOption({
          tooltip: { trigger: 'axis' },
          grid: { top: 40, bottom: 40, left: 50, right: 20 },
          xAxis: { 
            type: 'category', 
            data: data.monthlyTrend.map(t => t.month),
            axisLabel: { color: '#6b7280' }
          },
          yAxis: { 
            type: 'value',
            axisLabel: { 
              color: '#6b7280',
              formatter: (value: number) => value >= 1000 ? `₺${(value/1000).toFixed(0)}k` : `₺${value}`
            },
            splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } }
          },
          series: [{
            data: data.monthlyTrend.map(t => t.sales),
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: { width: 3, color: '#6366f1' },
            itemStyle: { color: '#6366f1' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(99, 102, 241, 0.2)' },
                { offset: 1, color: 'rgba(99, 102, 241, 0)' }
              ])
            }
          }]
        })
        
        const resize = () => trendChart.resize()
        window.addEventListener('resize', resize)
        return () => {
          window.removeEventListener('resize', resize)
          trendChart.dispose()
        }
      }
    }
    // Return undefined if conditions aren't met
    return undefined
  }, [loading, data, isOpen])

  if (!isOpen) return null

  const skeletonBase = { background: 'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)', backgroundSize: '200% 100%', animation: 'brand-shimmer 1.2s ease-in-out infinite', borderRadius: '8px' }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Marka Portalı: ${brandName}`} width="1000px">
      {loading && !data ? (
        <div style={{ display: 'grid', gap: '24px', padding: '8px 0' }}>
          <style>{`@keyframes brand-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            {[...Array(4)].map((_, i) => <div key={i} style={{ ...skeletonBase, height: '80px' }} />)}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '24px' }}>
            <div style={{ ...skeletonBase, height: '300px' }} />
            <div style={{ ...skeletonBase, height: '300px' }} />
          </div>
          <div style={{ ...skeletonBase, height: '200px' }} />
        </div>
      ) : data ? (
        <div style={{ display: 'grid', gap: '24px' }}>
          {/* KPI Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            {[
              { label: 'Toplam Ciro', value: `₺${Math.round(data.summary.sales).toLocaleString('tr-TR')}`, icon: <IconCurrencyLira size={20} />, color: '#4f46e5' },
              { label: 'Satış Adedi', value: data.summary.units.toLocaleString('tr-TR'), icon: <IconPackage size={20} />, color: '#10b981' },
              { label: 'Müşteri Sayısı', value: data.summary.customers.toLocaleString('tr-TR'), icon: <IconUsers size={20} />, color: '#f59e0b' },
              { label: 'Ort. Sepet', value: `₺${data.summary.avgTicket.toLocaleString('tr-TR')}`, icon: <IconShoppingCart size={20} />, color: '#ec4899' }
            ].map((kpi, i) => (
              <div key={i} style={{ padding: '20px', background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>{kpi.label}</span>
                  <span style={{ color: kpi.color, opacity: 0.8 }}>{kpi.icon}</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1e293b' }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
            {/* Trend Chart */}
            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '20px' }}>
              <h4 style={{ margin: '0 0 16px', fontSize: '1rem', fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <IconTrendingUp size={20} color="#6366f1" /> Satış Trendi
              </h4>
              <div id="brand-trend-chart" style={{ height: '350px', width: '100%' }}></div>
            </div>

            {/* Category Distribution Hierarchy */}
            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '20px', maxHeight: '420px', overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <IconList size={20} color="#10b981" /> Kategori Dağılımı
                </h4>
                <button 
                  onClick={() => setExpandAll(!expandAll)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '0.7rem',
                    background: '#f1f5f9',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    color: '#64748b',
                    fontWeight: 600
                  }}
                >
                  {expandAll ? 'Tümünü Kapat' : 'Tümünü Aç'}
                </button>
              </div>
              <div style={{ display: 'grid', gap: '4px' }}>
                {data.categoryHierarchy.length > 0 ? (
                  data.categoryHierarchy.map((node, i) => (
                    <CategoryNode key={i} node={node} totalSales={data.summary.sales} brandName={brandName} onExport={handleExportBrandCustomers} defaultOpen={expandAll} />
                  ))
                ) : (
                  <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>Kategori verisi bulunamadı.</div>
                )}
              </div>
            </div>
          </div>

          {/* Top Products Table */}
          <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '20px' }}>
            <h4 style={{ margin: '0 0 16px', fontSize: '1rem', fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <IconTrophy size={20} color="#f59e0b" /> En Çok Satan 10 Ürün
            </h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '2px solid #f1f5f9' }}>
                    <th style={{ padding: '12px', color: '#64748b' }}>Ürün Adı</th>
                    <th style={{ padding: '12px', color: '#64748b', textAlign: 'right' }}>Adet</th>
                    <th style={{ padding: '12px', color: '#64748b', textAlign: 'right' }}>Toplam Ciro</th>
                  </tr>
                </thead>
                <tbody>
                  {data.topProducts.map((prod, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '12px', fontWeight: 500, color: '#1e293b' }}>{prod.name}</td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>{prod.units.toLocaleString('tr-TR')}</td>
                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: 600, color: '#6366f1' }}>₺{Math.round(prod.sales).toLocaleString('tr-TR')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ padding: '60px', textAlign: 'center', color: '#ef4444' }}>
          Veri yüklenirken bir hata oluştu.
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes slideInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        /* Custom Scrollbar */
        div::-webkit-scrollbar {
          width: 6px;
        }
        div::-webkit-scrollbar-track {
          background: #f1f5f9;
        }
        div::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
        }
      `}</style>
      
      {/* GLOBAL EXPORT PROGRESS OVERLAY */}
      {isExporting && (
        <div style={{
          position: 'fixed',
          bottom: '32px',
          right: '32px',
          zIndex: 3000,
          background: 'white',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
          padding: '20px 24px',
          minWidth: '320px',
          border: '1px solid #e0e7ff',
          animation: 'slideInUp 0.3s ease-out'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#1e293b' }}>Excel Hazırlanıyor</div>
              <div style={{ fontSize: '0.78rem', color: '#6366f1', marginTop: '1px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{exportStep}</div>
            </div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#6366f1', flexShrink: 0 }}>{exportProgress}%</div>
          </div>
          <div style={{ width: '100%', height: '6px', background: '#e0e7ff', borderRadius: '99px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${exportProgress}%`,
              background: exportProgress === 100
                ? 'linear-gradient(90deg, #10b981, #059669)'
                : 'linear-gradient(90deg, #6366f1, #8b5cf6)',
              borderRadius: '99px',
              transition: 'width 0.4s ease'
            }} />
          </div>
        </div>
      )}
    </Modal>
  )
}
