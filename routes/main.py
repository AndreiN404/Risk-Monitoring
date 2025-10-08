from flask import Blueprint, render_template, request
from services.portfolio_service import get_portfolio_data, calculate_portfolio_dashboard_data
from services.data_service import data_service

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Dashboard - Main page showing portfolio overview"""
    portfolio, total_current_value, total_cost, total_pnl = get_portfolio_data()
    
    # Disable lightweight mode by default for now (turn off optimization until it's fixed)
    # Users can enable with ?lightweight=1 if they want faster loads with cached data
    lightweight = request.args.get('lightweight', '0') == '1'
    force_refresh = request.args.get('force_refresh', '0') == '1'
    
    dashboard_data = calculate_portfolio_dashboard_data(
        force_refresh=force_refresh,
        lightweight=lightweight
    )
    
    return render_template('index.html', 
                         portfolio=portfolio, 
                         total_value=total_current_value,
                         total_cost=total_cost,
                         total_pnl=total_pnl,
                         dashboard_data=dashboard_data)

@main_bp.route('/clear_cache')
def clear_cache():
    """Clear application cache"""
    data_service.clear_cache()
    return "Cache cleared successfully!"

@main_bp.route('/static/js/lightweight-charts.js')
def serve_lightweight_charts():
    """Serve lightweight charts library"""
    pass