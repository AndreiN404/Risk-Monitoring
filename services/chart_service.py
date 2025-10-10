"""Service for fetching chart data for indices and stocks"""
import yfinance as yf
import pandas as pd
from datetime import datetime

def get_hourly_candles(symbols, period="5d"):
    """
    Fetch hourly OHLC candle data for given symbols
    
    Args:
        symbols: List of ticker symbols (e.g., ['^GSPC', '^IXIC', '^FTSE', '^STOXX50E'])
        period: Time period for data (default: 5d for 5 days of hourly data)
        
    Returns:
        Dictionary with symbol as key and list of candle data as value
        Each candle: {'time': timestamp, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': int}
    """
    result = {}
    
    for symbol in symbols:
        try:
            # Fetch hourly data using yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval="1h")
            
            if data.empty:
                print(f"No data found for {symbol}")
                result[symbol] = []
                continue
            
            # Convert to lightweight-charts format
            candles = []
            for index, row in data.iterrows():
                # Convert datetime to Unix timestamp (seconds)
                timestamp = int(index.timestamp())
                
                candle = {
                    'time': timestamp,
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0
                }
                candles.append(candle)
            
            result[symbol] = candles
            print(f"Fetched {len(candles)} hourly candles for {symbol}")
            
        except Exception as e:
            print(f"Error fetching hourly data for {symbol}: {e}")
            result[symbol] = []
    
    return result

def get_index_info():
    """
    Get display names and metadata for major indices
    
    Returns:
        Dictionary with symbol as key and display info as value
    """
    return {
        '^GSPC': {
            'name': 'S&P 500',
            'description': 'U.S. Large Cap Index',
            'color': '#2962FF',
            'region': 'US'
        },
        '^IXIC': {
            'name': 'NASDAQ',
            'description': 'U.S. Tech-Heavy Index',
            'color': '#00BCD4',
            'region': 'US'
        },
        '^DJI': {
            'name': 'Dow Jones',
            'description': 'U.S. Industrial Average',
            'color': '#1976D2',
            'region': 'US'
        },
        '^RUT': {
            'name': 'Russell 2000',
            'description': 'U.S. Small Cap Index',
            'color': '#0288D1',
            'region': 'US'
        },
        '^FTSE': {
            'name': 'FTSE 100',
            'description': 'UK Large Cap Index',
            'color': '#9C27B0',
            'region': 'Europe'
        },
        '^STOXX50E': {
            'name': 'Euro Stoxx 50',
            'description': 'European Blue Chip Index',
            'color': '#FF6D00',
            'region': 'Europe'
        },
        '^GDAXI': {
            'name': 'DAX',
            'description': 'German Stock Index',
            'color': '#E64A19',
            'region': 'Europe'
        },
        '^N225': {
            'name': 'Nikkei 225',
            'description': 'Japanese Stock Index',
            'color': '#D32F2F',
            'region': 'Asia'
        },
        '^HSI': {
            'name': 'Hang Seng',
            'description': 'Hong Kong Index',
            'color': '#C62828',
            'region': 'Asia'
        },
        '000001.SS': {
            'name': 'SSE Composite',
            'description': 'Shanghai Stock Exchange',
            'color': '#B71C1C',
            'region': 'Asia'
        }
    }

def get_default_indices():
    """Get default indices to display"""
    return ['^GSPC', '^IXIC', '^FTSE', '^STOXX50E']

def get_available_indices_list():
    """
    Get list of all available indices with their metadata
    Returns a list of dictionaries, each containing symbol and metadata
    Used for settings page to display available indices
    """
    index_dict = get_index_info()
    return [
        {
            'symbol': symbol,
            'name': info['name'],
            'description': info['description'],
            'region': info['region'],
            'color': info.get('color', '#000000')
        }
        for symbol, info in index_dict.items()
    ]
