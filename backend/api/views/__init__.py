"""
Views Module
Provides modular views for authentication, datasources, dashboards, and widgets.
"""
from .auth_views import RegisterView, LoginView, ProfileView
from .datasource_views import DataSourceListView, DataSourceDetailView
from .dashboard_views import DashboardListView, DashboardDetailView
from .widget_views import WidgetCreateView, WidgetDeleteView, QueryView, SyncStatusView

__all__ = [
    'RegisterView',
    'LoginView',
    'ProfileView',
    'DataSourceListView',
    'DataSourceDetailView',
    'DashboardListView',
    'DashboardDetailView',
    'WidgetCreateView',
    'WidgetDeleteView',
    'QueryView',
    'SyncStatusView',
]
