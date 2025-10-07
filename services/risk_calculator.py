import numpy as np
import pandas as pd
from services.data_service import data_service

def calculate_returns(prices):
    """Calculate returns from price series"""
    return prices.pct_change().dropna()

def calculate_covariance_matrix(returns):
    """Calculate covariance matrix of returns"""
    return returns.cov()

def calculate_var(returns, confidence_level):
    """Calculate Value at Risk (VaR)"""
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
    """Calculate annualized volatility"""
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
    """Calculate Sharpe Ratio"""
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
        market_data = data_service.fetch_market_data(self.benchmark_symbol)
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
            
            # Distribution Statistics
            "Skewness": skewness,
            "Kurtosis": kurtosis
        }
        
        return results