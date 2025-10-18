"""
Example data provider plugin using yfinance
This shows how to create a custom data provider
"""
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import DataProviderPlugin


class YFinancePlugin(DataProviderPlugin):
    """
    Yahoo Finance data provider plugin
    Provides free market data for stocks, ETFs, indices, forex, crypto
    """
    
    def get_name(self) -> str:
        return "Yahoo Finance"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Free market data from Yahoo Finance API"
    
    def get_author(self) -> str:
        return "Terminal Team"
    
    def get_supported_asset_classes(self) -> List[str]:
        return ['stocks', 'etf', 'index', 'forex', 'crypto', 'commodities']
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote using yfinance
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get current price and previous close
            # Try multiple fields as yfinance API can vary
            current_price = (
                info.get('currentPrice') or 
                info.get('regularMarketPrice') or 
                info.get('previousClose') or 
                0
            )
            previous_close = info.get('previousClose', 0)
            
            # Calculate changes
            change = current_price - previous_close if previous_close else 0
            percent_change = (change / previous_close * 100) if previous_close else 0
            
            return {
                'symbol': symbol,
                'price': current_price,
                'change': change,
                'percent_change': percent_change,
                'previous_close': previous_close,
                'volume': info.get('volume', 0) or info.get('regularMarketVolume', 0),
                'provider': self.get_name(),
                'timestamp': info.get('regularMarketTime', 'N/A')
            }
            
        except Exception as e:
            logging.error(f"Error fetching quote for {symbol}: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None
    
    def get_historical(self, symbol: str, period: str = "1y", 
                      interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Get historical data using yfinance
        
        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logging.warning(f"No historical data for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logging.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol: str, period: str = "1y", 
                           interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        Alias for get_historical to match expected plugin interface
        """
        return self.get_historical(symbol, period, interval)
    
    def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Get quotes for multiple symbols at once
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            Dictionary mapping symbols to quote data
        """
        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
            except Exception as e:
                logging.error(f"Failed to get quote for {symbol}: {e}")
                quotes[symbol] = None
        return quotes
    
    def search_symbols(self, query: str) -> List[Dict]:
        """
        Search for symbols (basic implementation)
        """
        # yfinance doesn't have built-in search, so this is limited
        # In a real implementation, you'd use a separate search API
        try:
            ticker = yf.Ticker(query.upper())
            info = ticker.info
            
            return [{
                'symbol': query.upper(),
                'name': info.get('longName', query),
                'type': info.get('quoteType', 'Unknown'),
                'exchange': info.get('exchange', 'Unknown')
            }]
        except:
            return []
    
    def get_fundamentals(self, symbol: str) -> Dict:
        """
        Get fundamental data
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'eps': info.get('trailingEps'),
                'beta': info.get('beta'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'float_shares': info.get('floatShares')
            }
            
        except Exception as e:
            logging.error(f"Error fetching fundamentals for {symbol}: {e}")
            return {}
    
    def get_settings_schema(self) -> Dict:
        """
        Define settings for this provider
        """
        return {
            'type': 'object',
            'properties': {
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
                }
            }
        }
