# Package initialization for services
# data_service removed - now using plugin-driven architecture
from .portfolio_service import portfolio_service, PortfolioService, get_portfolio_data, calculate_portfolio_dashboard_data
from .risk_calculator import ProfessionalRiskEngine, calculate_returns, calculate_var, calculate_es, calculate_sharpe_ratio, calculate_sortino_ratio, calculate_beta

__all__ = [
    'portfolio_service', 'PortfolioService', 'get_portfolio_data', 'calculate_portfolio_dashboard_data',
    'ProfessionalRiskEngine', 'calculate_returns', 'calculate_var', 'calculate_es', 
    'calculate_sharpe_ratio', 'calculate_sortino_ratio', 'calculate_beta'
]

