/**
 * Comprehensive TypeScript Type Definitions
 * API Models, Request/Response types for the entire application
 */

// ============================================================================
// Authentication Types
// ============================================================================

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  confirmPassword?: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface User {
  id: number
  email: string
  username?: string
}

// ============================================================================
// Data Source Types
// ============================================================================

export type DataSourceType = 'csv' | 'json' | 'database'

export interface DataSource {
  id: number
  name: string
  type: DataSourceType
  data: any[]
  column_mapping?: ColumnMapping
  connection_info?: DatabaseConnectionInfo
  uploaded_at: string
  user: number
}

export interface ColumnMapping {
  [key: string]: string
}

export interface DatabaseConnectionInfo {
  server: string
  port: number
  database: string
  username: string
  encrypt?: boolean
  trustServerCertificate?: boolean
}

export interface DatabaseFormData {
  name: string
  server: string
  port: string
  database: string
  username: string
  password: string
  encrypt: boolean
  trustServerCertificate: boolean
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface Dashboard {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at: string
  user: number
}

// ============================================================================
// Analytics Types
// ============================================================================

export interface FilterState {
  startDate?: string
  endDate?: string
  year?: number
  month?: number
  category?: string
  segment?: string[]
  brand?: string
}

export interface AnalyticsData {
  revenue: RevenueData
  orders: OrdersData
  customers: CustomersData
  topProducts: ProductData[]
  categoryData: CategoryData[]
  brandData: BrandData[]
  timeSeriesData: TimeSeriesData[]
  customerSegments: SegmentData[]
  categoryHierarchy: CategoryHierarchy
  summary?: AnalyticsSummary
}

export interface RevenueData {
  total: number
  growth?: number
  trend?: 'up' | 'down' | 'stable'
}

export interface OrdersData {
  total: number
  growth?: number
  avgOrderValue?: number
}

export interface CustomersData {
  total: number
  new?: number
  returning?: number
  growth?: number
}

export interface ProductData {
  id?: number
  name: string
  revenue: number
  quantity: number
  category?: string
  brand?: string
  avgPrice?: number
}

export interface CategoryData {
  name: string
  revenue: number
  count?: number
  level?: string
  percentage?: number
}

export interface BrandData {
  name: string
  revenue: number
  count?: number
  percentage?: number
}

export interface TimeSeriesData {
  date: string
  revenue: number
  orders?: number
  customers?: number
}

export interface SegmentData {
  segment: string
  count: number
  revenue: number
  percentage: number
  color?: string
}

export interface CategoryHierarchy {
  [parentCategory: string]: {
    [mainCategory: string]: {
      [alt1Category: string]: {
        [alt2Category: string]: {
          revenue: number
          count: number
        }
      }
    }
  }
}

export interface AnalyticsSummary {
  totalRevenue: number
  totalOrders: number
  totalCustomers: number
  avgOrderValue: number
  period: {
    start: string
    end: string
  }
}

// ============================================================================
// RFM Analysis Types
// ============================================================================

export interface RFMAnalysisData {
  summary: RFMSummary
  segments: RFMSegment[]
  distribution: RFMDistribution
  customers?: RFMCustomer[]
}

export interface RFMSummary {
  totalCustomers: number
  avgRecency: number
  avgFrequency: number
  avgMonetary: number
}

export interface RFMSegment {
  segment: string
  count: number
  avgRecency: number
  avgFrequency: number
  avgMonetary: number
  totalRevenue: number
  percentage: number
  color: string
}

export interface RFMDistribution {
  recency: number[]
  frequency: number[]
  monetary: number[]
}

export interface RFMCustomer {
  customerId: string
  name?: string
  recency: number
  frequency: number
  monetary: number
  rfmScore: number
  segment: string
}

// ============================================================================
// Churn Analysis Types
// ============================================================================

export interface ChurnAnalysisData {
  summary: ChurnSummary
  riskSegments: ChurnRiskSegment[]
  timeSeriesData: ChurnTimeSeriesData[]
  factors: ChurnFactor[]
}

export interface ChurnSummary {
  churnRate: number
  atRiskCount: number
  retentionRate: number
  totalCustomers: number
}

export interface ChurnRiskSegment {
  risk: 'low' | 'medium' | 'high'
  count: number
  percentage: number
  avgDaysSinceLastOrder: number
}

export interface ChurnTimeSeriesData {
  date: string
  churnRate: number
  newCustomers: number
  lostCustomers: number
}

export interface ChurnFactor {
  factor: string
  impact: number
  description: string
}

// ============================================================================
// CLV (Customer Lifetime Value) Types
// ============================================================================

export interface CLVData {
  summary: CLVSummary
  distribution: CLVDistribution[]
  topCustomers: CLVCustomer[]
  factors: CLVFactor[]
}

export interface CLVSummary {
  averageCLV: number
  totalCLV: number
  medianCLV: number
  highValueCustomers: number
}

export interface CLVDistribution {
  range: string
  count: number
  percentage: number
  totalValue: number
}

export interface CLVCustomer {
  customerId: string
  name?: string
  clv: number
  totalOrders: number
  totalRevenue: number
  avgOrderValue: number
}

export interface CLVFactor {
  factor: string
  weight: number
  color: string
}

// ============================================================================
// Customer Segmentation Types
// ============================================================================

export interface SegmentationData {
  segments: CustomerSegment[]
  summary: SegmentationSummary
  behavioralPatterns: BehavioralPattern[]
}

export interface CustomerSegment {
  id: string
  name: string
  count: number
  revenue: number
  avgOrderValue: number
  avgFrequency: number
  percentage: number
  characteristics: string[]
  color: string
}

export interface SegmentationSummary {
  totalSegments: number
  mostProfitable: string
  largest: string
  fastestGrowing: string
}

export interface BehavioralPattern {
  pattern: string
  segments: string[]
  prevalence: number
}

// ============================================================================
// Campaign Analysis Types
// ============================================================================

export interface CampaignData {
  campaigns: Campaign[]
  summary: CampaignSummary
  performance: CampaignPerformance[]
}

export interface Campaign {
  id: string
  name: string
  startDate: string
  endDate?: string
  status: 'active' | 'completed' | 'planned'
  targetSegment: string
  results?: CampaignResults
}

export interface CampaignResults {
  revenue: number
  conversions: number
  reach: number
  roi: number
}

export interface CampaignSummary {
  totalCampaigns: number
  activeCampaigns: number
  totalRevenue: number
  avgROI: number
}

export interface CampaignPerformance {
  date: string
  revenue: number
  conversions: number
  clicks: number
}

// ============================================================================
// CRM Types
// ============================================================================

export interface PaginatedResponse<T> {
  data: T[]
  pagination: PaginationInfo
}

export interface PaginationInfo {
  page: number
  pageSize: number
  totalPages: number
  totalRecords: number
  hasNext: boolean
  hasPrevious: boolean
}

export interface PaginationParams {
  page?: number
  pageSize?: number
  search?: string
  sortBy?: string
  sortDir?: 'ASC' | 'DESC'
}

// ============================================================================
// Chart Types
// ============================================================================

export interface ChartData {
  labels: string[]
  datasets: ChartDataset[]
}

export interface ChartDataset {
  label: string
  data: number[]
  backgroundColor?: string | string[]
  borderColor?: string | string[]
  borderWidth?: number
}

export interface ChartOptions {
  responsive?: boolean
  maintainAspectRatio?: boolean
  plugins?: any
  scales?: any
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
  status?: number
}

export interface ErrorResponse {
  error: string
  type?: string
  details?: any
}

// ============================================================================
// Utility Types
// ============================================================================

export type SortDirection = 'ASC' | 'DESC'
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

export interface RequestState<T> {
  data: T | null
  loading: boolean
  error: string | null
}
// ============================================================================
// Campaign Recommendation Types
// ============================================================================

export interface CampaignRecommendation {
  OneriID: number
  OlusturmaTarihi: string
  KampanyaTipi: string
  HedefSegment: string
  HedefMusteriSayisi: number
  OncelikSeviye: number
  UrunID?: number
  UrunAdi?: string
  KategoriID?: number
  KategoriAdi?: string
  IkinciUrunID?: number
  IkinciUrunAdi?: string
  KaynakKategoriAd?: string
  VeriKaynagi: string
  OnerilenIndirim: number
  OnerilenMinTutar: number
  TahminiKatilim: number
  PotansiyelCiro: number
  TahminiKar: number
  ROITahmini: number
  Gerekcesi: string
  VeriOzeti: string
  OnerilenUrunler?: string
  BeklenenSonuc: string
  OneriDurumu: 'Bekliyor' | 'Onaylandi' | 'Reddedildi' | 'Uygulandi'
  KampanyaID?: number
  Lift?: number
  Guven?: number
  FisSayisi?: number
  SonGuncelleme: string
}
