"""
Example widget plugin - Price Card
This shows how to create a custom dashboard widget
"""
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import WidgetPlugin
from core.plugin_manager import get_plugin_manager


class PriceCardWidget(WidgetPlugin):
    """
    Simple price card widget showing current quote
    """
    
    def get_name(self) -> str:
        return "Price Card"
    
    def get_widget_id(self) -> str:
        return "price-card"
    
    def get_widget_category(self) -> str:
        return "market"
    
    def get_icon(self) -> str:
        return "💰"
    
    def get_description(self) -> str:
        return "Display current price and change for a symbol"
    
    def get_default_size(self) -> tuple:
        return (3, 2)  # 3 columns wide, 2 rows tall
    
    def get_min_size(self) -> tuple:
        return (2, 2)
    
    def get_data(self, params: Dict) -> Dict:
        """
        Fetch quote data for the widget
        """
        symbol = params.get('symbol', 'SPY')
        provider = params.get('provider', 'yfinance_provider')
        
        try:
            # Get the data provider plugin
            pm = get_plugin_manager()
            data_provider = pm.get_plugin('data_providers', provider)
            
            if data_provider is None:
                return {'error': 'Data provider not found'}
            
            # Get quote
            quote = data_provider.get_quote(symbol)
            
            return quote or {'error': 'No data available'}
            
        except Exception as e:
            return {'error': str(e)}
    
    def render(self, context: Dict) -> str:
        """
        Render the widget HTML
        """
        data = context.get('data', {})
        settings = context.get('settings', {})
        
        symbol = data.get('symbol', 'N/A')
        price = data.get('price', 0)
        change = data.get('change', 0)
        percent_change = data.get('percent_change', 0)
        
        # Determine color class
        color_class = 'text-success' if change > 0 else 'text-error' if change < 0 else 'text-neutral'
        arrow = '▲' if change > 0 else '▼' if change < 0 else '─'
        
        html = f"""
        <div class="price-card-widget h-full bg-base-100 rounded-lg shadow-lg p-4">
            <div class="flex flex-col h-full justify-between">
                <!-- Symbol -->
                <div class="text-sm font-semibold opacity-70">
                    {symbol}
                </div>
                
                <!-- Price -->
                <div class="text-3xl font-bold font-mono">
                    ${price:.2f}
                </div>
                
                <!-- Change -->
                <div class="flex items-center gap-2 text-sm {color_class}">
                    <span>{arrow}</span>
                    <span>${change:+.2f} ({percent_change:+.2f}%)</span>
                </div>
                
                <!-- Provider -->
                <div class="text-xs opacity-50">
                    {data.get('provider', 'Unknown')}
                </div>
            </div>
        </div>
        """
        
        return html
    
    def get_settings_schema(self) -> Dict:
        """
        Define widget settings
        """
        return {
            'type': 'object',
            'properties': {
                'symbol': {
                    'type': 'string',
                    'title': 'Symbol',
                    'default': 'SPY',
                    'description': 'Ticker symbol to display'
                },
                'provider': {
                    'type': 'string',
                    'title': 'Data Provider',
                    'default': 'yfinance_provider',
                    'enum': ['yfinance_provider'],
                    'description': 'Data source for quotes'
                },
                'refresh_interval': {
                    'type': 'integer',
                    'title': 'Refresh Interval (seconds)',
                    'default': 60,
                    'minimum': 10,
                    'maximum': 3600
                },
                'show_volume': {
                    'type': 'boolean',
                    'title': 'Show Volume',
                    'default': False
                }
            }
        }
