"""API routes for async data loading"""
from flask import Blueprint, jsonify, request
from services.portfolio_service import get_portfolio_data, calculate_portfolio_dashboard_data

api_bp = Blueprint('api', __name__, url_prefix='/api')

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
    """Get current market price for a stock symbol"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol.upper())
        
        # Get current market data
        info = ticker.info
        
        # Try different price fields in order of preference
        current_price = None
        price_fields = ['currentPrice', 'regularMarketPrice', 'previousClose', 'ask', 'bid']
        
        for field in price_fields:
            if field in info and info[field]:
                current_price = float(info[field])
                break
        
        if current_price is None:
            # Fallback: try to get latest close from history
            hist = ticker.history(period='1d')
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
        
        if current_price is None:
            return jsonify({'error': f'Could not fetch price for {symbol}'}), 404
        
        return jsonify({
            'symbol': symbol.upper(),
            'price': round(current_price, 2),
            'timestamp': info.get('regularMarketTime', 'N/A')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/charts/indices')
def get_indices_charts():
    """Get hourly candle data for major market indices"""
    try:
        from flask import session
        from services.chart_service import get_hourly_candles, get_index_info, get_default_indices
        
        # Get selected indices from session, or use defaults
        indices = session.get('selected_indices', get_default_indices())
        
        # Fetch hourly candle data
        candle_data = get_hourly_candles(indices, period='5d')
        
        # Get index display info
        index_info = get_index_info()
        
        # Combine data with display info
        result = {}
        for symbol in indices:
            result[symbol] = {
                'candles': candle_data.get(symbol, []),
                'info': index_info.get(symbol, {})
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
