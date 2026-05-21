/**
 * MarketFlow Project - Demo Version
 * Developed by Akif - © 2024
 * All rights reserved. Unauthorized reproduction or use is prohibited.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

interface AuthResponse {
  token: string
  user: {
    id: string
    email: string
  }
}

interface DataSourceResponse {
  id: string
  name: string
  type: 'csv' | 'json' | 'database'
  rowCount: number
  uploadedAt: string
}

interface DashboardResponse {
  id: string
  name: string
  description?: string
  widgetCount: number
  createdAt: string
  updatedAt: string
}

export interface DashboardFilters {
  year?: number
  month?: number
  start_date?: string
  end_date?: string
  categories?: string
  brands?: string
  view_mode?: string
  customer_type?: string
  approval_status?: string
  region?: string
}

export interface DashboardSummaryResponse {
  totalRevenue?: number
  totalReceipts?: number
  totalCustomers?: number
  totalRegisteredCustomers?: number
  totalProducts?: number
  totalBrands?: number
  averageOrderValue?: number
  avgTransactionsPerCustomer?: number
  avgRevenuePerCustomer?: number
  loyaltyShare?: number
  churnRate?: number
  salesByMonth?: any[]
  customerSegments?: any[]
  comparisonStats?: any
  breakdown?: any
  everPurchasedCount?: number
  neverPurchasedCount?: number
  kpis?: any
  trend?: any
  comparison?: any
  segments?: any
}

export interface CLVCustomerDetail {
  id: string
  name: string
  totalValue: number
  orderCount: number
  frequency: number
  firstPurchaseDate: string
  lastPurchaseDate: string
  lifespanDays: number
}

export interface CLVDetailsResponse {
  customers: CLVCustomerDetail[]
  total: number
  page: number
  pageSize: number
}

class ApiClient {
  private client: AxiosInstance
  private baseURL: string = (() => {
    let url = import.meta.env.VITE_API_URL || '/api'
    if (!url.endsWith('/api')) {
      url = url.endsWith('/') ? url + 'api' : url + '/api'
    }
    return url
  })()
  private token: string | null = localStorage.getItem('auth_token')

  // Reduce duplicate network calls: dedupe in-flight GETs + short response cache
  private inFlightGets = new Map<string, Promise<AxiosResponse<any>>>()
  private getCache = new Map<string, { timestamp: number; response: AxiosResponse<any> }>()
  private readonly getCacheTtlMs = 120000  // 2 dakika cache - backend ile eşleşiyor

  constructor() {
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 120000, // 120 seconds for heavy brand report queries
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Add token to requests if available
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`
      }
      // Add trailing slash to paths that don't have one
      if (config.url) {
        const [path, query] = config.url.split('?')
        if (!path.endsWith('/')) {
          config.url = path + '/' + (query ? '?' + query : '')
        }
      }
      return config
    })

    // Handle 401 responses
    this.client.interceptors.response.use(
      (response) => {
        return response
      },
      (error) => {
        if (error.response && error.response.status === 401) {
          // In demo mode with demo-token, we don't want to redirect to login
          if (this.token === 'demo-token') {
            console.error('Unauthorized access with demo-token detected. Check backend users.')
            return Promise.reject(error)
          }

          this.clearToken()
          localStorage.removeItem('auth_token')
          if (window.location.pathname !== '/giris' && window.location.pathname !== '/kayit') {
            window.location.href = '/giris'
          }
        }
        return Promise.reject(error)
      }
    )
  }

  setToken(token: string) {
    this.token = token
    localStorage.setItem('auth_token', token)
    this.inFlightGets.clear()
    this.getCache.clear()
  }

  clearToken() {
    this.token = null
    localStorage.removeItem('auth_token')
    this.inFlightGets.clear()
    this.getCache.clear()
  }

  private shouldCacheGet(url: string): boolean {
    const normalizedUrl = url.toLowerCase()
    if (normalizedUrl.includes('/auth/')) return false
    if (normalizedUrl.includes('/search-products')) return false
    // CLV, RFM, Churn gibi CRM analytics sayfaları için cache'i atla - her zaman taze veri
    if (normalizedUrl.includes('/clv')) return false
    if (normalizedUrl.includes('/rfm')) return false
    if (normalizedUrl.includes('/churn')) return false
    // DataSources listesi cache'lenmemeli - her zaman güncel liste
    if (normalizedUrl === '/veri-kaynaklari/' || normalizedUrl === '/veri-kaynaklari') return false

    // Portal endpoints — her ürün/marka/müşteri detayı 2 dk cache'le
    if (normalizedUrl.includes('/urun-portali/')) return true
    if (normalizedUrl.includes('/marka-portali/')) return true
    if (normalizedUrl.includes('/customers/')) return true
    // Products & analytics sayfaları — veri-kaynaklari ile başlayan analiz endpoint'leri
    if (normalizedUrl.includes('/analiz/')) return true
    if (normalizedUrl.includes('/urunler/')) return true
    // Kategori raporu — her kategori detayı ve ağaç 2 dk cache'le
    if (normalizedUrl.includes('/kategori-raporu/')) return true

    // Panel endpoints (KPI, trend, comparison, segments) her zaman taze veri
    if (normalizedUrl.includes('/panel/')) return false

    // Cache analytics-style GETs to avoid rapid duplicate fetches from UI changes
    return normalizedUrl.includes('/datasources/') ||
           normalizedUrl.includes('/dashboard-sqlite') ||
           normalizedUrl.includes('/dashboard/')
  }

  private buildGetKey(url: string, config?: AxiosRequestConfig): string {
    const params = (config?.params ?? null) as any
    // Order params deterministically
    let paramsKey = ''
    try {
      if (params && typeof params === 'object' && !(params instanceof URLSearchParams)) {
        const sortedKeys = Object.keys(params).sort()
        const normalized: Record<string, any> = {}
        for (const k of sortedKeys) normalized[k] = params[k]
        paramsKey = JSON.stringify(normalized)
      } else if (params instanceof URLSearchParams) {
        const entries = Array.from(params.entries()).sort(([a], [b]) => a.localeCompare(b))
        paramsKey = JSON.stringify(entries)
      } else {
        paramsKey = JSON.stringify(params)
      }
    } catch {
      paramsKey = ''
    }
    return `GET:${url}|params:${paramsKey}`
  }

  // Low-level request helpers (for custom endpoints)
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    const key = this.buildGetKey(url, config)
    const shouldCache = this.shouldCacheGet(url)

    if (shouldCache) {
      const cached = this.getCache.get(key)
      if (cached && Date.now() - cached.timestamp < this.getCacheTtlMs) {
        return Promise.resolve(cached.response as AxiosResponse<T>)
      }
    }

    const existing = this.inFlightGets.get(key)
    if (existing) {
      return existing as Promise<AxiosResponse<T>>
    }

    const requestPromise = this.client
      .get<T>(url, config)
      .then((response) => {
        if (shouldCache) {
          this.getCache.set(key, { timestamp: Date.now(), response })
        }
        this.inFlightGets.delete(key)
        return response
      })
      .catch((error) => {
        this.inFlightGets.delete(key)
        throw error
      })

    this.inFlightGets.set(key, requestPromise as Promise<AxiosResponse<any>>)
    return requestPromise
  }

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config)
  }

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config)
  }

  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config)
  }

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config)
  }

  // Auth endpoints
  async register(email: string, password: string) {
    const response = await this.client.post<AuthResponse>('/auth/kayit/', { email, password })
    return response.data
  }

  async login(email: string, password: string) {
    const response = await this.client.post<AuthResponse>('/auth/giris/', { email, password })
    if (response.data.token) {
      this.setToken(response.data.token)
    }
    return response.data
  }

  // DataSources endpoints
  async uploadDataSource(file: File, name: string) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', name)

    return await this.client.post('/veri-kaynaklari/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }

  async createDatabaseSource(payload: {
    name: string
    server: string
    port?: string
    database: string
    username: string
    password: string
    query: string
    encrypt?: boolean
    trustServerCertificate?: boolean
  }, config?: AxiosRequestConfig) {
    return await this.client.post('/veri-kaynaklari/', {
      type: 'database',
      dbType: 'mssql',
      ...payload
    }, config)
  }

  async getDataSources() {
    const response = await this.client.get<{ dataSources: DataSourceResponse[] }>('/veri-kaynaklari/')
    return response.data.dataSources
  }

  async getDataSource(id: string) {
    const response = await this.client.get(`/veri-kaynaklari/${id}/`)
    return response.data
  }

  async getDashboardSqlite(
    year?: number,
    month?: number,
    startDate?: string,
    endDate?: string,
    categories: string[] = [],
    brands: string[] = [],
    viewMode: 'category' | 'brand' = 'category',
    customerType?: string,
    approvalStatus?: string,
    region?: string
  ) {
    const params: any = {}
    if (year) params.year = year
    if (month) params.month = month
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    if (categories && categories.length > 0) params.categories = categories.join(',')
    if (brands && brands.length > 0) params.brands = brands.join(',')
    if (viewMode) params.view_mode = viewMode
    if (customerType) params.customer_type = customerType
    if (approvalStatus) params.approval_status = approvalStatus
    if (region) params.region = region

    // Cache'li get kullan - 2 dakika cache süresi
    const response = await this.get('/panel-sqlite/', { params })
    return response.data
  }

  // Dashboard Unified Summary
  async getDashboardFullSummary(params: DashboardFilters = {}): Promise<DashboardSummaryResponse> {
    const response = await this.get<DashboardSummaryResponse>('/panel-sqlite/', { params });
    return response.data;
  }

  async getDashboardKpis(params: any) {
    const response = await this.get('/panel/kpiler/', { params })
    return response.data
  }

  async getDashboardTrend(params: any) {
    const response = await this.get('/panel/trend/', { params })
    return response.data
  }

  async getDashboardComparison(params: any) {
    const response = await this.get('/panel/karsilastirma/', { params })
    return response.data
  }

  async getDashboardSegments(params: any) {
    const response = await this.get('/panel/segmentler/', { params })
    return response.data
  }

  async getDashboardFilters() {
    const response = await this.get('/panel/filtreler/')
    return response.data
  }

  async getDataSourceAnalytics(
    id: string, 
    segments: string[] = [], 
    categories: string[] = [], 
    brands: string[] = [],
    year?: number,
    month?: number,
    startDate?: string,
    endDate?: string
  ) {
    const params = new URLSearchParams()
    if (segments) segments.forEach(seg => params.append('segments', seg))
    if (categories) categories.forEach(cat => params.append('categories', cat))
    if (brands) brands.forEach(brand => params.append('brands', brand))
    if (year) params.append('year', year.toString())
    if (month) params.append('month', month.toString())
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    
    const url = `/veri-kaynaklari/${id}/analiz/?${params.toString()}`
    const response = await this.get(url)
    return response.data
  }

  async getProductAnalytics(
    id: string,
    categories: string[] = [],
    brands: string[] = [],
    productNames: string[] = [],
    year?: number,
    month?: number,
    startDate?: string,
    endDate?: string,
    customerType?: string,
    approvalStatus?: string,
    region?: string
  ) {
    const params = new URLSearchParams()
    categories.forEach(cat => params.append('categories', cat))
    brands.forEach(brand => params.append('brands', brand))
    productNames.forEach(prod => params.append('product_names', prod))
    if (year) params.append('year', year.toString())
    if (month) params.append('month', month.toString())
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    if (customerType) params.append('customer_type', customerType)
    if (approvalStatus) params.append('approval_status', approvalStatus)
    if (region) params.append('region', region)

    const url = `/veri-kaynaklari/${id}/urunler/?${params.toString()}`
    const response = await this.client.get(url)
    return response.data
  }

  async exportBrandCustomers(brand: string, category: string, level: 'ana' | 'alt1' | 'alt2') {
    const params = new URLSearchParams()
    params.append('brand', brand)
    params.append('category', category)
    params.append('level', level)

    const url = `/marka-musteri-listesi/?${params.toString()}`
    const response = await this.client.get(url, { responseType: 'blob' })
    return response
  }

  async deleteDataSource(id: string) {
    return await this.client.delete(`/veri-kaynaklari/${id}/`)
  }

  async updateDataSourceColumnMapping(id: string, columnMapping: Record<string, string>) {
    const response = await this.client.patch(`/veri-kaynaklari/${id}/`, { column_mapping: columnMapping })
    return response.data
  }

  // Dashboards endpoints
  async createDashboard(name: string, description?: string) {
    const response = await this.client.post<{ dashboard: DashboardResponse }>(
      '/paneller/',
      { name, description }
    )
    return response.data.dashboard
  }

  async getDashboards() {
    const response = await this.client.get<{ dashboards: DashboardResponse[] }>('/paneller/')
    return response.data.dashboards
  }

  async getDashboard(id: string) {
    const response = await this.client.get(`/paneller/${id}/`)
    return response.data
  }

  async updateDashboard(id: string, name: string, description?: string) {
    const response = await this.client.put(`/paneller/${id}/`, { name, description })
    return response.data
  }

  async deleteDashboard(id: string) {
    return await this.client.delete(`/paneller/${id}/`)
  }


  // Query endpoints
  async query(
    dataSourceId: string,
    field?: string,
    aggregation?: 'sum' | 'average' | 'count' | 'min' | 'max',
    groupBy?: string,
    filters?: Record<string, any>
  ) {
    const response = await this.client.post('/sorgu/', {
      dataSourceId,
      field,
      aggregation,
      groupBy,
      filters
    })
    return response.data
  }

  // CRM Analytics endpoints
  async getRFMAnalysis(dataSourceId: string, filters?: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/rfm-analizi/`, { params: filters })
    return response.data
  }

  async getChurnAnalysis(dataSourceId: string, filters?: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/churn-analizi/`, { params: filters })
    return response.data
  }

  async getCLVAnalysis(dataSourceId: string, filters?: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/clv-analizi/`, { params: filters })
    return response.data
  }

  async getCLVSegmentDetails(
    dataSourceId: string,
    segment: string,
    page: number = 1,
    limit: number = 20,
    filters?: Record<string, any>
  ): Promise<CLVDetailsResponse> {
    const params = {
      segment,
      page,
      limit,
      ...filters
    }
    const { data } = await this.client.get<CLVDetailsResponse>(`/veri-kaynaklari/${dataSourceId}/clv-analizi/detaylar/`, { params })
    return data
  }

  async getBrandReport(dataSourceId: string, filters?: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/markalar/`, { params: filters })
    return response.data
  }

  async getSegmentationAnalysis(dataSourceId: string, filters?: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/segmentasyon/`, { params: filters })
    return response.data
  }

  async getBrandSuggestions(dataSourceId: string, query: string) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/markalar/oneriler/`, { params: { q: query } })
    return response.data
  }

  async getBrandDetail(dataSourceId: string, filters: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/markalar/detay/`, { params: filters })
    return response.data
  }

  async getProductPortal(dataSourceId: string, productId: number, filters?: Record<string, any>) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/urun-portali/${productId}/`, { params: filters })
    return response.data
  }

  async searchProducts(dataSourceId: string, query: string, limit: number = 50) {
    const params = new URLSearchParams()
    params.append('q', query)
    params.append('limit', limit.toString())

    const url = `/veri-kaynaklari/${dataSourceId}/urun-ara/?${params.toString()}`
    const response = await this.client.get(url)
    return response.data
  }

  async getCategoryDetails(dataSourceId: string, categoryName: string, level: string = 'ana', strategy?: string) {
    const params: any = { name: categoryName, level }
    if (strategy) params.strategy = strategy
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/kategori-raporu/`, { params })
    return response.data
  }

  async getCategoryAnalysis(categoryName: string, level: string = 'primary') {
    const response = await this.client.get('/analiz/kategori-ozet/', { params: { name: categoryName, level } })
    return response.data
  }

  async getBrandAnalysis(brandName: string) {
    const response = await this.client.get('/analiz/marka-ozet/', { params: { name: brandName } })
    return response.data
  }

  async getCategoryTree(dataSourceId: string) {
    const response = await this.get(`/veri-kaynaklari/${dataSourceId}/kategori-raporu/agac/`)
    return response.data
  }

  async handleCategoryTag(dataSourceId: string, categoryId: string, tag: string, action: 'add' | 'remove') {
    const response = await this.client.post(`/veri-kaynaklari/${dataSourceId}/kategori-raporu/etiketler/`, { category_id: categoryId, tag, action })
    return response.data
  }

  // --- CRM Customers ---
  async getCustomers(dataSourceId: string, page: number = 1, limit: number = 50, filters?: Record<string, any>) {
    const params = {
      page,
      limit,
      ...filters
    }
    const response = await this.client.get(`/veri-kaynaklari/${dataSourceId}/musteriler/`, { params })
    return response.data
  }

  // Campaign Recommendations
  async getCampaignRecommendations(
    status: string = 'Bekliyor',
    type: string = 'Tümü',
    category: string = 'all',
    kategoriYoneticisi: string = 'all',
    brand: string = 'all',
    page: number = 1,
    limit: number = 50,
    sortBy: string = 'default',
    sortOrder: 'ASC' | 'DESC' = 'DESC',
    minLift: number = 0,
    minConfidence: number = 0,
    minFis: number = 0,
    brandBothSides: boolean = false
  ) {
    const response = await this.client.get('/kampanya-onerileri/', {
      params: {
        status, type, category, yonetici: kategoriYoneticisi, brand, page, limit,
        sort_by: sortBy,
        sort_order: sortOrder,
        min_lift: minLift,
        min_confidence: minConfidence,
        min_fis: minFis,
        brand_both_sides: brandBothSides
      }
    })
    return response.data
  }

  async getCampaignCounts(status: string = 'Bekliyor') {
    const response = await this.client.get('/kampanya-onerileri/sayilar/', {
      params: { status }
    })
    return response.data
  }

  async getCampaignSourceCategories(params: Record<string, any>) {
    const response = await this.client.get('/kampanya-onerileri/kategoriler/', { params })
    return response.data
  }

  async getCampaignFilterCounts(status: string = 'Bekliyor', type: string = 'Cross-Sell') {
    const response = await this.client.get('/kampanya-onerileri/filtre-sayilari/', {
      params: { status, type }
    })
    return response.data
  }

  async updateRecommendationStatus(id: number, status: string) {
    const response = await this.client.post(`/kampanya-onerileri/${id}/durum/`, { status })
    return response.data
  }

  async bulkUpdateRecommendationStatus(ids: number[], status: string) {
    const response = await this.client.post('/kampanya-onerileri/toplu-durum/', { ids, status })
    return response.data
  }

  async getCampaignAiSummary(id: number) {
    const response = await this.get(`/kampanya-onerileri/${id}/ai-ozet/`)
    return response.data
  }

  async getCampaignAiSummaryV2(id: number) {
    const response = await this.get(`/kampanya-onerileri/${id}/ai-ozet-v2/`)
    return response.data
  }

  async getCategoryHierarchy() {
    const response = await this.client.get('/kampanya-onerileri/kategori-hiyerarsisi/')
    return response.data
  }

  async getCategoryTopProducts(name: string) {
    const response = await this.client.get('/kampanya-onerileri/kategori-urunleri/', { params: { name } })
    return response.data
  }

  async getKategoriYoneticileri() {
    const response = await this.client.get('/filters/kategori-yoneticileri/')
    return response.data
  }

  async getBrands() {
    const response = await this.client.get('/filters/markalar/')
    return response.data
  }

  // --- Settings ---
  async getSettings() {
    const response = await this.get('/ayarlar/')
    return response.data
  }

  async updateSettings(settings: Record<string, any>) {
    const response = await this.client.post('/ayarlar/', settings)
    return response.data
  }

  async getProfile() {
    const response = await this.client.get('/auth/profil/')
    return response.data
  }

  async updateProfile(data: { password?: string, first_name?: string, last_name?: string }) {
    const response = await this.client.post('/auth/profil/', data)
    return response.data
  }

  async detectAnomalies(dataSourceId: number = 0) {
    const response = await this.get('/ai/anomaliler/', { params: { data_source_id: dataSourceId } })
    return response.data
  }

  // --- AI Notifications (Sprint 10) ---
  async getNotifications() {
    return await this.get('/ai/bildirimler/')
  }

  async syncNotifications(dataSourceId: number = 0) {
    return await this.post('/ai/bildirimler/sync/', { data_source_id: dataSourceId })
  }

  async markNotificationRead(id: number) {
    return await this.post(`/ai/bildirimler/${id}/okundu/`)
  }

  // --- Campaign Orchestration (Sprint 11) ---
  async getScheduledCampaigns() {
    const response = await this.client.get('/ai/kampanya/listele/')
    return response.data
  }

  async scheduleCampaign(data: {
    title: string,
    description: string,
    segment: string,
    channel: string,
    scheduled_at?: string
  }) {
    const response = await this.client.post('/ai/kampanya/planla/', data)
    return response.data
  }

  async deleteScheduledCampaign(id: number, cancelOnly: boolean = false) {
    if (cancelOnly) {
      const response = await this.client.post(`/ai/kampanya/${id}/sil/`)
      return response.data
    }
    const response = await this.client.delete(`/ai/kampanya/${id}/sil/`)
    return response.data
  }

  async runScheduledCampaign(id: number) {
    const response = await this.client.post(`/ai/kampanya/${id}/calistir/`)
    return response.data
  }

  // --- AI Dashboards (Sprint 12) ---
  async getAIDashboards() {
    const response = await this.get('/ai/paneller/')
    return response.data.dashboards
  }

  async getAIDashboard(id: number) {
    const response = await this.get(`/ai/paneller/${id}/`)
    return response.data.dashboard
  }

  async deleteAIDashboard(id: number) {
    return await this.delete(`/ai/paneller/${id}/sil/`)
  }

  async toggleAIDashboardFavorite(id: number) {
    return await this.post(`/ai/paneller/${id}/favori/`)
  }

  async getAIUsageStats() {
    const response = await this.get('/ai/kullanim/')
    return response.data
  }

  // --- Store Analysis ---
  async getStoreAnalysis(params: { 
    region?: string; 
    start_date?: string; 
    end_date?: string;
    customer_type?: string;
    approval_status?: string;
  }) {
    const response = await this.client.get('/magaza-analizi/', { params })
    return response.data
  }
}

export default new ApiClient()

