"""
Alpha Vantage Data Provider Plugin
Professional-grade market data provider with comprehensive coverage
Supports: Stocks, Forex, Crypto, Technical Indicators, Fundamentals
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import DataProviderPlugin


class AlphaVantageProvider(DataProviderPlugin):
    """
    Alpha Vantage data provider with enterprise-grade features
    - Real-time and historical data
    - 50+ technical indicators
    - Fundamental data
    - Economic indicators
    - Forex and crypto support
    """
    
    def __init__(self):
        """Initialize with API key from environment or config"""
        self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
        self.base_url = 'https://www.alphavantage.co/query'
        self._cache = {}
        self._cache_ttl = 60  # 60 seconds cache
        self.logger = logging.getLogger(__name__)
    
    def get_name(self) -> str:
        return "Alpha Vantage Professional"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Enterprise-grade market data: stocks, forex, crypto, fundamentals, 50+ indicators"
    
    def get_author(self) -> str:
        return "Terminal Team"
    
    def get_supported_asset_classes(self) -> List[str]:
        return ['stocks', 'forex', 'crypto', 'etf', 'indices', 'commodities']
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make API request with error handling and caching"""
        params['apikey'] = self.api_key
        cache_key = str(sorted(params.items()))
        
        # Check cache
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_data
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                self.logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                return None
            
            # Cache the result
            self._cache[cache_key] = (datetime.now(), data)
            return data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Alpha Vantage request failed: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote with extended data
        Returns: symbol, price, change, percent_change, volume, high, low, open
        """
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        if not data or 'Global Quote' not in data:
            return None
        
        quote = data['Global Quote']
        
        try:
            current_price = float(quote.get('05. price', 0))
            previous_close = float(quote.get('08. previous close', 0))
            change = float(quote.get('09. change', 0))
            percent_change = float(quote.get('10. change percent', '0').rstrip('%'))
            
            return {
                'symbol': symbol,
                'price': current_price,
                'change': change,
                'percent_change': percent_change,
                'previous_close': previous_close,
                'volume': int(quote.get('06. volume', 0)),
                'high': float(quote.get('03. high', 0)),
                'low': float(quote.get('04. low', 0)),
                'open': float(quote.get('02. open', 0)),
                'timestamp': quote.get('07. latest trading day'),
                'provider': self.get_name()
            }
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parsing quote data: {e}")
            return None
    
    def get_historical(self, symbol: str, period: str = "1y", 
                      interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data
        
        Args:
            symbol: Ticker symbol
            period: Not used (Alpha Vantage returns full history)
            interval: 1d (daily), 1wk (weekly), 1mo (monthly), or intraday (1min, 5min, 15min, 30min, 60min)
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        # Map interval to Alpha Vantage function
        if interval in ['1min', '5min', '15min', '30min', '60min']:
            function = 'TIME_SERIES_INTRADAY'
            params = {
                'function': function,
                'symbol': symbol,
                'interval': interval,
                'outputsize': 'full'
            }
        elif interval == '1wk':
            function = 'TIME_SERIES_WEEKLY'
            params = {
                'function': function,
                'symbol': symbol
            }
        elif interval == '1mo':
            function = 'TIME_SERIES_MONTHLY'
            params = {
                'function': function,
                'symbol': symbol
            }
        else:  # Default to daily
            function = 'TIME_SERIES_DAILY'
            params = {
                'function': function,
                'symbol': symbol,
                'outputsize': 'full'
            }
        
        data = self._make_request(params)
        if not data:
            return None
        
        # Find the time series key
        time_series_key = None
        for key in data.keys():
            if 'Time Series' in key:
                time_series_key = key
                break
        
        if not time_series_key:
            self.logger.error("No time series data found in response")
            return None
        
        time_series = data[time_series_key]
        
        # Convert to DataFrame
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # Rename columns to standard format
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.astype(float)
        
        return df
    
    def search_symbols(self, query: str) -> List[Dict]:
        """
        Search for symbols using Alpha Vantage's search endpoint
        """
        params = {
            'function': 'SYMBOL_SEARCH',
            'keywords': query
        }
        
        data = self._make_request(params)
        if not data or 'bestMatches' not in data:
            return []
        
        results = []
        for match in data['bestMatches'][:10]:  # Limit to top 10
            results.append({
                'symbol': match.get('1. symbol', ''),
                'name': match.get('2. name', ''),
                'type': match.get('3. type', ''),
                'region': match.get('4. region', ''),
                'currency': match.get('8. currency', ''),
                'match_score': float(match.get('9. matchScore', 0))
            })
        
        return results
    
    def get_fundamentals(self, symbol: str) -> Dict:
        """
        Get comprehensive fundamental data
        """
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        data = self._make_request(params)
        if not data:
            return {}
        
        try:
            return {
                'market_cap': float(data.get('MarketCapitalization', 0)),
                'pe_ratio': float(data.get('PERatio', 0) or 0),
                'forward_pe': float(data.get('ForwardPE', 0) or 0),
                'peg_ratio': float(data.get('PEGRatio', 0) or 0),
                'price_to_book': float(data.get('PriceToBookRatio', 0) or 0),
                'price_to_sales': float(data.get('PriceToSalesRatioTTM', 0) or 0),
                'dividend_yield': float(data.get('DividendYield', 0) or 0),
                'eps': float(data.get('EPS', 0) or 0),
                'beta': float(data.get('Beta', 0) or 0),
                'fifty_two_week_high': float(data.get('52WeekHigh', 0) or 0),
                'fifty_two_week_low': float(data.get('52WeekLow', 0) or 0),
                'fifty_day_ma': float(data.get('50DayMovingAverage', 0) or 0),
                'two_hundred_day_ma': float(data.get('200DayMovingAverage', 0) or 0),
                'shares_outstanding': float(data.get('SharesOutstanding', 0) or 0),
                'revenue_ttm': float(data.get('RevenueTTM', 0) or 0),
                'profit_margin': float(data.get('ProfitMargin', 0) or 0),
                'operating_margin': float(data.get('OperatingMarginTTM', 0) or 0),
                'roe': float(data.get('ReturnOnEquityTTM', 0) or 0),
                'roa': float(data.get('ReturnOnAssetsTTM', 0) or 0),
                'sector': data.get('Sector', ''),
                'industry': data.get('Industry', ''),
                'description': data.get('Description', '')
            }
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error parsing fundamentals: {e}")
            return {}
    
    def get_technical_indicator(self, symbol: str, indicator: str, 
                                interval: str = 'daily', **params) -> Optional[pd.DataFrame]:
        """
        Get technical indicator data
        
        Supported indicators: SMA, EMA, WMA, RSI, MACD, BBANDS, ADX, CCI, AROON, etc.
        
        Args:
            symbol: Ticker symbol
            indicator: Indicator name (e.g., 'RSI', 'MACD', 'SMA')
            interval: Time interval (daily, weekly, monthly, or intraday)
            **params: Indicator-specific parameters (e.g., time_period=14 for RSI)
        """
        indicator_params = {
            'function': indicator,
            'symbol': symbol,
            'interval': interval,
            **params
        }
        
        data = self._make_request(indicator_params)
        if not data:
            return None
        
        # Find the technical analysis key
        tech_key = None
        for key in data.keys():
            if 'Technical Analysis' in key:
                tech_key = key
                break
        
        if not tech_key:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame.from_dict(data[tech_key], orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df.astype(float)
        
        return df
    
    def get_settings_schema(self) -> Dict:
        """Define customizable settings"""
        return {
            'type': 'object',
            'properties': {
                'api_key': {
                    'type': 'string',
                    'title': 'API Key',
                    'default': 'demo',
                    'description': 'Your Alpha Vantage API key (get free at alphavantage.co)'
                },
                'cache_duration': {
                    'type': 'integer',
                    'title': 'Cache Duration (seconds)',
                    'default': 60,
                    'minimum': 0,
                    'maximum': 3600
                },
                'request_timeout': {
                    'type': 'integer',
                    'title': 'Request Timeout (seconds)',
                    'default': 10,
                    'minimum': 1,
                    'maximum': 60
                },
                'default_outputsize': {
                    'type': 'string',
                    'title': 'Default Output Size',
                    'enum': ['compact', 'full'],
                    'default': 'full',
                    'description': 'Compact = latest 100 data points, Full = 20+ years'
                }
            }
        }
