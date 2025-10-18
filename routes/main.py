from flask import Blueprint, render_template, request, session, current_app
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Dashboard - plugin-driven interface"""
    
    # Get plugin manager
    plugin_manager = current_app.plugin_manager
    
    # Get dashboard widgets
    dashboard_widgets = []
    all_widgets = plugin_manager.plugins.get('widgets', {})
    
    for widget_name, widget_instance in all_widgets.items():
        widget_key = f'widgets.{widget_name}'
        
        # Only show enabled dashboard widgets
        if widget_key in plugin_manager.enabled_plugins:
            # Get widget category
            widget_category = widget_instance.get_widget_category()
            
            # Filter to dashboard category
            if widget_category == 'dashboard':
                dashboard_widgets.append({
                    'id': widget_instance.get_widget_id(),
                    'name': widget_instance.get_name(),
                    'description': widget_instance.get_description(),
                    'category': widget_category,
                    'icon': widget_instance.get_icon(),
                    'instance': widget_instance
                })
    
    # Pass params for rendering
    force_refresh = request.args.get('force_refresh', '0') == '1'
    lightweight = request.args.get('lightweight', '0') == '1'
    
    render_params = {
        'force_refresh': force_refresh,
        'lightweight': lightweight
    }
    
    return render_template('index.html', 
                         widgets=dashboard_widgets,
                         render_params=render_params)

@main_bp.route('/clear_cache')
def clear_cache():
    """Clear application cache - Now managed per-function"""
    # Cache is now managed at function level, not service level
    # Each function maintains its own _cache attribute
    return "Cache system updated to plugin-driven architecture!"

@main_bp.route('/static/js/lightweight-charts.js')
def serve_lightweight_charts():
    """Serve lightweight charts library"""
    pass