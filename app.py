import os
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, session, redirect, url_for, flash
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from flask_sqlalchemy import SQLAlchemy
import warnings
from datetime import datetime, timedelta
import time
import traceback

warnings.filterwarnings('ignore')

# Simple cache to avoid repeated API calls
_data_cache = {}
_cache_timeout = 300  # 5 minutes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a real secret key

# Alpha Vantage Configuration
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')  # Set your API key in environment variables

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///risk_engine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class StockData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Create unique constraint on ticker and date
    __table_args__ = (db.UniqueConstraint('ticker', 'date', name='unique_ticker_date'),)

class StockAnalysisCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, unique=True)
    period = db.Column(db.String(10), nullable=False, default='1y')
    data_start_date = db.Column(db.Date, nullable=False)
    data_end_date = db.Column(db.Date, nullable=False)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    row_count = db.Column(db.Integer, nullable=False, default=0)
    is_valid = db.Column(db.Boolean, nullable=False, default=True)
    
    # Create unique constraint on ticker and period
    __table_args__ = (db.UniqueConstraint('ticker', 'period', name='unique_ticker_period'),)

class RiskMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_data.id'), nullable=False)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='My Portfolio')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class PortfolioAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    asset_class = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    allocation = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=True)  # Price per share when purchased
    quantity = db.Column(db.Float, nullable=True)        # Number of shares owned
    purchase_date = db.Column(db.Date, nullable=True)    # Date of purchase
    
    portfolio = db.relationship('Portfolio', backref='assets')

class PortfolioMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class Snapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    description = db.Column(db.String(200), nullable=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=True)

def calculate_portfolio_weights(portfolio_id=None):
    """Calculate dynamic weights based on allocation amounts"""
    if portfolio_id:
        assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        # Get the first (or default) portfolio
        portfolio = Portfolio.query.first()
        if not portfolio:
            return {}
        assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
    
    if not assets:
        return {}
    
    # Calculate total allocation
    total_allocation = sum(asset.allocation for asset in assets)
    
    if total_allocation == 0:
        return {}
    
    # Calculate weights as percentages
    weights = {}
    for asset in assets:
        weights[asset.symbol] = asset.allocation / total_allocation
    
    return weights

def update_portfolio_weights(portfolio_id=None):
    """Update all portfolio asset weights based on current allocations"""
    weights = calculate_portfolio_weights(portfolio_id)
    
    if portfolio_id:
        assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        portfolio = Portfolio.query.first()
        if not portfolio:
            return
        assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
    
    # Update weights in database
    for asset in assets:
        if asset.symbol in weights:
            asset.weight = weights[asset.symbol]
    
    try:
        db.session.commit()
        print(f"Updated weights for {len(assets)} assets")
    except Exception as e:
        db.session.rollback()
        print(f"Error updating weights: {e}")

def save_stock_data_to_db(ticker, stock_data, period="1y"):
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
                    date_value = pd.Timestamp(index).date()
                
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

def get_stock_data_from_db(ticker, period="1y"):
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

def fetch_stock_data(tickers, period="1y", interval="daily"):
    """
    Fetch stock data using database cache first, then Alpha Vantage API with fallback to yfinance
    """
    # For single ticker, try database cache first
    if len(tickers) == 1:
        ticker = tickers[0]
        cached_data = get_stock_data_from_db(ticker, period)
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
        if (datetime.now() - cached_time).seconds < _cache_timeout:
            print(f"Using memory cache for {tickers}")
            return cached_data
    
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        
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
                    save_stock_data_to_db(ticker, data_for_db, period)
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
                save_stock_data_to_db(tickers[0], df, period)
            except Exception as e:
                print(f"Warning: Failed to save {tickers[0]} to database cache: {e}")
        
        return df
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def fetch_market_data(symbol="SPY", period="1y"):
    """
    Fetch market benchmark data for beta calculation
    """
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
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

def calculate_returns(prices):
    return prices.pct_change().dropna()

def calculate_covariance_matrix(returns):
    return returns.cov()

def calculate_var(returns, confidence_level):
    if not hasattr(returns, 'shape'):
        return None
    
    try:
        if len(returns) == 0:
            return None
    except (TypeError, ValueError):
        return None
    
    print(f"VaR calculation - returns type: {type(returns)}, shape: {returns.shape if hasattr(returns, 'shape') else 'no shape'}")
    
    try:
        if isinstance(returns, pd.DataFrame):
            if returns.shape[1] == 1:
                returns = returns.iloc[:, 0] 
            else:
                return None
        
        return -returns.quantile(1 - confidence_level)
    except Exception as e:
        print(f"VaR quantile error: {e}")
        return None

def calculate_es(returns, confidence_level):
    """Calculate Expected Shortfall (Conditional VaR)"""
    if not hasattr(returns, 'shape'):
        return None
    
    try:
        if len(returns) == 0:
            return None
    except (TypeError, ValueError):
        return None
        
    try:
        if isinstance(returns, pd.DataFrame):
            if returns.shape[1] == 1:
                returns = returns.iloc[:, 0] 
            else:
                return None
                
        var = calculate_var(returns, confidence_level)
        if var is None:
            return None
        tail_returns = returns[returns < -var]
        if len(tail_returns) == 0:
            return None
        return -tail_returns.mean()
    except (ValueError, AttributeError) as e:
        print(f"Error in ES calculation: {e}")
        return None

def calculate_annualized_volatility(returns):
    if not hasattr(returns, 'shape'):
        return None
    
    try:
        if len(returns) == 0:
            return None
    except (TypeError, ValueError):
        return None
    
    print(f"Volatility calculation - returns type: {type(returns)}, shape: {returns.shape if hasattr(returns, 'shape') else 'no shape'}")
    
    try:    
        if isinstance(returns, pd.DataFrame):
            if returns.shape[1] == 1:
                returns = returns.iloc[:, 0] 
            else:
                return None
                
        return returns.std() * np.sqrt(252)
    except Exception as e:
        print(f"Volatility calculation error: {e}")
        return None

def calculate_sharpe_ratio(returns, risk_free_rate):
    if not hasattr(returns, 'shape'):
        return None
    
    try:
        if len(returns) == 0:
            return None
    except (TypeError, ValueError):
        return None
    
    if isinstance(returns, pd.DataFrame):
        if returns.shape[1] == 1:
            returns = returns.iloc[:, 0]   
        else:
            # For multi-column DataFrame, we need to handle differently
            return None
            
    annual_return = returns.mean() * 252
    annual_volatility = calculate_annualized_volatility(returns)
    
    # Handle both Series and scalar cases
    if annual_volatility is None:
        return None
    
    # For Series (multiple assets), check if any volatility is zero
    if hasattr(annual_volatility, '__iter__') and not isinstance(annual_volatility, str):
        try:
            if (annual_volatility == 0).any():
                return np.inf
        except (ValueError, AttributeError):
            if annual_volatility == 0:
                return np.inf
    else:
        # For scalar values
        if annual_volatility == 0:
            return np.inf
            
    return (annual_return - risk_free_rate) / annual_volatility

def calculate_sortino_ratio(returns, risk_free_rate):
    """Calculate Sortino Ratio - focuses only on downside volatility"""
    # Handle DataFrame vs Series consistently
    if not hasattr(returns, 'shape'):
        return None
    
    try:
        if len(returns) == 0:
            return None
    except (TypeError, ValueError):
        return None
    
    # For DataFrame with single column, convert to Series
    if isinstance(returns, pd.DataFrame):
        if returns.shape[1] == 1:
            returns = returns.iloc[:, 0]   
        else:
            # For multi-column DataFrame, we need to handle differently
            return None
    
    annual_return = returns.mean() * 252
    downside_returns = returns[returns < 0]
    
    if len(downside_returns) == 0:
        return np.inf
    
    downside_volatility = downside_returns.std() * np.sqrt(252)
    
    # Handle both Series and scalar cases for volatility check
    if downside_volatility is None:
        return None
        
    if hasattr(downside_volatility, '__iter__') and not isinstance(downside_volatility, str):
        try:
            if (downside_volatility == 0).any():
                return np.inf
        except (ValueError, AttributeError):
            if downside_volatility == 0:
                return np.inf
    else:
        if downside_volatility == 0:
            return np.inf
        
    return (annual_return - risk_free_rate) / downside_volatility

def calculate_beta(stock_returns, market_returns):
    """Calculate Beta relative to market benchmark"""
    try:
        # Validate inputs are not None
        if stock_returns is None or market_returns is None:
            return None
            
        # Ensure both are Series or DataFrame with proper shape
        if not hasattr(stock_returns, '__len__') or not hasattr(market_returns, '__len__'):
            return None
            
        if len(stock_returns) == 0 or len(market_returns) == 0:
            return None
    except (TypeError, AttributeError):
        return None
    
    # Handle both Series and DataFrame cases for stock returns
    if hasattr(stock_returns, 'columns') and len(stock_returns.columns) > 1:
        # Multiple stocks - calculate beta for each
        betas = {}
        for column in stock_returns.columns:
            stock_col = stock_returns[column].dropna()
            market_aligned = market_returns.reindex(stock_col.index).dropna()
            
            combined = pd.DataFrame({
                'stock': stock_col,
                'market': market_aligned
            }).dropna()
            
            if len(combined) < 30:
                betas[column] = None
                continue
                
            covariance = combined['stock'].cov(combined['market'])
            market_variance = combined['market'].var()
            
            if market_variance == 0:
                betas[column] = None
            else:
                betas[column] = covariance / market_variance
        
        return pd.Series(betas)
    else:
        try:
            # Single stock case
            if not isinstance(stock_returns, pd.Series):
                return None
            if not isinstance(market_returns, pd.Series):
                return None
                
            combined = pd.DataFrame({
                'stock': stock_returns,
                'market': market_returns
            }).dropna()
            
            if len(combined) < 30:
                return None
                
            covariance = combined['stock'].cov(combined['market'])
            market_variance = combined['market'].var()
            
            if market_variance == 0:
                return None
                
            return covariance / market_variance
        except Exception as e:
            print(f"Beta calculation error: {e}")
            return None

def calculate_maximum_drawdown(prices):
    """Calculate Maximum Drawdown"""
    if len(prices) == 0:
        return None
    
    # Calculate running maximum
    running_max = prices.expanding().max()
    
    # Calculate drawdown
    drawdown = (prices - running_max) / running_max
    
    return drawdown.min()

def calculate_calmar_ratio(returns):
    """Calculate Calmar Ratio (Annual Return / Max Drawdown)"""
    try:
        if len(returns) == 0:
            return None
    except (TypeError, AttributeError):
        return None
    
    # Calculate annual return and ensure it's scalar
    annual_ret = returns.mean() * 252
    if hasattr(annual_ret, 'item') and hasattr(annual_ret, 'size') and annual_ret.size == 1:
        annual_return = annual_ret.item()
    elif hasattr(annual_ret, '__iter__') and not isinstance(annual_ret, str):
        annual_return = float(annual_ret.iloc[0]) if hasattr(annual_ret, 'iloc') else float(annual_ret[0])
    else:
        annual_return = float(annual_ret)
        
    prices = (1 + returns).cumprod()
    max_dd = calculate_maximum_drawdown(prices)
    

    if max_dd is None:
        return np.inf
    
    try:
        # Handle both scalar and Series cases
        if hasattr(max_dd, 'item'):
            max_dd_value = max_dd.item() if max_dd.size == 1 else max_dd
        else:
            max_dd_value = max_dd
            
        if max_dd_value == 0:
            return np.inf
            
        return annual_return / abs(max_dd_value)
    except (ValueError, TypeError):
        return None

class ProfessionalRiskEngine:
    """
    Professional-grade risk engine with comprehensive analytics
    """
    def __init__(self, stock_data, benchmark_symbol="SPY"):
        self.stock_data = stock_data
        self.benchmark_symbol = benchmark_symbol
        
    def analyze(self, risk_free_rate=0.02):
        """
        Comprehensive risk analysis with professional metrics
        """
        if 'Close' not in self.stock_data.columns:
            return {"Error": "No price data available"}
            
        # For single stock, ensure we're working with a Series
        if hasattr(self.stock_data['Close'], 'columns'):
            # Multiple columns - take the first one for single stock analysis
            prices = self.stock_data['Close'].iloc[:, 0]
        else:
            prices = self.stock_data['Close']
            
        returns = calculate_returns(prices)
        
        # Fetch market data for beta calculation
        market_data = fetch_market_data(self.benchmark_symbol)
        market_returns = calculate_returns(market_data) if not market_data.empty else pd.Series()
        
        # Basic risk metrics
        var_95 = calculate_var(returns, 0.95)
        var_99 = calculate_var(returns, 0.99)
        es_95 = calculate_es(returns, 0.95)
        es_99 = calculate_es(returns, 0.99)
        volatility = calculate_annualized_volatility(returns)
        
        # Performance metrics
        annual_return = returns.mean() * 252 if not returns.empty else None
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
        sortino = calculate_sortino_ratio(returns, risk_free_rate)
        
        # Advanced metrics
        beta = calculate_beta(returns, market_returns)
        max_drawdown = calculate_maximum_drawdown(prices)
        calmar = calculate_calmar_ratio(returns)
        
        # Additional statistics - ensure scalar values
        try:
            if not returns.empty:
                skewness_series = returns.skew()
                skewness = float(skewness_series.iloc[0]) if hasattr(skewness_series, 'iloc') else float(skewness_series)
            else:
                skewness = None
        except (AttributeError, TypeError, IndexError):
            skewness = None
        
        try:
            if not returns.empty:
                kurtosis_series = returns.kurtosis()
                kurtosis = float(kurtosis_series.iloc[0]) if hasattr(kurtosis_series, 'iloc') else float(kurtosis_series)
            else:
                kurtosis = None
        except (AttributeError, TypeError, IndexError):
            kurtosis = None
        
        results = {
            # Risk Metrics
            "VaR (95%)": var_95,
            "VaR (99%)": var_99,
            "ES (95%)": es_95,
            "ES (99%)": es_99,
            "Annualized Volatility": volatility,
            
            # Performance Metrics
            "Annualized Return": annual_return,
            "Sharpe Ratio": sharpe,
            "Sortino Ratio": sortino,
            "Calmar Ratio": calmar,
            
            # Market Metrics
            f"Beta (vs {self.benchmark_symbol})": beta,
            "Maximum Drawdown": max_drawdown,
            
            # Distribution Metrics
            "Skewness": skewness,
            "Kurtosis": kurtosis,
        }
        
        return results

class PortfolioRiskEngine:
    """
    Portfolio-level risk analysis engine
    """
    def __init__(self, portfolio_data, weights=None):
        self.portfolio_data = portfolio_data
        self.weights = weights
        
    def analyze(self, risk_free_rate=0.02):
        """
        Portfolio risk analysis with equal or custom weights
        """
        if 'Close' not in self.portfolio_data.columns:
            return {"Error": "No portfolio data available"}
            
        returns = calculate_returns(self.portfolio_data['Close'])
        
        if self.weights is None:
            # Equal weights
            n_assets = returns.shape[1] if len(returns.shape) > 1 else 1
            self.weights = np.array([1/n_assets] * n_assets)
        
        # Portfolio return calculation
        if len(returns.shape) > 1:
            portfolio_returns = returns.dot(self.weights)
        else:
            portfolio_returns = returns
            
        # Calculate portfolio metrics
        portfolio_return = portfolio_returns.mean() * 252
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Risk metrics
        portfolio_var_95 = calculate_var(portfolio_returns, 0.95)
        portfolio_var_99 = calculate_var(portfolio_returns, 0.99)
        portfolio_es_95 = calculate_es(portfolio_returns, 0.95)
        portfolio_es_99 = calculate_es(portfolio_returns, 0.99)
        
        # Performance metrics
        portfolio_sharpe = calculate_sharpe_ratio(portfolio_returns, risk_free_rate)
        portfolio_sortino = calculate_sortino_ratio(portfolio_returns, risk_free_rate)
        
        # Portfolio specific metrics
        if len(returns.shape) > 1:
            correlation_matrix = returns.corr()
            covariance_matrix = returns.cov() * 252  # Annualized
        else:
            correlation_matrix = None
            covariance_matrix = None
        
        results = {
            "Portfolio Annualized Return": portfolio_return,
            "Portfolio Annualized Volatility": portfolio_volatility,
            "Portfolio Sharpe Ratio": portfolio_sharpe,
            "Portfolio Sortino Ratio": portfolio_sortino,
            "Portfolio VaR (95%)": portfolio_var_95,
            "Portfolio VaR (99%)": portfolio_var_99,
            "Portfolio ES (95%)": portfolio_es_95,
            "Portfolio ES (99%)": portfolio_es_99,
            "Correlation Matrix": correlation_matrix.to_html(classes='table table-zebra') if correlation_matrix is not None else None,
            "Covariance Matrix": covariance_matrix.to_html(classes='table table-zebra') if covariance_matrix is not None else None
        }
        
        return results
    

def get_portfolio_data():
    """Get current portfolio from database with accurate P&L calculation"""
    portfolio = Portfolio.query.first()
    if not portfolio:
        return None, 0, 0, 0  # assets, total_value, total_cost, total_pnl
    
    assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
    total_cost = sum(asset.allocation for asset in assets)  # Initial cost basis (what was paid)
    
    # Get current market values
    symbols = [asset.symbol for asset in assets]
    
    if not symbols:
        return assets, total_cost, total_cost, 0
    
    try:
        live_prices = fetch_live_prices(symbols)
    except Exception as e:
        print(f"Error fetching live prices: {e}")
        # If we can't get live prices, assume no change
        return assets, total_cost, total_cost, 0
    
    # Calculate current value based on actual purchase prices
    total_current_value = 0
    
    for asset in assets:
        if asset.symbol in live_prices and live_prices[asset.symbol] is not None:
            current_price = live_prices[asset.symbol]
            
            if hasattr(asset, 'purchase_price') and hasattr(asset, 'quantity') and asset.purchase_price and asset.quantity:
                # Use actual purchase price and quantity for precise P&L
                current_value = current_price * asset.quantity
                total_current_value += current_value
                print(f"{asset.symbol}: {asset.quantity} shares @ ${current_price:.2f} = ${current_value:.2f} (bought @ ${asset.purchase_price:.2f})")
            else:
                # Fallback: estimate based on allocation and price changes from recent data
                try:
                    # Get recent historical data to establish a baseline
                    historical_data = fetch_stock_data([asset.symbol], period="5d", interval="daily")
                    
                    if not historical_data.empty:
                        if len(symbols) == 1:
                            baseline_price = historical_data['Close'].iloc[0]
                        else:
                            if asset.symbol in historical_data['Close'].columns:
                                baseline_price = historical_data['Close'][asset.symbol].iloc[0]
                            else:
                                baseline_price = current_price  # Use current price as baseline
                        
                        # Calculate price change ratio and apply to allocation
                        price_change_ratio = current_price / baseline_price
                        current_value = asset.allocation * price_change_ratio
                        total_current_value += current_value
                        print(f"{asset.symbol}: Estimated value ${current_value:.2f} (baseline: ${baseline_price:.2f}, current: ${current_price:.2f})")
                    else:
                        # No historical data, use allocation
                        total_current_value += asset.allocation
                        print(f"{asset.symbol}: Using allocation ${asset.allocation:.2f} (no historical data)")
                        
                except Exception as e:
                    print(f"Error calculating estimated value for {asset.symbol}: {e}")
                    # Ultimate fallback: use allocation as current value
                    total_current_value += asset.allocation
        else:
            # No live price available, use allocation as current value
            total_current_value += asset.allocation
            print(f"{asset.symbol}: No live price available, using allocation ${asset.allocation:.2f}")
    
    total_pnl = total_current_value - total_cost
    
    return assets, total_current_value, total_cost, total_pnl

def fetch_live_prices(symbols, force_refresh=False):
    """
    Fetch current/latest prices for given symbols using Alpha Vantage and yfinance
    Uses 5-minute caching to avoid unnecessary API calls unless force_refresh is True
    """
    cache_key = f"live_prices_{'-'.join(sorted(symbols))}"
    
    # Check cache first (unless force refresh is requested)
    if not force_refresh and cache_key in _data_cache:
        cached_data, cached_time = _data_cache[cache_key]
        if (datetime.now() - cached_time).seconds < _cache_timeout:
            print(f"Using cached live prices for {symbols} (fetched {(datetime.now() - cached_time).seconds}s ago)")
            return cached_data
    
    if force_refresh:
        print(f"Force refreshing live prices for {symbols}")
    else:
        print(f"Fetching fresh live prices for {symbols}")
    
    live_prices = {}
    ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
    
    for symbol in symbols:
        try:
            # For free Alpha Vantage tier, use daily data as intraday is premium only
            try:
                data, _ = ts.get_daily(symbol=symbol, outputsize='compact')
                if not data.empty:
                    # Get the most recent close price from daily data
                    latest_price = data['4. close'].iloc[0]  # Most recent daily close
                    live_prices[symbol] = float(latest_price)
                    print(f"Alpha Vantage daily price for {symbol}: ${latest_price:.2f}")
                else:
                    raise Exception("No daily data from Alpha Vantage")
            except Exception as av_error:
                error_msg = str(av_error).lower()
                print(f"Alpha Vantage failed for {symbol}: {av_error}")
                
                # Check for specific daily rate limit message
                if 'our standard api rate limit is 25 requests per day' in error_msg:
                    print(f"Alpha Vantage daily rate limit (25 requests/day) exceeded for {symbol}. Switching to yfinance.")
                elif 'rate limit' in error_msg:
                    print(f"Alpha Vantage rate limit exceeded for {symbol}. Falling back to yfinance.")
                
                raise Exception("Alpha Vantage failed")
            
            # Add small delay to respect rate limits
            time.sleep(0.2)
            
        except Exception as e:
            print(f"Trying yfinance for {symbol} live price")
            try:
                # Use yfinance for more recent/intraday data
                ticker_data = yf.Ticker(symbol)
                
                # Try to get 1-day 1-minute data for most recent price
                hist = ticker_data.history(period="1d", interval="1m")
                if not hist.empty:
                    latest_price = float(hist['Close'].iloc[-1])
                    live_prices[symbol] = latest_price
                    print(f"yfinance live price for {symbol}: ${latest_price:.2f}")
                else:
                    # Fallback to recent daily data
                    hist_daily = ticker_data.history(period="2d")
                    if not hist_daily.empty:
                        latest_price = float(hist_daily['Close'].iloc[-1])
                        live_prices[symbol] = latest_price
                        print(f"yfinance daily price for {symbol}: ${latest_price:.2f}")
                    else:
                        print(f"No price data available for {symbol}")
                        live_prices[symbol] = None
                        
            except Exception as e2:
                print(f"Failed to get live price for {symbol}: {e2}")
                live_prices[symbol] = None
    
    # Cache the live prices with current timestamp
    _data_cache[cache_key] = (live_prices, datetime.now())
    
    return live_prices

def calculate_portfolio_dashboard_data(force_refresh=False):
    """Calculate comprehensive dashboard metrics for the portfolio"""
    assets, total_current_value, total_cost, total_pnl = get_portfolio_data()
    
    if not assets:
        return None
    
    # Get symbols and weights
    symbols = [asset.symbol for asset in assets]
    weights = np.array([asset.weight for asset in assets])
    
    # Fetch live prices for dashboard display
    live_prices = fetch_live_prices(symbols, force_refresh=force_refresh)
    
    # Fetch portfolio data for calculations
    try:
        portfolio_data = fetch_stock_data(symbols, period="1y", interval="daily")
        if portfolio_data.empty:
            return None
            
        # Calculate portfolio returns
        if len(symbols) == 1:
            returns = calculate_returns(portfolio_data['Close'])
            prices = portfolio_data['Close']
        else:
            returns = calculate_returns(portfolio_data['Close'])
            portfolio_returns = returns.dot(weights)
            portfolio_prices = (portfolio_data['Close'] * weights).sum(axis=1)
            returns = portfolio_returns
            prices = portfolio_prices
        
        # Fetch market data for beta
        market_data = fetch_market_data("SPY")
        market_returns = calculate_returns(market_data) if not market_data.empty else pd.Series()
        
        # Ensure market_returns is a Series for beta calculation
        if isinstance(market_returns, pd.DataFrame):
            market_returns = market_returns.iloc[:, 0]
        
        print(f"Market data shape: {market_data.shape if hasattr(market_data, 'shape') else 'no shape'}")
        print(f"Market returns shape: {market_returns.shape if hasattr(market_returns, 'shape') else 'no shape'}")
        print(f"Portfolio returns shape: {returns.shape if hasattr(returns, 'shape') else 'no shape'}")
        print(f"Market returns type: {type(market_returns)}")
        print(f"Portfolio returns type: {type(returns)}")
        
        # Calculate all metrics with individual error handling
        try:
            var_95 = calculate_var(returns, 0.95) or 0
        except Exception as e:
            print(f"Error calculating VaR 95: {e}")
            var_95 = 0
            
        try:
            var_99 = calculate_var(returns, 0.99) or 0
        except Exception as e:
            print(f"Error calculating VaR 99: {e}")
            var_99 = 0
            
        try:
            es_95 = calculate_es(returns, 0.95) or 0
        except Exception as e:
            print(f"Error calculating ES: {e}")
            es_95 = 0
            
        try:
            volatility = calculate_annualized_volatility(returns) or 0
        except Exception as e:
            print(f"Error calculating volatility: {e}")
            volatility = 0
        # Calculate annual return safely - ensure scalar result
        try:
            if not returns.empty:
                annual_ret = returns.mean() * 252
                # Ensure we get a scalar value
                if hasattr(annual_ret, 'item') and hasattr(annual_ret, 'size') and annual_ret.size == 1:
                    annual_return = annual_ret.item()
                elif hasattr(annual_ret, '__iter__') and not isinstance(annual_ret, str):
                    # If it's still a Series/array, take the first value
                    annual_return = float(annual_ret.iloc[0]) if hasattr(annual_ret, 'iloc') else float(annual_ret[0])
                else:
                    annual_return = float(annual_ret)
            else:
                annual_return = 0
        except Exception as e:
            print(f"Error calculating annual return: {e}")
            annual_return = 0
        
        try:
            risk_free_rate = session.get('risk_free_rate', 0.02)
            sharpe_ratio = calculate_sharpe_ratio(returns, risk_free_rate)
        except Exception as e:
            print(f"Error calculating Sharpe ratio: {e}")
            sharpe_ratio = None
            
        try:
            sortino_ratio = calculate_sortino_ratio(returns, risk_free_rate)
        except Exception as e:
            print(f"Error calculating Sortino ratio: {e}")
            sortino_ratio = None
            
        try:
            calmar_ratio = calculate_calmar_ratio(returns)
        except Exception as e:
            print(f"Error calculating Calmar ratio: {e}")
            calmar_ratio = None
            
        try:
            beta = calculate_beta(returns, market_returns)
            print(f"Beta calculation result: {beta}")
        except Exception as e:
            print(f"Error calculating Beta: {e}")
            beta = None
        
        # Fix pandas Series boolean ambiguity for max drawdown
        try:
            max_dd_result = calculate_maximum_drawdown(prices)
            if max_dd_result is None:
                max_drawdown = 0
            elif hasattr(max_dd_result, 'item') and hasattr(max_dd_result, 'size') and max_dd_result.size == 1:
                max_drawdown = max_dd_result.item()
            else:
                max_drawdown = max_dd_result if not pd.isna(max_dd_result) else 0
        except Exception as e:
            print(f"Error calculating max drawdown: {e}")
            max_drawdown = 0
        
        # Fix pandas Series boolean ambiguity
        try:
            if not returns.empty:
                skewness_series = returns.skew()
                skewness = float(skewness_series.iloc[0]) if hasattr(skewness_series, 'iloc') else float(skewness_series)
            else:
                skewness = None
        except (AttributeError, TypeError, IndexError):
            skewness = None
        
        # Daily P&L (approximate) - ensure scalar result
        try:
            if not returns.empty:
                daily_return = returns.iloc[-1]
                # Ensure we get a scalar value
                if hasattr(daily_return, 'item') and hasattr(daily_return, 'size') and daily_return.size == 1:
                    daily_pnl = daily_return.item()
                elif hasattr(daily_return, '__iter__') and not isinstance(daily_return, str):
                    # If it's still a Series/array, take the first value
                    daily_pnl = float(daily_return.iloc[0]) if hasattr(daily_return, 'iloc') else float(daily_return[0])
                else:
                    daily_pnl = float(daily_return)
            else:
                daily_pnl = 0
        except (IndexError, AttributeError, TypeError, ValueError):
            daily_pnl = 0
        
        # Asset class breakdown
        asset_class_breakdown = {}
        for asset in assets:
            class_name = asset.asset_class
            if class_name not in asset_class_breakdown:
                asset_class_breakdown[class_name] = {'weight': 0, 'count': 0}
            asset_class_breakdown[class_name]['weight'] += asset.weight
            asset_class_breakdown[class_name]['count'] += 1
        
        # Correlation matrix for multi-asset portfolios
        correlation_matrix = None
        if len(symbols) > 1 and not portfolio_data.empty:
            try:
                corr_matrix = portfolio_data['Close'].corr()
                correlation_matrix = corr_matrix.to_html(classes='table table-zebra')
            except:
                correlation_matrix = None
        
        # Calculate price changes for live prices
        price_changes = {}
        try:
            if not portfolio_data.empty and len(symbols) == 1:
                # For single asset, compare live price to yesterday's close
                yesterday_close = portfolio_data['Close'].iloc[-1]
                # Ensure scalar value
                if hasattr(yesterday_close, 'item'):
                    yesterday_close = yesterday_close.item()
                    
                symbol = symbols[0]
                if live_prices.get(symbol) is not None and yesterday_close is not None:
                    price_change = ((live_prices[symbol] - yesterday_close) / yesterday_close) * 100
                    price_changes[symbol] = float(price_change)  # Ensure scalar
            elif not portfolio_data.empty and len(symbols) > 1:
                # For multiple assets, compare each live price to yesterday's close
                for symbol in symbols:
                    if symbol in portfolio_data['Close'].columns:
                        yesterday_close = portfolio_data['Close'][symbol].iloc[-1]
                        # Ensure scalar value
                        if hasattr(yesterday_close, 'item'):
                            yesterday_close = yesterday_close.item()
                            
                        if live_prices.get(symbol) is not None and pd.notna(yesterday_close) and yesterday_close != 0:
                            price_change = ((live_prices[symbol] - yesterday_close) / yesterday_close) * 100
                            price_changes[symbol] = float(price_change)  # Ensure scalar
        except Exception as e:
            print(f"Error calculating price changes: {e}")
            price_changes = {}

        # Check if live prices are cached (for UI indication)
        live_prices_cache_key = f"live_prices_{'-'.join(sorted(symbols))}"
        is_prices_cached = (live_prices_cache_key in _data_cache and 
                           (datetime.now() - _data_cache[live_prices_cache_key][1]).seconds < _cache_timeout)

        dashboard_data = {
            'total_value': total_current_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'pnl_percentage': (total_pnl / total_cost * 100) if total_cost != 0 else 0,
            'daily_pnl': daily_pnl,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'var_95': var_95,
            'var_99': var_99,
            'es_95': es_95,
            'max_drawdown': max_drawdown,
            'beta': beta,
            'skewness': skewness,
            'asset_class_breakdown': asset_class_breakdown,
            'correlation_matrix': correlation_matrix,
            'live_prices': live_prices,
            'price_changes': price_changes,
            'price_update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_prices_cached': is_prices_cached
        }
        
        return dashboard_data
        
    except Exception as e:
        print(f"Error calculating portfolio metrics: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return None

@app.route('/')
def index():
    """Dashboard - Main page showing portfolio overview"""
    portfolio, total_current_value, total_cost, total_pnl = get_portfolio_data()
    
    # Check if force refresh is requested
    force_refresh = request.args.get('force_refresh', '0') == '1'
    dashboard_data = calculate_portfolio_dashboard_data(force_refresh=force_refresh)
    
    return render_template('index.html', 
                         portfolio=portfolio, 
                         total_value=total_current_value,
                         total_cost=total_cost,
                         total_pnl=total_pnl,
                         dashboard_data=dashboard_data)

@app.route('/portfolio')
def portfolio_manager():
    """Portfolio management page"""
    portfolio, total_current_value, total_cost, total_pnl = get_portfolio_data()
    return render_template('portfolio.html', 
                         portfolio=portfolio, 
                         total_value=total_current_value,
                         total_cost=total_cost,
                         total_pnl=total_pnl)

@app.route('/add_asset', methods=['POST'])
def add_asset():
    """Add asset to portfolio"""
    symbol = request.form.get('symbol', '').upper().strip()
    asset_class = request.form.get('asset_class')
    allocation = float(request.form.get('allocation', 0))
    purchase_price = request.form.get('purchase_price')
    quantity = request.form.get('quantity')
    purchase_date = request.form.get('purchase_date')
    
    if not symbol or not asset_class or allocation <= 0:
        flash('Please fill in all fields with valid values.', 'error')
        return redirect(url_for('portfolio_manager'))
    
    # Convert optional fields
    purchase_price_val = None
    quantity_val = None
    purchase_date_val = None
    
    if purchase_price and purchase_price.strip():
        try:
            purchase_price_val = float(purchase_price)
        except ValueError:
            pass
    
    if quantity and quantity.strip():
        try:
            quantity_val = float(quantity)
        except ValueError:
            pass
    
    if purchase_date and purchase_date.strip():
        try:
            purchase_date_val = datetime.strptime(purchase_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Validation: if purchase price is provided, quantity should be calculated or provided
    if purchase_price_val and not quantity_val:
        # Calculate quantity from allocation and purchase price
        quantity_val = allocation / purchase_price_val
    elif quantity_val and not purchase_price_val:
        # Calculate purchase price from allocation and quantity
        purchase_price_val = allocation / quantity_val
    
    # Get or create portfolio
    portfolio = Portfolio.query.first()
    if not portfolio:
        portfolio = Portfolio(name='My Portfolio')
        db.session.add(portfolio)
        db.session.commit()
    
    # Check if asset already exists
    existing_asset = PortfolioAsset.query.filter_by(
        portfolio_id=portfolio.id, 
        symbol=symbol
    ).first()
    
    if existing_asset:
        flash(f'{symbol} is already in your portfolio. Remove it first to update.', 'error')
        return redirect(url_for('portfolio_manager'))
    
    # Add new asset with temporary weight (will be recalculated)
    new_asset = PortfolioAsset(
        portfolio_id=portfolio.id,
        symbol=symbol,
        asset_class=asset_class,
        weight=0.0,  # Temporary value, will be calculated
        allocation=allocation,
        purchase_price=purchase_price_val,
        quantity=quantity_val,
        purchase_date=purchase_date_val
    )
    
    db.session.add(new_asset)
    db.session.commit()
    
    # Recalculate all weights based on new allocations
    update_portfolio_weights(portfolio.id)
    
    flash(f'{symbol} added to portfolio successfully!', 'success')
    return redirect(url_for('portfolio_manager'))

@app.route('/remove_asset', methods=['POST'])
def remove_asset():
    """Remove asset from portfolio"""
    symbol = request.form.get('symbol')
    
    asset = PortfolioAsset.query.filter_by(symbol=symbol).first()
    if asset:
        portfolio_id = asset.portfolio_id
        db.session.delete(asset)
        db.session.commit()
        
        # Recalculate weights for remaining assets
        update_portfolio_weights(portfolio_id)
        
        flash(f'{symbol} removed from portfolio.', 'success')
    else:
        flash('Asset not found.', 'error')
    
    return redirect(url_for('portfolio_manager'))

@app.route('/load_preset', methods=['POST'])
def load_preset():
    """Load preset portfolio allocations"""
    preset = request.form.get('preset')
    
    # Clear existing portfolio
    portfolio = Portfolio.query.first()
    if portfolio:
        PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).delete()
    else:
        portfolio = Portfolio(name='My Portfolio')
        db.session.add(portfolio)
        db.session.commit()
    
    # Define preset portfolios (weights will be calculated automatically)
    presets = {
        'conservative': [
            {'symbol': 'TLT', 'asset_class': 'Fixed Income', 'allocation': 60000},
            {'symbol': 'VTI', 'asset_class': 'US Equity', 'allocation': 30000},
            {'symbol': 'VNQ', 'asset_class': 'Real Estate', 'allocation': 10000},
        ],
        'balanced': [
            {'symbol': 'VTI', 'asset_class': 'US Equity', 'allocation': 40000},
            {'symbol': 'VXUS', 'asset_class': 'International Equity', 'allocation': 20000},
            {'symbol': 'BND', 'asset_class': 'Fixed Income', 'allocation': 30000},
            {'symbol': 'VNQ', 'asset_class': 'Real Estate', 'allocation': 10000},
        ],
        'aggressive': [
            {'symbol': 'QQQ', 'asset_class': 'US Equity', 'allocation': 70000},
            {'symbol': 'EEM', 'asset_class': 'International Equity', 'allocation': 15000},
            {'symbol': 'VNQ', 'asset_class': 'Real Estate', 'allocation': 10000},
            {'symbol': 'BTC-USD', 'asset_class': 'Crypto', 'allocation': 5000},
        ]
    }
    
    if preset in presets:
        for asset_data in presets[preset]:
            new_asset = PortfolioAsset(
                portfolio_id=portfolio.id,
                symbol=asset_data['symbol'],
                asset_class=asset_data['asset_class'],
                weight=0.0,  # Will be calculated dynamically
                allocation=asset_data['allocation']
            )
            db.session.add(new_asset)
        
        db.session.commit()
        
        # Calculate weights based on allocations
        update_portfolio_weights(portfolio.id)
        
        flash(f'{preset.capitalize()} portfolio loaded successfully!', 'success')
    else:
        flash('Invalid preset selected.', 'error')
    
    return redirect(url_for('portfolio_manager'))

def prepare_chart_data(stock_data, ticker):
    """
    Prepare chart data for lightweight-charts from stock data
    Returns data in the format expected by TradingView Lightweight Charts
    """
    try:
        print(f"Preparing chart data for {ticker}")
        print(f"Stock data shape: {stock_data.shape}")
        print(f"Stock data columns: {stock_data.columns.tolist()}")
        print(f"Stock data index type: {type(stock_data.index)}")
        print(f"Stock data date range: {stock_data.index.min()} to {stock_data.index.max()}")
        print(f"Number of trading days: {len(stock_data)}")
        
        # Handle different data structures
        price_data = None
        
        # Case 1: Multi-level columns (yfinance with multiple tickers)
        if hasattr(stock_data.columns, 'levels') and len(stock_data.columns.levels) > 1:
            print("Multi-level columns detected")
            if ticker in stock_data.columns.get_level_values(1):
                price_data = stock_data.xs(ticker, axis=1, level=1)
                print(f"Extracted data for {ticker} from multi-level columns")
        
        # Case 2: Single ticker data or flat structure
        if price_data is None:
            price_data = stock_data.copy()
            print("Using direct data structure")
        
        # Handle Alpha Vantage column names (from API)
        if '1. open' in price_data.columns:
            print("Alpha Vantage column format detected")
            col_mapping = {
                '1. open': 'Open',
                '2. high': 'High', 
                '3. low': 'Low',
                '4. close': 'Close',
                '5. volume': 'Volume'
            }
            price_data = price_data.rename(columns=col_mapping)
        
        # Ensure proper column names for yfinance data
        if 'Adj Close' in price_data.columns and 'Close' not in price_data.columns:
            price_data['Close'] = price_data['Adj Close']
        
        # CRITICAL: Ensure the index is a proper datetime index
        if not isinstance(price_data.index, pd.DatetimeIndex):
            print(f"WARNING: Index is not DatetimeIndex, it's {type(price_data.index)}")
            print(f"Index values: {price_data.index[:5].tolist()}")
            
            # Try to find date information
            if 'Date' in price_data.columns:
                print("Found 'Date' column, using it as index")
                price_data['Date'] = pd.to_datetime(price_data['Date'])
                price_data = price_data.set_index('Date')
            elif hasattr(price_data.index, 'name') and price_data.index.name == 'Date':
                print("Index is named 'Date' but not DatetimeIndex, converting...")
                price_data.index = pd.to_datetime(price_data.index)
            else:
                print("ERROR: No proper date information found!")
                print(f"Available columns: {price_data.columns.tolist()}")
                return {
                    'candlestick': [],
                    'volume': [],
                    'ticker': ticker,
                    'error': 'No date information in data'
                }
        else:
            print("✓ Index is already a proper DatetimeIndex")
        
        # Check for required columns
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_cols if col not in price_data.columns]
        
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")
            return {
                'candlestick': [],
                'volume': [],
                'ticker': ticker,
                'error': f'Missing columns: {missing_cols}'
            }
        
        # Prepare candlestick data
        candlestick_data = []
        volume_data = []
        
        # Sort by date to ensure proper order
        price_data = price_data.sort_index()
        
        # Handle different index types
        print(f"Processing {len(price_data)} rows of data")
        print(f"Index type: {type(price_data.index)}")
        print(f"Index name: {price_data.index.name}")
        print(f"First few index values: {price_data.index[:3].tolist()}")
        
        for i, (date_idx, row) in enumerate(price_data.iterrows()):
            if i < 3:  # Debug first 3 rows
                print(f"Row {i}: date_idx = {date_idx}, type = {type(date_idx)}")
            
            try:
                # For TradingView Lightweight Charts v5.x, use YYYY-MM-DD string format
                # Convert the pandas date index to a proper date string
                if hasattr(date_idx, 'date'):
                    # Extract just the date part
                    date_str = date_idx.date().strftime('%Y-%m-%d')
                elif hasattr(date_idx, 'strftime'):
                    # Direct strftime if available
                    date_str = date_idx.strftime('%Y-%m-%d')
                elif isinstance(date_idx, str):
                    # If already a string, validate and use it
                    try:
                        from datetime import datetime
                        # Parse to validate, then reformat to ensure consistency
                        parsed_date = datetime.strptime(date_idx, '%Y-%m-%d')
                        date_str = parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        # Try pandas parsing if the format is different
                        pd_ts = pd.Timestamp(date_idx)
                        date_str = pd_ts.strftime('%Y-%m-%d')
                else:
                    # Convert to pandas timestamp first, then to string
                    pd_ts = pd.Timestamp(date_idx)
                    date_str = pd_ts.strftime('%Y-%m-%d')
                
                print(f"Processing date {date_idx} -> {date_str}")  # Debug line
                
                # Create candlestick data point
                if all(col in row.index and pd.notna(row[col]) for col in required_cols):
                    open_val = float(row['Open'])
                    high_val = float(row['High'])
                    low_val = float(row['Low'])
                    close_val = float(row['Close'])
                    
                    # Validate OHLC data
                    if high_val >= max(open_val, close_val) and low_val <= min(open_val, close_val):
                        candlestick_data.append({
                            'time': date_str,
                            'open': open_val,
                            'high': high_val,
                            'low': low_val,
                            'close': close_val
                        })
                        print(f"Added candlestick for {date_idx} -> {date_str}: OHLC=({open_val}, {high_val}, {low_val}, {close_val})")
                    else:
                        print(f"Invalid OHLC data for {date_idx}: O={open_val}, H={high_val}, L={low_val}, C={close_val}")
                
                # Volume data point
                if 'Volume' in row.index and pd.notna(row['Volume']) and row['Volume'] > 0:
                    volume_data.append({
                        'time': date_str,
                        'value': float(row['Volume'])
                    })
                    
            except Exception as e:
                print(f"Error processing row for date {date_idx}: {e}")
                continue
        
        print(f"Prepared {len(candlestick_data)} candlestick points and {len(volume_data)} volume points")
        
        # Debug: Print first few data points
        if len(candlestick_data) > 0:
            print(f"First candlestick point: {candlestick_data[0]}")
            print(f"Last candlestick point: {candlestick_data[-1]}")
        
        if len(candlestick_data) == 1:
            print("WARNING: Only one data point found! This suggests a data issue.")
            print(f"Single data point: {candlestick_data[0]}")
        
        return {
            'candlestick': candlestick_data,
            'volume': volume_data,
            'ticker': ticker
        }
        
    except Exception as e:
        print(f"Error preparing chart data for {ticker}: {str(e)}")
        traceback.print_exc()
        return {
            'candlestick': [],
            'volume': [],
            'ticker': ticker,
            'error': str(e)
        }

@app.route('/rebalance_portfolio', methods=['POST'])
def rebalance_portfolio():
    """Manually trigger portfolio rebalancing"""
    portfolio = Portfolio.query.first()
    if portfolio:
        update_portfolio_weights(portfolio.id)
        flash('Portfolio weights recalculated successfully!', 'success')
    else:
        flash('No portfolio found to rebalance.', 'error')
    
    return redirect(url_for('portfolio_manager'))

@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    """Individual stock analysis page"""
    ticker = None
    results = None
    
    if request.method == 'POST':
        ticker = request.form.get('ticker', '').upper().strip()
    elif request.method == 'GET':
        # Handle ticker from URL parameter (when clicking from portfolio)
        ticker = request.args.get('ticker', '').upper().strip()
    
    if ticker:
        try:
            stock_data = fetch_stock_data([ticker], period="1y", interval="daily")
            if not stock_data.empty:
                risk_free_rate = session.get('risk_free_rate', 0.02)
                engine = ProfessionalRiskEngine(stock_data)
                results = engine.analyze(risk_free_rate=risk_free_rate)
                
                # Prepare chart data for lightweight-charts
                chart_data = prepare_chart_data(stock_data, ticker)
                
                return render_template('analysis.html', results=results, ticker=ticker, chart_data=chart_data)
            else:
                flash(f'Unable to fetch data for {ticker}. Please check the symbol and try again.', 'error')
        except Exception as e:
            flash(f'Error analyzing {ticker}: {str(e)}', 'error')

    return render_template('analysis.html', results=results, ticker=ticker)

@app.route('/static/js/lightweight-charts.js')
def serve_lightweight_charts():
    """Serve lightweight-charts library locally"""
    from flask import send_from_directory
    import os
    
    charts_path = os.path.join(os.getcwd(), 'node_modules', 'lightweight-charts', 'dist')
    return send_from_directory(charts_path, 'lightweight-charts.standalone.production.js')

@app.route('/clear_cache')
def clear_cache():
    """Clear stock data cache"""
    try:
        # Clear database cache
        StockData.query.delete()
        StockAnalysisCache.query.delete()
        db.session.commit()
        
        # Clear memory cache
        _data_cache.clear()
        
        flash('Stock data cache cleared successfully!', 'success')
    except Exception as e:
        flash(f'Error clearing cache: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('settings'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        try:
            # Handle risk-free rate
            risk_free_rate = float(request.form.get('risk_free_rate'))
            session['risk_free_rate'] = risk_free_rate
        except (ValueError, TypeError):
            # Handle case where input is not a valid float
            pass
        
        # Handle theme selection
        theme = request.form.get('theme')
        if theme in ['light', 'dark', 'system']:
            session['theme'] = theme
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html')

@app.route('/set_theme', methods=['POST'])
def set_theme():
    """AJAX endpoint for quick theme switching"""
    data = request.get_json()
    theme = data.get('theme')
    
    if theme in ['light', 'dark', 'system']:
        session['theme'] = theme
        return {'status': 'success'}
    
    return {'status': 'error'}, 400

def init_database():
    """Initialize database with new tables and migrate existing schema"""
    try:
        # Create new tables if they don't exist
        db.create_all()
        print("Database tables created/updated successfully")
        
        # Check if we need to add new columns to existing portfolio_asset table
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        if 'portfolio_asset' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('portfolio_asset')]
            
            # Add missing columns if they don't exist
            if 'purchase_price' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN purchase_price FLOAT'))
                        conn.commit()
                    print("Added purchase_price column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add purchase_price column: {e}")
            
            if 'quantity' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN quantity FLOAT'))
                        conn.commit()
                    print("Added quantity column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add quantity column: {e}")
            
            if 'purchase_date' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN purchase_date DATE'))
                        conn.commit()
                    print("Added purchase_date column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add purchase_date column: {e}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == '__main__':
    with app.app_context():
        # Initialize database with new caching tables
        init_database()
        print("Database initialized with stock data caching.")
    app.run(debug=True)