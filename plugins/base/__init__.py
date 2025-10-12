"""
Base classes for all plugin types
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


class BasePlugin(ABC):
    """
    Base class for all plugins
    """
    
    def __init__(self):
        self._settings = self.get_default_settings()
    
    @abstractmethod
    def get_name(self) -> str:
        """Plugin name"""
        pass
    
    def get_version(self) -> str:
        """Plugin version"""
        return "1.0.0"
    
    def get_description(self) -> str:
        """Plugin description"""
        return ""
    
    def get_author(self) -> str:
        """Plugin author"""
        return "Unknown"
    
    def get_settings_schema(self) -> Dict:
        """
        Define customizable settings using JSON Schema format
        
        Example:
        {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": "Your API key for authentication"
                },
                "rate_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 5,
                    "title": "Rate Limit (requests/sec)"
                }
            }
        }
        """
        return {}
    
    def get_default_settings(self) -> Dict:
        """
        Get default values for all settings from schema
        """
        schema = self.get_settings_schema()
        defaults = {}
        
        if 'properties' in schema:
            for key, prop in schema['properties'].items():
                if 'default' in prop:
                    defaults[key] = prop['default']
        
        return defaults
    
    def get_current_settings(self) -> Dict:
        """
        Get current plugin settings
        Override this to load from database/file
        """
        # Handle plugins instantiated before __init__ was added
        if not hasattr(self, '_settings'):
            self._settings = self.get_default_settings()
        return self._settings
    
    def update_settings(self, settings: Dict) -> bool:
        """
        Update plugin settings with validation
        
        Args:
            settings: Dictionary of setting_name: value pairs
        
        Returns:
            True if update successful, False otherwise
        """
        # TODO: Add JSON schema validation
        # Handle plugins instantiated before __init__ was added
        if not hasattr(self, '_settings'):
            self._settings = self.get_default_settings()
        self._settings.update(settings)
        return True


class DataProviderPlugin(BasePlugin):
    """
    Base class for data provider plugins
    Allows integration of any data source (APIs, databases, files, etc.)
    """
    
    @abstractmethod
    def get_supported_asset_classes(self) -> List[str]:
        """
        Return list of supported asset classes
        Examples: ['stocks', 'crypto', 'forex', 'commodities', 'bonds']
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for a symbol
        
        Returns:
            dict with keys: symbol, price, change, percent_change, timestamp
        """
        pass
    
    @abstractmethod
    def get_historical(self, symbol: str, period: str = "1y", 
                      interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Get historical data
        
        Args:
            symbol: Ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        pass
    
    def search_symbols(self, query: str) -> List[Dict]:
        """
        Search for symbols/tickers
        
        Returns:
            List of dicts with keys: symbol, name, type, exchange
        """
        return []
    
    def get_fundamentals(self, symbol: str) -> Dict:
        """
        Get fundamental data (optional)
        
        Returns:
            Dict with fundamental metrics (P/E, EPS, Market Cap, etc.)
        """
        return {}
    
    def get_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get news for a symbol (optional)
        
        Returns:
            List of dicts with keys: title, source, url, published, summary
        """
        return []


class WidgetPlugin(BasePlugin):
    """
    Base class for dashboard widgets
    Users can create custom widgets to display any data
    """
    
    @abstractmethod
    def get_widget_id(self) -> str:
        """Unique widget identifier (lowercase, no spaces)"""
        pass
    
    def get_widget_category(self) -> str:
        """
        Widget category for organization
        Examples: 'market', 'portfolio', 'news', 'analytics', 'custom'
        """
        return 'custom'
    
    def get_icon(self) -> str:
        """
        Widget icon (FontAwesome class or emoji)
        Example: 'fa-chart-line' or '📊'
        """
        return '📊'
    
    def get_default_size(self) -> tuple:
        """
        Default (width, height) in grid units (12-column grid)
        Example: (4, 3) = 4 columns wide, 3 rows tall
        """
        return (4, 3)
    
    def get_min_size(self) -> tuple:
        """
        Minimum (width, height) in grid units
        """
        return (2, 2)
    
    def is_resizable(self) -> bool:
        """Can widget be resized?"""
        return True
    
    @abstractmethod
    def render(self, context: Dict) -> str:
        """
        Render widget HTML
        
        Args:
            context: Dict with widget settings and user preferences
        
        Returns:
            HTML string
        """
        pass
    
    @abstractmethod
    def get_data(self, params: Dict) -> Dict:
        """
        Fetch widget data
        
        Args:
            params: Dict with symbol, timeframe, or other parameters
        
        Returns:
            Dict with data to display
        """
        pass
    
    def on_update(self, params: Dict) -> Dict:
        """
        Handle widget updates (when user changes settings)
        
        Returns:
            Updated data
        """
        return self.get_data(params)


class AnalyticsPlugin(BasePlugin):
    """
    Base class for analytics/indicator plugins
    For custom technical indicators, strategies, etc.
    """
    
    @abstractmethod
    def get_indicator_name(self) -> str:
        """Indicator name (e.g., 'Custom RSI', 'My Strategy')"""
        pass
    
    def get_parameters(self) -> Dict:
        """
        Define indicator parameters
        Example: {'period': 14, 'overbought': 70, 'oversold': 30}
        """
        return {}
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **params) -> pd.Series:
        """
        Calculate indicator values
        
        Args:
            data: DataFrame with OHLCV data
            **params: Indicator parameters
        
        Returns:
            Series with indicator values
        """
        pass
    
    def plot_config(self) -> Dict:
        """
        Configuration for plotting
        Example: {'overlay': True, 'color': 'blue', 'line_width': 2}
        """
        return {
            'overlay': False,
            'color': 'blue',
            'line_width': 1
        }


class ThemePlugin(BasePlugin):
    """
    Base class for theme plugins
    Define custom color schemes and styles
    """
    
    @abstractmethod
    def get_theme_id(self) -> str:
        """Unique theme identifier"""
        pass
    
    @abstractmethod
    def get_colors(self) -> Dict:
        """
        Color palette
        Required keys: primary, secondary, accent, background, text, 
                      success, warning, error
        """
        pass
    
    def get_fonts(self) -> Dict:
        """
        Font configuration
        Keys: family, size, weights
        """
        return {
            'family': 'Inter, sans-serif',
            'size': '14px',
            'weights': {'normal': 400, 'bold': 700}
        }
    
    def get_chart_colors(self) -> Dict:
        """
        Chart-specific colors
        Keys: up_candle, down_candle, line, area, volume
        """
        return {
            'up_candle': '#10b981',
            'down_candle': '#ef4444',
            'line': '#3b82f6',
            'area': '#3b82f680',
            'volume': '#9ca3af'
        }
    
    def generate_css(self) -> str:
        """
        Generate CSS for theme
        Returns CSS string with variables
        """
        colors = self.get_colors()
        fonts = self.get_fonts()
        
        return f"""
        :root {{
            --color-primary: {colors.get('primary', '#3b82f6')};
            --color-secondary: {colors.get('secondary', '#6b7280')};
            --color-accent: {colors.get('accent', '#8b5cf6')};
            --color-background: {colors.get('background', '#ffffff')};
            --color-text: {colors.get('text', '#1f2937')};
            --color-success: {colors.get('success', '#10b981')};
            --color-warning: {colors.get('warning', '#f59e0b')};
            --color-error: {colors.get('error', '#ef4444')};
            
            --font-family: {fonts.get('family', 'Inter, sans-serif')};
            --font-size: {fonts.get('size', '14px')};
        }}
        """


class IntegrationPlugin(BasePlugin):
    """
    Base class for integration plugins
    For connecting to external services (Excel, Jupyter, APIs, etc.)
    """
    
    @abstractmethod
    def get_integration_type(self) -> str:
        """
        Type of integration
        Examples: 'export', 'import', 'webhook', 'api', 'notebook'
        """
        pass
    
    @abstractmethod
    def execute(self, action: str, **kwargs) -> Dict:
        """
        Execute integration action
        
        Args:
            action: Action to perform
            **kwargs: Action-specific parameters
        
        Returns:
            Result dict
        """
        pass
