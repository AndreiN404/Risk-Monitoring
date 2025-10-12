# Package initialization for routes
from .main import main_bp
from .portfolio import portfolio_bp
from .analysis import analysis_bp
from .settings import settings_bp
from .news import news_bp
from .markets import markets_bp

__all__ = ['main_bp', 'portfolio_bp', 'analysis_bp', 'settings_bp', 'news_bp', 'markets_bp']