"""API routes for async data loading"""
from flask import Blueprint, jsonify
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
