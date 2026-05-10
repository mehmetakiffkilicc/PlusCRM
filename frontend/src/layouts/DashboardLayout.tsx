import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate, Outlet } from 'react-router-dom'
import { useDisclosure } from '@mantine/hooks'
import useAuthStore from '../stores/authStore'
import useDashboardStore from '../stores/dashboardStore'
import useUIStore from '../stores/uiStore'
import useNotificationStore from '../stores/notificationStore'
import apiClient from '../api/client'
import FilterPanel from '../components/FilterPanel'
import InlineSpinner from '../components/InlineSpinner'
import { ChatWidget } from '../components/ai/ChatWidget'
import { NotificationCenter } from '../components/ai/NotificationCenter'
import { useChatStore } from '../stores/chatStore'
import {
  NavLink,
  Avatar,
  Tooltip,
  Text,
  Title,
  Group,
  Indicator,
  ActionIcon,
} from '@mantine/core'
import {
  IconLayoutDashboard,
  IconBox,
  IconChartBar,
  IconAlertTriangle,
  IconCoin,
  IconTarget,
  IconTag,
  IconCategory,
  IconSpeakerphone,
  IconUserPlus,
  IconUsers,
  IconSparkles,
  IconSettings,
  IconRocket,
  IconLogout,
  IconChevronLeft,
  IconChevronDown,
  IconCalendarStats,
  IconLink,
  IconDiamond,
  IconFlame,
  IconShieldX,
  IconHome,
  IconBell,
  IconCalendar,
  IconMenu2,
  IconX,
  IconBuildingStore,
} from '@tabler/icons-react'
import '../styles/DashboardLayout.css'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Ana Sayfa',
  '/urunler': 'Ürün Analizi',
  '/rfm-analizi': 'RFM Analizi',
  '/churn-analizi': 'Churn Analizi',
  '/clv-analizi': 'Müşteri Yaşam Boyu Değeri (CLV)',
  '/segmentasyon': 'Müşteri Segmentasyonu',
  '/kampanyalar': 'Kampanya Yönetimi',
  '/yeni-musteriler': 'Yeni Müşteri Analizi',
  '/marka-raporu': 'Marka Performans Raporu',
  '/kategori-raporu': 'Kategori Analiz Merkezi',
  '/musteri-portali': 'Müşteri Zekası Portalı',
  '/kampanya-onerileri': 'Akıllı Kampanya Önerileri',
  '/kohort-analizi': 'Kohort Retention Analizi',
  '/urun-birliktelik': 'Ürün Birliktelik Analizi (MBA)',
  '/marka-sadakati': 'Marka Sadakati Analizi',
  '/enflasyon-profil': 'Enflasyon Dayanıklılık Profili',
  '/rakip-riski': 'Rakip Riski Analizi',
  '/ayarlar': 'Ayarlar',
  '/ai-paneller': 'Özel AI Panelleri',
  '/ai-takvim': 'Kampanya Takvimi',
  '/magaza-analizi': 'Mağaza Analiz Merkezi',
}

type NavDivider = { type: 'divider' }
type NavItem = {
  id: string
  label: string
  icon: React.ElementType
  path: string
  type?: undefined
  children?: NavItem[]
}
type NavGroup = {
  id: string
  label: string
  icon: React.ElementType
  type: 'group'
  children: NavItem[]
}
type NavEntry = NavDivider | NavItem | NavGroup

export default function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { selectedDataSourceId, setSelectedDataSourceId, setDataSources } = useDashboardStore()

  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [canScrollDown, setCanScrollDown] = useState(false)
  const navRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 1024)
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const checkScroll = () => {
    if (navRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = navRef.current
      setCanScrollDown(scrollHeight - Math.ceil(scrollTop) > clientHeight + 2)
    }
  }

  useEffect(() => {
    const timer = setTimeout(checkScroll, 100)
    window.addEventListener('resize', checkScroll)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', checkScroll)
    }
  }, [isSidebarOpen])

  useEffect(() => {

    const sourcesPromise = apiClient.getDataSources()
      .then(sources => {
        if (sources && sources.length > 0) {
          const normalizedSources = sources.map((s: any) => ({ ...s, id: s.id.toString() }))
          setDataSources(normalizedSources)
          const firstId = normalizedSources[0].id
          const validSource = normalizedSources.find((s: any) => s.id === selectedDataSourceId)
          if (!validSource || !selectedDataSourceId) setSelectedDataSourceId(firstId)
        }
      })
      .catch(e => console.error('Failed to load data sources', e))

    const filtersPromise = apiClient.getDashboardFilters()
      .then(data => {
        if (data) {
          const store = useDashboardStore.getState()
          if (data.availableYears) store.setAvailableYears(data.availableYears)
          if (data.availableRegions) store.setAvailableRegions(data.availableRegions)
          if (data.availableCustomerTypes) store.setAvailableCustomerTypes(data.availableCustomerTypes)
          if (data.availableApprovalStatuses) store.setAvailableApprovalStatuses(data.availableApprovalStatuses)
        }
      })
      .catch(err => console.error('Failed to load global filter data', err))

    Promise.all([sourcesPromise, filtersPromise])
  }, [])

  // Bildirimleri Otomatik Senkronize Et (Sprint 10)
  const [notifOpened, { open: openNotif, close: closeNotif }] = useDisclosure(false)
  const { unreadCount, syncNotifications } = useNotificationStore()
  
  useEffect(() => {
    if (selectedDataSourceId) {
      // Sayfa yüklendiğinde bir kez anomalileri tara ve bildirimleri çek
      syncNotifications(Number(selectedDataSourceId))
    }
  }, [selectedDataSourceId])

  // AI için global bağlamı (context) güncelle: Her sayfa ve veri kaynağı değişiminde AI'yı haberdar et
  useEffect(() => {
    const { attachPageContext } = useChatStore.getState();
    const pageKey = location.pathname;
    const pageTitle = PAGE_TITLES[pageKey] || 'Dashboard';
    
    attachPageContext(pageTitle, {
      page: pageKey,
      data_source_id: selectedDataSourceId,
      timestamp: new Date().toISOString(),
      user_email: user?.email
    });
  }, [location.pathname, selectedDataSourceId]);

  const currentTitle = PAGE_TITLES[location.pathname] || 'Dashboard'

  const navItems: NavEntry[] = [
    {
      id: 'g-dashboard',
      label: 'Gösterge & CRM',
      icon: IconLayoutDashboard,
      type: 'group',
      children: [
         { id: 'home', label: 'Ana Sayfa', icon: IconHome, path: '/' },
         { id: 'customerportal', label: 'Müşteri Portalı', icon: IconUsers, path: '/musteri-portali' },
         { id: 'aipaneller', label: 'AI Paneller', icon: IconLayoutDashboard, path: '/ai-paneller' },
        { id: 'aitakvim', label: 'Kampanya Takvimi', icon: IconCalendar, path: '/ai-takvim' },
      ],
    },
    { type: 'divider' },
    {
      id: 'g-strategy',
      label: 'Stratejik Analiz',
      icon: IconTarget,
      type: 'group',
      children: [
        { id: 'kohort', label: 'Kohort Analizi', icon: IconCalendarStats, path: '/kohort-analizi' },
        { id: 'birliktelik', label: 'Ürün Birliktelik', icon: IconLink, path: '/urun-birliktelik' },
        { id: 'enflasyon', label: 'Enflasyon Profili', icon: IconFlame, path: '/enflasyon-profil' },
        { id: 'rakipriski', label: 'Rakip Riski', icon: IconShieldX, path: '/rakip-riski' },
        { id: 'hane', label: 'Hane Analizi', icon: IconHome, path: '/hane-analizi' },
        { id: 'magazaanalizi', label: 'Mağaza Analizi', icon: IconBuildingStore, path: '/magaza-analizi' },
      ],
    },
    { type: 'divider' },
    {
      id: 'g-intelligence',
      label: 'Müşteri Zekası',
      icon: IconUsers,
      type: 'group',
      children: [
        { id: 'segmentation', label: 'Segmentasyon', icon: IconTarget, path: '/segmentasyon' },
        { id: 'rfm', label: 'RFM Analizi', icon: IconChartBar, path: '/rfm-analizi' },
        { id: 'clv', label: 'CLV Analizi', icon: IconCoin, path: '/clv-analizi' },
        { id: 'churn', label: 'Churn Analizi', icon: IconAlertTriangle, path: '/churn-analizi' },
        { id: 'brandsadakat', label: 'Marka Sadakati', icon: IconDiamond, path: '/marka-sadakati' },
        { id: 'newcustomers', label: 'Yeni Müşteriler', icon: IconUserPlus, path: '/yeni-musteriler' },
      ],
    },
    { type: 'divider' },
    {
      id: 'g-reports',
      label: 'Raporlar',
      icon: IconBox,
      type: 'group',
      children: [
        { id: 'products', label: 'Ürün Analizi', icon: IconBox, path: '/urunler' },
        { id: 'categoryreport', label: 'Kategori Raporu', icon: IconCategory, path: '/kategori-raporu' },
        { id: 'brandreport', label: 'Marka Raporu', icon: IconTag, path: '/marka-raporu' },
      ],
    },
    { type: 'divider' },
    {
      id: 'g-actions',
      label: 'Aksiyon',
      icon: IconSpeakerphone,
      type: 'group',
      children: [
        { id: 'campaigns', label: 'Kampanyalar', icon: IconSpeakerphone, path: '/kampanyalar' },
        { id: 'smartcampaigns', label: 'Kampanya Önerileri', icon: IconSparkles, path: '/kampanya-onerileri' },
      ],
    },
    { type: 'divider' },
    {
      id: 'g-mgmt',
      label: 'Sistem',
      icon: IconSettings,
      type: 'group',
      children: [
        { id: 'settings', label: 'Ayarlar (Demo)', icon: IconSettings, path: '/ayarlar' },
      ],
    },
  ]

  const sidebarOpen = isMobile ? isMobileSidebarOpen : isSidebarOpen

  return (
    <div className="dashboard-container">
      {/* Mobile overlay backdrop */}
      {isMobile && isMobileSidebarOpen && (
        <div
          className="mobile-sidebar-overlay"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside className={`dashboard-sidebar ${sidebarOpen ? 'open' : 'closed'}${isMobile ? ' mobile' : ''}`}>
        {/* Logo */}
        <div className="sidebar-header">
          <div className="logo-container">
            <span className="logo-icon">
              <IconRocket size={20} stroke={2} color="#fff" />
            </span>
            {sidebarOpen && <span className="logo-text">MarketFlow</span>}
          </div>
          {!isMobile && (
            <button
              className="toggle-sidebar"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              title={isSidebarOpen ? 'Daralt' : 'Genişlet'}
            >
              <IconChevronLeft
                size={18}
                stroke={2}
                style={{
                  transition: 'transform 0.3s',
                  transform: isSidebarOpen ? 'rotate(0deg)' : 'rotate(180deg)',
                }}
              />
            </button>
          )}
          {isMobile && (
            <button
              className="toggle-sidebar"
              onClick={() => setIsMobileSidebarOpen(false)}
              title="Kapat"
            >
              <IconX size={18} stroke={2} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav" ref={navRef} onScroll={checkScroll}>
          {navItems.map((entry, idx) => {
            if (entry.type === 'divider') {
              return <div key={idx} className="nav-divider" />
            }

            if (entry.type === 'group') {
              const GroupIcon = entry.icon
              const isGroupActive = entry.children.some(child => location.pathname === child.path)

              if (!isSidebarOpen) {
                return (
                  <Tooltip key={entry.id} label={entry.label} position="right" withArrow zIndex={100}>
                    <NavLink
                      label={undefined}
                      leftSection={<GroupIcon size={20} stroke={1.8} />}
                      active={isGroupActive}
                      classNames={{ root: 'sidebar-nav-link' }}
                    />
                  </Tooltip>
                )
              }

              return (
                <NavLink
                  key={entry.id}
                  label={entry.label}
                  leftSection={<GroupIcon size={20} stroke={1.8} />}
                  childrenOffset={28}
                  defaultOpened={isGroupActive}
                  classNames={{
                    root: 'sidebar-nav-link group-header',
                    label: 'sidebar-nav-label-group',
                  }}
                >
                  {entry.children.map(child => {
                    const ChildIcon = child.icon
                    const isChildActive = location.pathname === child.path
                    return (
                      <NavLink
                        key={child.id}
                        active={isChildActive}
                        label={child.label}
                        leftSection={<ChildIcon size={18} stroke={1.5} />}
                        onClick={() => { navigate(child.path); if (isMobile) setIsMobileSidebarOpen(false) }}
                        classNames={{
                          root: 'sidebar-nav-link-sub',
                          label: 'sidebar-nav-label-sub',
                        }}
                      />
                    )
                  })}
                </NavLink>
              )
            }

            const Icon = entry.icon
            const isActive = location.pathname === entry.path

            const navLink = (
              <NavLink
                key={entry.id}
                active={isActive}
                label={sidebarOpen ? entry.label : undefined}
                leftSection={<Icon size={20} stroke={1.8} />}
                onClick={() => { navigate(entry.path); if (isMobile) setIsMobileSidebarOpen(false) }}
                classNames={{
                  root: 'sidebar-nav-link',
                  label: 'sidebar-nav-label',
                  section: 'sidebar-nav-section',
                }}
              />
            )

            if (!isSidebarOpen) {
              return (
                <Tooltip key={entry.id} label={entry.label} position="right" withArrow zIndex={100}>
                  {navLink}
                </Tooltip>
              )
            }

            return navLink
          })}
        </nav>

        {canScrollDown && (
          <div className="sidebar-scroll-indicator" onClick={() => {
            navRef.current?.scrollBy({ top: 150, behavior: 'smooth' })
          }} title="Daha fazla seçenek için kaydırın">
            <IconChevronDown size={18} stroke={2} className="pulsing-arrow" />
          </div>
        )}

        {/* User Profile Footer */}
        <div className="sidebar-footer">
          <div className="user-profile">
            <Avatar
              size="sm"
              radius="xl"
              color="indigo"
              style={{ flexShrink: 0 }}
            >
              D
            </Avatar>
            {isSidebarOpen && (
              <div className="user-info">
                <Text size="xs" fw={600} c="#f1f5f9" truncate style={{ maxWidth: 140 }}>
                  Demo User
                </Text>
                <Text size="10px" c="dimmed">
                  MarketFlow Demo
                </Text>
              </div>
            )}
          </div>
          
          {isSidebarOpen && (
            <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.05)', marginTop: '8px' }}>
              <Text size="10px" c="dimmed" style={{ textAlign: 'center', fontStyle: 'italic' }}>
                Developed by Akif<br/>
                © 2024 MarketFlow Project
              </Text>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="dashboard-main">
        {/* Header — Page title + Filters */}
        <header className="dashboard-header">
          {isMobile && (
            <button
              className="mobile-hamburger"
              onClick={() => setIsMobileSidebarOpen(true)}
              title="Menüyü Aç"
            >
              <IconMenu2 size={22} stroke={2} />
            </button>
          )}
          <div className="header-title-area">
            <Group gap="xs">
              <Text size="xs" fw={500} c="dimmed" tt="uppercase" lts="0.5px">
                MarketFlow
              </Text>
              <div style={{ 
                background: 'linear-gradient(45deg, #4f46e5, #06b6d4)', 
                color: 'white', 
                fontSize: '10px', 
                padding: '2px 8px', 
                borderRadius: '12px', 
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Demo Mode
              </div>
            </Group>
            <Title order={5} c="#0f172a" style={{ whiteSpace: 'nowrap' }}>
              {currentTitle}
            </Title>
          </div>

          <div className="header-filter-area">

            <FilterPanel
              availableYears={useDashboardStore(state => state.availableYears)}
              availableMonths={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}
              availableCustomerTypes={useDashboardStore(state => state.availableCustomerTypes)}
              availableApprovalStatuses={useDashboardStore(state => state.availableApprovalStatuses)}
              availableRegions={useDashboardStore(state => state.availableRegions)}
              initialFilters={{
                year: useDashboardStore(state => state.selectedYear),
                month: useDashboardStore(state => state.selectedMonth),
                startDate: useDashboardStore(state => state.selectedStartDate),
                endDate: useDashboardStore(state => state.selectedEndDate),
                segments: useDashboardStore(state => state.selectedSegments),
                categories: useDashboardStore(state => state.selectedCategories),
                brands: useDashboardStore(state => state.selectedBrands),
                customerType: useDashboardStore(state => state.selectedCustomerType),
                approvalStatus: useDashboardStore(state => state.selectedApprovalStatus),
                region: useDashboardStore(state => state.selectedRegion),
              }}
              onFilterChange={(filters) => {
                const store = useDashboardStore.getState()
                if (Object.keys(filters).length === 0) {
                  store.resetFilters()
                  return
                }
                store.setSelectedYear(filters.year)
                store.setSelectedMonth(filters.month)
                store.setDateRange(filters.startDate, filters.endDate)
                store.setSelectedSegments(filters.segments || [])
                store.setSelectedCategories(filters.categories || [])
                store.setSelectedBrands(filters.brands || [])
                store.setSelectedCustomerType(filters.customerType)
                store.setSelectedApprovalStatus(filters.approvalStatus)
                store.setSelectedRegion(filters.region)
              }}
              showApplyButton={true}
              showYearFilter={true}
              showMonthFilter={true}
              showDateRangeFilter={true}
              showCustomerTypeFilter={true}
              showApprovalStatusFilter={true}
              showRegionFilter={true}
              showCategoryFilter={[
                '/urunler',
                '/yeni-musteriler',
                '/musteri-bilgisi',
                '/kampanyalar',
              ].includes(location.pathname)}
              showBrandFilter={[
                '/urunler',
                '/yeni-musteriler',
                '/musteri-bilgisi',
                '/marka-raporu',
              ].includes(location.pathname)}
            />
          </div>

          <div className="header-actions" style={{ marginLeft: '12px', display: 'flex', gap: '8px' }}>
            <Indicator 
              inline 
              label={unreadCount > 0 ? unreadCount : undefined} 
              size={16} 
              disabled={unreadCount === 0} 
              color="red" 
              withBorder
              offset={4}
            >
              <ActionIcon 
                variant="subtle" 
                color="gray" 
                size="lg" 
                radius="xl" 
                onClick={openNotif}
                title="AI Bildirimleri"
              >
                <IconBell size={22} stroke={1.5} />
              </ActionIcon>
            </Indicator>
          </div>
        </header>

        <NotificationCenter opened={notifOpened} onClose={closeNotif} />

        {/* Page Content */}
        <div className="dashboard-content">
          <Outlet />
        </div>
      </main>

      {/* Floating Global AI Widget */}
      <ChatWidget />
    </div>
  )
}

