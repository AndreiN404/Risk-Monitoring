"""Markets route - Plugin Widget Showcase"""
from flask import Blueprint, render_template, current_app

markets_bp = Blueprint('markets', __name__)

@markets_bp.route('/markets')
def markets():
    """Markets page - displays enabled plugin widgets"""
    widgets = []
    
    try:
        plugin_manager = getattr(current_app, 'plugin_manager', None)
        if plugin_manager:
            # Get all enabled widget plugins
            all_widgets = plugin_manager.plugins.get('widgets', {})
            for widget_name, widget_instance in all_widgets.items():
                widget_key = f'widgets.{widget_name}'
                if widget_key in plugin_manager.enabled_plugins:
                    widget_info = {
                        'id': widget_instance.get_widget_id(),
                        'name': widget_instance.get_name(),
                        'description': widget_instance.get_description(),
                        'category': widget_instance.get_widget_category(),
                        'icon': widget_instance.get_icon(),
                        'instance': widget_instance
                    }
                    widgets.append(widget_info)
    except Exception as e:
        print(f"Error loading widgets: {e}")
    
    return render_template('markets.html', widgets=widgets)
