"""
Risk Calculator Analytics Plugin
Provides risk metrics calculations with configurable parameters
"""
from plugins.base import AnalyticsPlugin
import numpy as np
import pandas as pd
from typing import Dict, Optional


class RiskCalculatorPlugin(AnalyticsPlugin):
    """
    Advanced risk calculation plugin with configurable parameters
    """
    
    def get_name(self) -> str:
        return "Risk Calculator"
    
    def get_version(self) -> str:
        return "2.0.0"
    
    def get_description(self) -> str:
        return "Calculate VaR, volatility, Sharpe ratio, Sortino ratio, and other risk metrics with configurable parameters"
    
    def get_author(self) -> str:
        return "Risk Monitoring Team"
    
    def get_analytics_category(self) -> str:
        return "risk"
    
    def get_icon(self) -> str:
        return "📊"
    
    def get_settings_schema(self) -> Dict:
        """
        Expose risk calculation parameters as configurable settings
        """
        return {
            "type": "object",
            "title": "Risk Calculation Parameters",
            "properties": {
                "risk_free_rate": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 0.2,
                    "default": 0.03,
                    "title": "Risk-Free Rate",
                    "description": "Annual risk-free rate (e.g., 10-year Treasury yield) used for Sharpe and Sortino ratio calculations",
                    "format": "percentage"
                },
                "confidence_level": {
                    "type": "number",
                    "minimum": 0.8,
                    "maximum": 0.99,
                    "default": 0.95,
                    "title": "VaR Confidence Level",
                    "description": "Confidence level for Value at Risk (VaR) calculations. 0.95 means 95% confidence",
                    "format": "percentage"
                },
                "var_method": {
                    "type": "string",
                    "enum": ["historical", "parametric", "monte_carlo"],
                    "default": "historical",
                    "title": "VaR Calculation Method",
                    "description": "Method used to calculate Value at Risk"
                },
                "lookback_days": {
                    "type": "integer",
                    "minimum": 30,
                    "maximum": 1000,
                    "default": 252,
                    "title": "Historical Lookback Period (days)",
                    "description": "Number of trading days to use for historical calculations"
                }
            }
        }
    
    def calculate_var(self, returns: pd.Series) -> Optional[float]:
        """Calculate Value at Risk using configured method and confidence level"""
        if returns is None or len(returns) == 0:
            return None
        
        settings = self.get_current_settings()
        confidence_level = settings.get('confidence_level', 0.95)
        method = settings.get('var_method', 'historical')
        
        try:
            if method == 'historical':
                return -returns.quantile(1 - confidence_level)
            elif method == 'parametric':
                # Parametric VaR (assumes normal distribution)
                mean = returns.mean()
                std = returns.std()
                z_score = np.percentile(np.random.standard_normal(10000), (1 - confidence_level) * 100)
                return -(mean + z_score * std)
            elif method == 'monte_carlo':
                # Monte Carlo simulation (simplified)
                mean = returns.mean()
                std = returns.std()
                simulations = np.random.normal(mean, std, 10000)
                return -np.percentile(simulations, (1 - confidence_level) * 100)
            else:
                return -returns.quantile(1 - confidence_level)
        except Exception as e:
            print(f"VaR calculation error: {e}")
            return None
    
    def calculate_es(self, returns: pd.Series) -> Optional[float]:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if returns is None or len(returns) == 0:
            return None
        
        settings = self.get_current_settings()
        confidence_level = settings.get('confidence_level', 0.95)
        
        try:
            var = self.calculate_var(returns)
            if var is None:
                return None
            tail_returns = returns[returns < -var]
            if len(tail_returns) == 0:
                return None
            return -tail_returns.mean()
        except Exception as e:
            print(f"ES calculation error: {e}")
            return None
    
    def calculate_volatility(self, returns: pd.Series) -> Optional[float]:
        """Calculate annualized volatility"""
        if returns is None or len(returns) == 0:
            return None
        
        try:
            return returns.std() * np.sqrt(252)
        except Exception as e:
            print(f"Volatility calculation error: {e}")
            return None
    
    def calculate_sharpe_ratio(self, returns: pd.Series) -> Optional[float]:
        """Calculate Sharpe Ratio using configured risk-free rate"""
        if returns is None or len(returns) == 0:
            return None
        
        settings = self.get_current_settings()
        risk_free_rate = settings.get('risk_free_rate', 0.03)
        
        try:
            annual_return = returns.mean() * 252
            annual_volatility = self.calculate_volatility(returns)
            
            if annual_volatility is None or annual_volatility == 0:
                return None
            
            return (annual_return - risk_free_rate) / annual_volatility
        except Exception as e:
            print(f"Sharpe ratio calculation error: {e}")
            return None
    
    def calculate_sortino_ratio(self, returns: pd.Series) -> Optional[float]:
        """Calculate Sortino Ratio using configured risk-free rate"""
        if returns is None or len(returns) == 0:
            return None
        
        settings = self.get_current_settings()
        risk_free_rate = settings.get('risk_free_rate', 0.03)
        
        try:
            annual_return = returns.mean() * 252
            
            # Calculate downside deviation (only negative returns)
            downside_returns = returns[returns < 0]
            if len(downside_returns) == 0:
                return None
            
            downside_volatility = downside_returns.std() * np.sqrt(252)
            
            if downside_volatility == 0:
                return None
            
            return (annual_return - risk_free_rate) / downside_volatility
        except Exception as e:
            print(f"Sortino ratio calculation error: {e}")
            return None
    
    def calculate_max_drawdown(self, returns: pd.Series) -> Optional[float]:
        """Calculate maximum drawdown"""
        if returns is None or len(returns) == 0:
            return None
        
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
        except Exception as e:
            print(f"Max drawdown calculation error: {e}")
            return None
    
    def calculate_beta(self, asset_returns: pd.Series, market_returns: pd.Series) -> Optional[float]:
        """Calculate beta (systematic risk)"""
        if asset_returns is None or market_returns is None:
            return None
        
        if len(asset_returns) == 0 or len(market_returns) == 0:
            return None
        
        try:
            covariance = asset_returns.cov(market_returns)
            market_variance = market_returns.var()
            
            if market_variance == 0:
                return None
            
            return covariance / market_variance
        except Exception as e:
            print(f"Beta calculation error: {e}")
            return None
    
    def analyze(self, returns: pd.Series, market_returns: Optional[pd.Series] = None) -> Dict:
        """
        Perform comprehensive risk analysis
        
        Args:
            returns: Asset returns series
            market_returns: Market/benchmark returns (optional, for beta calculation)
        
        Returns:
            Dictionary with all risk metrics
        """
        settings = self.get_current_settings()
        
        return {
            'var': self.calculate_var(returns),
            'es': self.calculate_es(returns),
            'volatility': self.calculate_volatility(returns),
            'sharpe_ratio': self.calculate_sharpe_ratio(returns),
            'sortino_ratio': self.calculate_sortino_ratio(returns),
            'max_drawdown': self.calculate_max_drawdown(returns),
            'beta': self.calculate_beta(returns, market_returns) if market_returns is not None else None,
            'settings_used': {
                'risk_free_rate': settings.get('risk_free_rate', 0.03),
                'confidence_level': settings.get('confidence_level', 0.95),
                'var_method': settings.get('var_method', 'historical')
            }
        }


# Export the plugin class
__all__ = ['RiskCalculatorPlugin']
