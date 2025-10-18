"""API routes for async data loading"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.before_request
def require_login():
    """Require authentication for all API routes"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401

@api_bp.route('/dashboard/metrics')
def get_dashboard_metrics():
    """Get dashboard metrics asynchronously"""
    try:
        dashboard_data = calculate_portfolio_dashboard_data(force_refresh=False)
        
        # Convert dashboard_data object to dictionary
        metrics = {
            'total_pnl': dashboard_data.total_pnl,
            'pnl_percentage': dashboard_data.pnl_percentage,
            'total_value': dashboard_data.total_value,
            'total_cost': dashboard_data.total_cost,
            'volatility': dashboard_data.volatility,
            'sharpe_ratio': dashboard_data.sharpe_ratio,
            'var_95': dashboard_data.var_95,
            'var_99': dashboard_data.var_99,
            'es_95': dashboard_data.es_95,
            'max_drawdown': dashboard_data.max_drawdown,
            'beta': dashboard_data.beta,
            'annual_return': dashboard_data.annual_return,
            'sortino_ratio': dashboard_data.sortino_ratio,
            'calmar_ratio': dashboard_data.calmar_ratio,
            'daily_pnl': dashboard_data.daily_pnl,
            'skewness': dashboard_data.skewness,
            'asset_class_breakdown': dashboard_data.asset_class_breakdown
        }
        
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/dashboard/live-prices')
def get_live_prices():
    """Get live prices asynchronously"""
    try:
        from services.portfolio_service import get_live_prices_for_portfolio
        prices_data = get_live_prices_for_portfolio()
        return jsonify(prices_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/dashboard/correlation')
def get_correlation_matrix():
    """Get correlation matrix asynchronously"""
    try:
        from services.portfolio_service import calculate_correlation_matrix
        matrix_html = calculate_correlation_matrix()
        return jsonify({'matrix_html': matrix_html})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/stock/current-price/<symbol>')
def get_current_price(symbol):
    """Get current market price for a stock symbol - Plugin-driven"""
    import logging
    import traceback
    
    try:
        from flask import current_app
        
        # Get data provider plugin
        pm = current_app.plugin_manager
        logging.info(f"Fetching price for {symbol}, plugin_manager: {pm}")
        
        data_plugin = pm.get_enabled_plugin('data_providers', 'yfinance_provider')
        logging.info(f"Data plugin: {data_plugin}")
        
        if not data_plugin:
            error_msg = 'No data provider plugin available. Please enable yfinance_provider in Settings > Plugins'
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 503
        
        # Get quote via plugin
        quote = data_plugin.get_quote(symbol.upper())
        logging.info(f"Quote for {symbol}: {quote}")
        
        if not quote:
            error_msg = f'Could not fetch price for {symbol}. Symbol may not exist or market data unavailable.'
            logging.warning(error_msg)
            return jsonify({'error': error_msg}), 404
        
        return jsonify({
            'symbol': symbol.upper(),
            'price': round(quote['price'], 2),
            'timestamp': quote.get('timestamp', 'N/A')
        })
        
    except Exception as e:
        error_msg = f'Error fetching price for {symbol}: {str(e)}'
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500

@api_bp.route('/charts/indices')
def get_indices_charts():
    """Get hourly candle data for major market indices - Plugin-driven"""
    try:
        from flask import session, current_app
        import pandas as pd
        
        # Index metadata configuration
        INDEX_INFO = {
            '^GSPC': {'name': 'S&P 500', 'description': 'U.S. Large Cap Index', 'color': '#2962FF', 'region': 'US'},
            '^IXIC': {'name': 'NASDAQ', 'description': 'U.S. Tech-Heavy Index', 'color': '#00BCD4', 'region': 'US'},
            '^DJI': {'name': 'Dow Jones', 'description': 'U.S. Industrial Average', 'color': '#1976D2', 'region': 'US'},
            '^FTSE': {'name': 'FTSE 100', 'description': 'UK Large Cap Index', 'color': '#9C27B0', 'region': 'Europe'},
            '^STOXX50E': {'name': 'Euro Stoxx 50', 'description': 'European Blue Chip Index', 'color': '#FF6D00', 'region': 'Europe'},
        }
        DEFAULT_INDICES = ['^GSPC', '^IXIC', '^FTSE', '^STOXX50E']
        
        # Get selected indices from session, or use defaults
        indices = session.get('selected_indices', DEFAULT_INDICES)
        
        # Get data provider plugin
        pm = current_app.plugin_manager
        data_plugin = pm.get_enabled_plugin('data_providers', 'yfinance_provider')
        
        if not data_plugin:
            return jsonify({'error': 'No data provider plugin available'}), 503
        
        # Fetch hourly candle data via plugin
        result = {}
        for symbol in indices:
            try:
                # Get historical data with hourly interval
                hist_data = data_plugin.get_historical_data(symbol, period='5d', interval='1h')
                
                if hist_data is not None and not hist_data.empty:
                    # Convert to lightweight-charts format
                    candles = []
                    for index, row in hist_data.iterrows():
                        timestamp = int(index.timestamp())
                        candles.append({
                            'time': timestamp,
                            'open': round(float(row['Open']), 2),
                            'high': round(float(row['High']), 2),
                            'low': round(float(row['Low']), 2),
                            'close': round(float(row['Close']), 2),
                            'volume': int(row['Volume']) if 'Volume' in row and pd.notna(row['Volume']) else 0
                        })
                    
                    result[symbol] = {
                        'candles': candles,
                        'info': INDEX_INFO.get(symbol, {'name': symbol, 'description': '', 'color': '#000000', 'region': 'Unknown'})
                    }
                else:
                    result[symbol] = {
                        'candles': [],
                        'info': INDEX_INFO.get(symbol, {})
                    }
            except Exception as e:
                print(f"Error fetching chart data for {symbol}: {e}")
                result[symbol] = {
                    'candles': [],
                    'info': INDEX_INFO.get(symbol, {})
                }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/news/articles')
def fetch_finviz_news():
    """Fetch latest news articles from Finviz and save to database"""
    try:
        from services.news_service import fetch_finviz_news as fetch_news
        articles = fetch_news()
        return jsonify({'articles_fetched': len(articles)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
