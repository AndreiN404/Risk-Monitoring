"""
Dashboard Overview Widget
Displays portfolio summary, risk metrics, and market overview
Configurable through plugin settings
"""
from typing import Dict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import WidgetPlugin
from services.portfolio_service import get_portfolio_data, calculate_portfolio_dashboard_data
from flask import session


class DashboardOverviewWidget(WidgetPlugin):
    """
    Main dashboard widget showing portfolio overview and risk metrics
    """
    
    def get_name(self) -> str:
        return "Dashboard Overview"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Portfolio overview with risk metrics, performance analytics, and market insights"
    
    def get_author(self) -> str:
        return "Risk Monitoring Team"
    
    def get_widget_id(self) -> str:
        return "dashboard-overview"
    
    def get_widget_category(self) -> str:
        return "dashboard"
    
    def get_icon(self) -> str:
        return "📊"
    
    def get_data(self, params: Dict = None) -> Dict:
        """
        Get dashboard data including portfolio and market info
        """
        params = params or {}
        
        # Get portfolio data
        portfolio, total_current_value, total_cost, total_pnl = get_portfolio_data()
        
        # Get dashboard analytics
        lightweight = params.get('lightweight', False)
        force_refresh = params.get('force_refresh', False)
        
        dashboard_data = calculate_portfolio_dashboard_data(
            force_refresh=force_refresh,
            lightweight=lightweight
        )
        
        return {
            'portfolio': portfolio,
            'total_current_value': total_current_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'dashboard_data': dashboard_data
        }
    
    def render(self, params: Dict = None) -> str:
        """
        Render the dashboard overview widget
        """
        params = params or {}
        
        # Get settings with defaults
        schema = self.get_settings_schema()
        settings = {}
        for key, prop in schema.get('properties', {}).items():
            settings[key] = prop.get('default', True)
        
        # Get data
        data = self.get_data(params)
        portfolio = data.get('portfolio', [])
        dashboard_data = data.get('dashboard_data', {})
        
        # Check if we should show this widget
        if not portfolio:
            return self._render_empty_state()
        
        # Build HTML based on settings
        html_sections = []
        
        # Portfolio Summary
        if settings.get('show_portfolio_summary', True):
            html_sections.append(self._render_portfolio_summary(data))
        
        # Risk Metrics
        if settings.get('show_risk_metrics', True):
            html_sections.append(self._render_risk_metrics(dashboard_data))
        
        # Performance Chart
        if settings.get('show_performance_chart', True):
            html_sections.append(self._render_performance_chart(dashboard_data))
        
        # Top Holdings
        if settings.get('show_top_holdings', True):
            html_sections.append(self._render_top_holdings(portfolio))
        
        # Asset Allocation
        if settings.get('show_asset_allocation', True):
            html_sections.append(self._render_asset_allocation(dashboard_data))
        
        return '\n'.join(html_sections)
    
    def _render_empty_state(self) -> str:
        """Render when no portfolio exists"""
        return """
        <div class="hero min-h-[400px] bg-base-200 rounded-box">
            <div class="hero-content text-center">
                <div class="max-w-md">
                    <h1 class="text-4xl font-bold">Welcome to Risk Monitoring!</h1>
                    <p class="py-6">Create your first portfolio to see comprehensive risk analytics and performance metrics.</p>
                    <a href="/portfolio" class="btn btn-primary">Create Portfolio</a>
                </div>
            </div>
        </div>
        """
    
    def _render_portfolio_summary(self, data: Dict) -> str:
        """Render Bloomberg-style portfolio summary cards"""
        total_value = data.get('total_current_value', 0)
        total_cost = data.get('total_cost', 0)
        total_pnl = data.get('total_pnl', 0)
        pnl_percent = (total_pnl / total_cost * 100) if total_cost else 0
        pnl_color = '#00ff87' if total_pnl >= 0 else '#ff4757'
        pnl_arrow = '▲' if total_pnl >= 0 else '▼'
        
        return f"""
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <!-- Total Value Card -->
            <div class="bloomberg-card p-6 bloomberg-glow">
                <div class="flex items-start justify-between mb-4">
                    <div>
                        <p class="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Total Portfolio Value</p>
                        <h2 class="text-4xl font-bold font-mono bg-gradient-to-r from-orange-400 to-orange-500 bg-clip-text text-transparent">
                            ${total_value:,.0f}
                        </h2>
                    </div>
                    <div class="w-12 h-12 bg-orange-500/10 rounded-lg flex items-center justify-center">
                        <span class="text-2xl">💰</span>
                    </div>
                </div>
                <div class="flex items-center text-xs text-gray-400">
                    <span class="mr-2">Cost Basis:</span>
                    <span class="font-mono">${total_cost:,.0f}</span>
                </div>
                <div class="mt-3 h-1 bg-gradient-to-r from-orange-500/20 to-orange-500/5 rounded-full"></div>
            </div>
            
            <!-- P&L Card -->
            <div class="bloomberg-card p-6" style="border-color: {pnl_color}30;">
                <div class="flex items-start justify-between mb-4">
                    <div>
                        <p class="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Unrealized P&L</p>
                        <h2 class="text-4xl font-bold font-mono" style="color: {pnl_color};">
                            {pnl_arrow} ${abs(total_pnl):,.0f}
                        </h2>
                    </div>
                    <div class="w-12 h-12 rounded-lg flex items-center justify-center" style="background: {pnl_color}20;">
                        <span class="text-2xl">{'📈' if total_pnl >= 0 else '📉'}</span>
                    </div>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-xs text-gray-400">Return</span>
                    <span class="text-lg font-bold font-mono" style="color: {pnl_color};">
                        {'+' if pnl_percent >= 0 else ''}{pnl_percent:.2f}%
                    </span>
                </div>
                <div class="mt-3 h-1 rounded-full" style="background: linear-gradient(90deg, {pnl_color}40 0%, {pnl_color}10 100%);"></div>
            </div>
            
            <!-- Performance Indicator -->
            <div class="bloomberg-card p-6">
                <div class="flex items-start justify-between mb-4">
                    <div>
                        <p class="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Performance Status</p>
                        <h2 class="text-2xl font-bold" style="color: {pnl_color};">
                            {'PROFITABLE' if total_pnl >= 0 else 'LOSS'}
                        </h2>
                    </div>
                    <div class="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center">
                        <span class="text-2xl">📊</span>
                    </div>
                </div>
                <div class="space-y-2">
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-400">Efficiency</span>
                        <span class="font-mono text-white">{min(abs(pnl_percent), 100):.1f}%</span>
                    </div>
                    <div class="w-full bg-gray-800 rounded-full h-2">
                        <div class="h-2 rounded-full transition-all" 
                             style="width: {min(abs(pnl_percent), 100)}%; background: linear-gradient(90deg, {pnl_color} 0%, {pnl_color}80 100%);"></div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _render_risk_metrics(self, dashboard_data) -> str:
        """Render Bloomberg-style risk metrics section"""
        # DashboardData is a class with attributes, not a dict
        var_95 = getattr(dashboard_data, 'var_95', 0)
        volatility = getattr(dashboard_data, 'volatility', 0)
        sharpe_ratio = getattr(dashboard_data, 'sharpe_ratio', 0)
        max_drawdown = getattr(dashboard_data, 'max_drawdown', 0)
        beta = getattr(dashboard_data, 'beta', 1.0)
        sortino_ratio = getattr(dashboard_data, 'sortino_ratio', 0)
        
        return f"""
        <div class="bloomberg-card p-6 mb-8">
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 bg-red-500/10 rounded-lg flex items-center justify-center">
                        <span class="text-xl">⚠️</span>
                    </div>
                    <div>
                        <h2 class="text-xl font-bold text-orange-400 uppercase tracking-wide">Risk Metrics</h2>
                        <p class="text-xs text-gray-500">Portfolio risk assessment and analytics</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2 px-3 py-1 bg-red-500/10 rounded border border-red-500/20">
                    <div class="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
                    <span class="text-xs font-mono text-red-400">RISK MONITOR</span>
                </div>
            </div>
            
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <!-- VaR 95% -->
                <div class="bg-gradient-to-br from-red-950/50 to-red-950/20 p-4 rounded-lg border border-red-500/20 hover:border-red-500/40 transition-all">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">VaR (95%)</div>
                    <div class="text-2xl font-bold font-mono text-red-400">
                        {abs(var_95 * 100):.2f}%
                    </div>
                    <div class="text-xs text-gray-600 mt-1">Max loss @ 95%</div>
                </div>
                
                <!-- Volatility -->
                <div class="bg-gradient-to-br from-yellow-950/50 to-yellow-950/20 p-4 rounded-lg border border-yellow-500/20 hover:border-yellow-500/40 transition-all">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Volatility</div>
                    <div class="text-2xl font-bold font-mono text-yellow-400">
                        {volatility * 100:.2f}%
                    </div>
                    <div class="text-xs text-gray-600 mt-1">Annualized σ</div>
                </div>
                
                <!-- Sharpe Ratio -->
                <div class="bg-gradient-to-br from-blue-950/50 to-blue-950/20 p-4 rounded-lg border border-blue-500/20 hover:border-blue-500/40 transition-all">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Sharpe</div>
                    <div class="text-2xl font-bold font-mono text-blue-400">
                        {sharpe_ratio:.2f}
                    </div>
                    <div class="text-xs text-gray-600 mt-1">Risk-adjusted</div>
                </div>
                
                <!-- Max Drawdown -->
                <div class="bg-gradient-to-br from-orange-950/50 to-orange-950/20 p-4 rounded-lg border border-orange-500/20 hover:border-orange-500/40 transition-all">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Drawdown</div>
                    <div class="text-2xl font-bold font-mono text-orange-400">
                        {abs(max_drawdown * 100):.2f}%
                    </div>
                    <div class="text-xs text-gray-600 mt-1">Maximum DD</div>
                </div>
                
                <!-- Beta -->
                <div class="bg-gradient-to-br from-purple-950/50 to-purple-950/20 p-4 rounded-lg border border-purple-500/20 hover:border-purple-500/40 transition-all">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Beta</div>
                    <div class="text-2xl font-bold font-mono text-purple-400">
                        {beta:.2f}
                    </div>
                    <div class="text-xs text-gray-600 mt-1">Market correlation</div>
                </div>
                
                <!-- Sortino -->
                <div class="bg-gradient-to-br from-green-950/50 to-green-950/20 p-4 rounded-lg border border-green-500/20 hover:border-green-500/40 transition-all">
                    <div class="text-xs text-gray-500 uppercase tracking-wider mb-1">Sortino</div>
                    <div class="text-2xl font-bold font-mono text-green-400">
                        {sortino_ratio:.2f}
                    </div>
                    <div class="text-xs text-gray-600 mt-1">Downside risk</div>
                </div>
            </div>
        </div>
        """
    
    def _render_performance_chart(self, dashboard_data) -> str:
        """Render performance chart placeholder"""
        return """
        <div class="card bg-base-100 shadow-xl mb-6">
            <div class="card-body">
                <h2 class="card-title">Portfolio Performance</h2>
                <div id="performance-chart" class="h-64 flex items-center justify-center bg-base-200 rounded">
                    <p class="text-base-content/50">Chart rendering requires chart.js integration</p>
                </div>
            </div>
        </div>
        """
    
    def _render_top_holdings(self, portfolio: list) -> str:
        """Render top holdings table"""
        if not portfolio:
            return ""
        
        # Calculate current value for each asset
        from services.portfolio_service import fetch_live_prices
        
        symbols = [asset.symbol for asset in portfolio]
        try:
            live_prices = fetch_live_prices(symbols)
        except:
            live_prices = {}
        
        # Build holdings list with calculated values
        holdings = []
        for asset in portfolio:
            current_price = live_prices.get(asset.symbol, asset.purchase_price or 0)
            quantity = asset.quantity or 0
            current_value = current_price * quantity if quantity else 0
            cost_basis = (asset.purchase_price or 0) * quantity if quantity else 0
            pnl = current_value - cost_basis
            pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            holdings.append({
                'symbol': asset.symbol,
                'quantity': quantity,
                'current_value': current_value,
                'pnl': pnl,
                'pnl_percent': pnl_percent
            })
        
        # Sort by current value and take top 5
        top_5 = sorted(holdings, key=lambda x: x['current_value'], reverse=True)[:5]
        
        rows = []
        for holding in top_5:
            symbol = holding['symbol']
            quantity = holding['quantity']
            current_value = holding['current_value']
            pnl = holding['pnl']
            pnl_percent = holding['pnl_percent']
            
            rows.append(f"""
            <tr>
                <td class="font-bold">{symbol}</td>
                <td>{quantity}</td>
                <td>${current_value:,.2f}</td>
                <td class="{'text-success' if pnl >= 0 else 'text-error'}">
                    ${pnl:,.2f} ({'+' if pnl_percent >= 0 else ''}{pnl_percent:.2f}%)
                </td>
            </tr>
            """)
        
        return f"""
        <div class="card bg-base-100 shadow-xl mb-6">
            <div class="card-body">
                <h2 class="card-title">Top Holdings</h2>
                <div class="overflow-x-auto">
                    <table class="table table-zebra">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Quantity</th>
                                <th>Value</th>
                                <th>P&L</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
    
    def _render_asset_allocation(self, dashboard_data) -> str:
        """Render asset allocation chart placeholder"""
        return """
        <div class="card bg-base-100 shadow-xl mb-6">
            <div class="card-body">
                <h2 class="card-title">Asset Allocation</h2>
                <div id="allocation-chart" class="h-64 flex items-center justify-center bg-base-200 rounded">
                    <p class="text-base-content/50">Pie chart showing asset distribution</p>
                </div>
            </div>
        </div>
        """
    
    def get_settings_schema(self) -> Dict:
        """
        Define configurable settings for the dashboard
        """
        return {
            'type': 'object',
            'properties': {
                'show_portfolio_summary': {
                    'type': 'boolean',
                    'title': 'Show Portfolio Summary',
                    'default': True,
                    'description': 'Display total value, P&L, and cost cards'
                },
                'show_risk_metrics': {
                    'type': 'boolean',
                    'title': 'Show Risk Metrics',
                    'default': True,
                    'description': 'Display VaR, volatility, Sharpe ratio, etc.'
                },
                'show_performance_chart': {
                    'type': 'boolean',
                    'title': 'Show Performance Chart',
                    'default': True,
                    'description': 'Display portfolio performance over time'
                },
                'show_top_holdings': {
                    'type': 'boolean',
                    'title': 'Show Top Holdings',
                    'default': True,
                    'description': 'Display top 5 holdings by value'
                },
                'show_asset_allocation': {
                    'type': 'boolean',
                    'title': 'Show Asset Allocation',
                    'default': True,
                    'description': 'Display asset allocation pie chart'
                },
                'refresh_interval': {
                    'type': 'integer',
                    'title': 'Auto-refresh Interval (seconds)',
                    'default': 60,
                    'minimum': 30,
                    'maximum': 600,
                    'description': 'How often to refresh dashboard data'
                }
            }
        }
