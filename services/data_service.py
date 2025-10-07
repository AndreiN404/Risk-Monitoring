import os
import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from datetime import datetime
import time
from models import db, StockData, StockAnalysisCache

# Simple cache to avoid repeated API calls
_data_cache = {}

class DataService:
    """Service for handling stock data fetching, caching, and database operations"""
    
    def __init__(self, cache_timeout=300):
        self.cache_timeout = cache_timeout
        self.alpha_vantage_api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    
    def save_stock_data_to_db(self, ticker, stock_data, period="1y"):
        """Save stock data to database for faster caching"""
        try:
            print(f"Saving {ticker} data to database cache...")
            
            # Clear existing data for this ticker and period
            existing_cache = StockAnalysisCache.query.filter_by(ticker=ticker, period=period).first()
            if existing_cache:
                # Delete old stock data entries
                StockData.query.filter_by(ticker=ticker).delete()
                db.session.delete(existing_cache)
            
            # Prepare data for insertion
            data_to_insert = []
            data_start_date = None
            data_end_date = None
            
            for index, row in stock_data.iterrows():
                try:
                    # Handle different date formats
                    if hasattr(index, 'date'):
                        date_value = index.date()
                    elif isinstance(index, str):
                        date_value = pd.to_datetime(index).date()
                    else:
                        # Properly handle Timestamp index
                        try:
                            if hasattr(index, 'to_pydatetime'):
                                date_value = index.to_pydatetime().date()
                            else:
                                date_value = pd.Timestamp(index).date()
                        except Exception as date_error:
                            print(f"Date conversion error for {index}: {date_error}")
                            # Fallback for any date conversion issues
                            date_value = pd.to_datetime(str(index)).date()
                    
                    # Track date range
                    if data_start_date is None or date_value < data_start_date:
                        data_start_date = date_value
                    if data_end_date is None or date_value > data_end_date:
                        data_end_date = date_value
                    
                    # Handle different column names and structures
                    if 'Open' in row.index:
                        open_val = float(row['Open'])
                        high_val = float(row['High'])
                        low_val = float(row['Low'])
                        close_val = float(row['Close'])
                        volume_val = int(row['Volume']) if pd.notna(row['Volume']) else 0
                    else:
                        # Skip if we don't have the required columns
                        continue
                    
                    data_to_insert.append(StockData(
                        ticker=ticker,
                        date=date_value,
                        open=open_val,
                        high=high_val,
                        low=low_val,
                        close=close_val,
                        volume=volume_val
                    ))
                    
                except Exception as e:
                    print(f"Error processing row for {ticker} on {index}: {e}")
                    continue
            
            # Bulk insert stock data
            if data_to_insert:
                db.session.bulk_save_objects(data_to_insert)
                
                # Create cache entry
                cache_entry = StockAnalysisCache(
                    ticker=ticker,
                    period=period,
                    data_start_date=data_start_date,
                    data_end_date=data_end_date,
                    row_count=len(data_to_insert),
                    is_valid=True
                )
                db.session.add(cache_entry)
                
                db.session.commit()
                print(f"Successfully saved {len(data_to_insert)} rows for {ticker}")
                return True
            else:
                print(f"No valid data to save for {ticker}")
                return False
                
        except Exception as e:
            print(f"Error saving {ticker} to database: {e}")
            db.session.rollback()
            return False

    def get_stock_data_from_db(self, ticker, period="1y"):
        """Retrieve stock data from database cache"""
        try:
            # Check if we have cached data for this ticker and period
            cache_entry = StockAnalysisCache.query.filter_by(
                ticker=ticker, 
                period=period, 
                is_valid=True
            ).first()
            
            if not cache_entry:
                print(f"No cache entry found for {ticker} ({period})")
                return None
            
            # Check if cache is recent (within 1 day for analysis)
            cache_age = datetime.now() - cache_entry.last_updated
            if cache_age.days > 1:
                print(f"Cache for {ticker} is {cache_age.days} days old, refreshing...")
                return None
            
            # Retrieve stock data
            stock_data_rows = StockData.query.filter_by(ticker=ticker).order_by(StockData.date).all()
            
            if not stock_data_rows:
                print(f"No stock data rows found for {ticker}")
                return None
            
            # Convert to pandas DataFrame
            data_dict = {
                'Date': [row.date for row in stock_data_rows],
                'Open': [row.open for row in stock_data_rows],
                'High': [row.high for row in stock_data_rows],
                'Low': [row.low for row in stock_data_rows],
                'Close': [row.close for row in stock_data_rows],
                'Volume': [row.volume for row in stock_data_rows]
            }
            
            df = pd.DataFrame(data_dict)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            # Add Adj Close column (same as Close for our purposes)
            df['Adj Close'] = df['Close']
            
            print(f"Retrieved {len(df)} rows from database cache for {ticker}")
            return df
            
        except Exception as e:
            print(f"Error retrieving {ticker} from database: {e}")
            return None

    def fetch_stock_data(self, tickers, period="1y", interval="daily"):
        """
        Fetch stock data using database cache first, then Alpha Vantage API with fallback to yfinance
        """
        # For single ticker, try database cache first
        if len(tickers) == 1:
            ticker = tickers[0]
            cached_data = self.get_stock_data_from_db(ticker, period)
            if cached_data is not None:
                print(f"Using database cache for {ticker}")
                return cached_data
            else:
                print(f"Database cache miss for {ticker}, fetching from API...")
        
        # If no cache hit or multiple tickers, proceed with original logic
        cache_key = f"{'-'.join(tickers)}_{period}_{interval}"
        
        # Check memory cache first
        if cache_key in _data_cache:
            cached_data, cached_time = _data_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_timeout:
                print(f"Using memory cache for {tickers}")
                return cached_data
        
        try:
            ts = TimeSeries(key=self.alpha_vantage_api_key, output_format='pandas')
            
            if len(tickers) == 1:
                ticker = tickers[0]
                # Try Alpha Vantage first - use free endpoint
                try:
                    if period == "1y":
                        # Use the free daily endpoint instead of daily_adjusted
                        data, _ = ts.get_daily(symbol=ticker, outputsize='full')
                    else:
                        data, _ = ts.get_daily(symbol=ticker, outputsize='compact')
                    
                    # Add small delay to respect rate limits
                    time.sleep(0.2)  # 0.2 seconds between calls
                    
                    # Rename columns to match expected format (free endpoint has different column names)
                    data = data.rename(columns={
                        '1. open': 'Open',
                        '2. high': 'High', 
                        '3. low': 'Low',
                        '4. close': 'Close',
                        '5. volume': 'Volume'
                    })
                    
                    # For free endpoint, we don't have adjusted close, so use close
                    data['Adj Close'] = data['Close']
                    
                    # Sort by date ascending
                    data = data.sort_index()
                    data.reset_index(inplace=True)
                    data['Ticker'] = ticker
                    
                    # Limit to last year if needed
                    if period == "1y" and len(data) > 252:
                        data = data.tail(252)
                    
                    # Cache the result
                    _data_cache[cache_key] = (data, datetime.now())
                    
                    # Save to database cache
                    try:
                        # Convert back to proper DataFrame format for database
                        data_for_db = data.set_index('Date') if 'Date' in data.columns else data
                        self.save_stock_data_to_db(ticker, data_for_db, period)
                    except Exception as e:
                        print(f"Warning: Failed to save {ticker} to database cache: {e}")
                    
                    print(f"Alpha Vantage success for {ticker}")
                    return data
                    
                except Exception as e:
                    error_msg = str(e)
                    if "premium endpoint" in error_msg:
                        print(f"Alpha Vantage premium endpoint error for {ticker}: Using free endpoint fallback.")
                    elif 'our standard api rate limit is 25 requests per day' in error_msg.lower():
                        print(f'Alpha Vantage daily rate limit (25 requests/day) exceeded for {ticker}. Switching to yfinance.')
                    elif "rate limit" in error_msg.lower():
                        print(f"Alpha Vantage rate limit exceeded for {ticker}. Falling back to yfinance.")
                    else:
                        print(f"Alpha Vantage failed for {ticker}: {e}. Falling back to yfinance.")
                    
            # Fallback to yfinance for multiple tickers or if Alpha Vantage fails
            print(f"Using yfinance fallback for {tickers}")
            df = yf.download(tickers, period=period, interval="1d")

            
            if len(tickers) == 1:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] if col[1] == tickers[0] else f"{col[0]}_{col[1]}" for col in df.columns]
                # Add ticker as a separate column if needed, but keep date index
                # df['Ticker'] = tickers[0]
                
            # Cache the result
            _data_cache[cache_key] = (df, datetime.now())
            
            # Save to database cache for single ticker analysis
            if len(tickers) == 1 and not df.empty:
                try:
                    self.save_stock_data_to_db(tickers[0], df, period)
                except Exception as e:
                    print(f"Warning: Failed to save {tickers[0]} to database cache: {e}")
            
            return df
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

    def fetch_market_data(self, symbol="SPY", period="1y"):
        """
        Fetch market benchmark data for beta calculation
        """
        try:
            ts = TimeSeries(key=self.alpha_vantage_api_key, output_format='pandas')
            # Use free daily endpoint instead of daily_adjusted
            data, _ = ts.get_daily(symbol=symbol, outputsize='full')
            
            data = data.rename(columns={
                '1. open': 'Open',
                '2. high': 'High',
                '3. low': 'Low', 
                '4. close': 'Close',
                '5. volume': 'Volume'
            })
            
            data['Adj Close'] = data['Close']
            
            data = data.sort_index()
            if len(data) > 252:
                data = data.tail(252)
            
            print(f"Alpha Vantage market data success for {symbol}")
            return data['Close']
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'our standard api rate limit is 25 requests per day' in error_msg:
                print(f"Alpha Vantage daily rate limit (25 requests/day) exceeded for {symbol}. Switching to yfinance.")
            elif 'rate limit' in error_msg:
                print(f"Alpha Vantage rate limit exceeded for {symbol}. Using yfinance fallback.")
            else:
                print(f"Error fetching market data: {e}. Using yfinance fallback.")
            
            market_data = yf.download(symbol, period=period, interval="1d")
            return market_data['Close'] if not market_data.empty else pd.Series()

    def clear_cache(self):
        """Clear in-memory cache"""
        global _data_cache
        _data_cache.clear()
        print("Memory cache cleared")

# Create a default instance
data_service = DataService()