# Package initialization for routes
from .main import main_bp
from .portfolio import portfolio_bp
from .analysis import analysis_bp
from .settings import settings_bp

__all__ = ['main_bp', 'portfolio_bp', 'analysis_bp', 'settings_bp']