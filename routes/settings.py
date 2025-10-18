from flask import Blueprint, render_template, request, session, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user

settings_bp = Blueprint('settings', __name__)

# Protect all routes in this blueprint
@settings_bp.before_request
def require_login():
    """Require authentication for all settings routes"""
    if not current_user.is_authenticated:
        # For AJAX/API requests, return JSON error instead of redirect
        if request.is_json or request.path.startswith('/settings/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Authentication required', 'redirect': url_for('auth.login')}), 401
        return redirect(url_for('auth.login', next=request.url))

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for application configuration - Plugin-driven approach"""
    
    # Get plugin manager
    plugin_manager = getattr(current_app, 'plugin_manager', None)
    if plugin_manager is None:
        flash('Plugin manager not initialized', 'error')
        return render_template('settings.html', plugins_with_settings=[], current_settings={})
    
    if request.method == 'POST':
        # Handle application settings
        session['theme'] = request.form.get('theme', 'system')
        
        # Risk analysis settings
        risk_free_rate = request.form.get('risk_free_rate')
        if risk_free_rate:
            session['risk_free_rate'] = float(risk_free_rate)
        
        # Dashboard settings
        session['show_market_overview'] = 'show_market_overview' in request.form
        
        # Market indices selection (limit to 4)
        selected_indices = request.form.getlist('selected_indices')[:4]
        session['selected_indices'] = selected_indices
        
        # Handle plugin settings updates
        updated_count = 0
        
        for plugin_type in ['data_providers', 'widgets', 'analytics', 'integrations']:
            for plugin_name, plugin_instance in plugin_manager.plugins[plugin_type].items():
                plugin_key = f"{plugin_type}.{plugin_name}"
                schema = plugin_instance.get_settings_schema()
                
                if not schema or 'properties' not in schema:
                    continue
                
                # Collect settings from form
                plugin_settings = {}
                for setting_name, setting_schema in schema['properties'].items():
                    form_key = f"{plugin_key}.{setting_name}"
                    
                    if setting_schema['type'] == 'number':
                        value = request.form.get(form_key)
                        if value:
                            plugin_settings[setting_name] = float(value)
                    elif setting_schema['type'] == 'integer':
                        value = request.form.get(form_key)
                        if value:
                            plugin_settings[setting_name] = int(value)
                    elif setting_schema['type'] == 'boolean':
                        plugin_settings[setting_name] = form_key in request.form
                    elif setting_schema['type'] == 'string':
                        value = request.form.get(form_key)
                        if value is not None:
                            plugin_settings[setting_name] = value
                
                # Update plugin settings
                if plugin_settings:
                    if plugin_instance.update_settings(plugin_settings):
                        updated_count += 1
        
        flash(f'Settings updated successfully. {updated_count} plugin(s) configured.', 'success')
        return redirect(url_for('settings.settings'))
    
    # GET request - display settings
    # Collect all plugins with settings
    plugins_with_settings = []
    
    for plugin_type in ['analytics', 'data_providers', 'widgets', 'integrations']:
        for plugin_name, plugin_instance in plugin_manager.plugins[plugin_type].items():
            schema = plugin_instance.get_settings_schema()
            
            if not schema or 'properties' not in schema:
                continue
            
            plugins_with_settings.append({
                'key': f"{plugin_type}.{plugin_name}",
                'name': plugin_instance.get_name(),
                'description': plugin_instance.get_description(),
                'type': plugin_type,
                'icon': plugin_instance.get_icon() if hasattr(plugin_instance, 'get_icon') else '⚙️',
                'schema': schema,
                'current_values': plugin_instance.get_current_settings()
            })
    
    # Default application settings
    app_settings = {
        'theme': session.get('theme', 'system'),
        'risk_free_rate': session.get('risk_free_rate', 0.03),
        'show_market_overview': session.get('show_market_overview', True),
        'selected_indices': session.get('selected_indices', ['SPX', 'NDX', 'DJI', 'RUT'])
    }
    
    # Available market indices
    available_indices = [
        {'symbol': 'SPX', 'name': 'S&P 500', 'region': 'US'},
        {'symbol': 'NDX', 'name': 'NASDAQ 100', 'region': 'US'},
        {'symbol': 'DJI', 'name': 'Dow Jones', 'region': 'US'},
        {'symbol': 'RUT', 'name': 'Russell 2000', 'region': 'US'},
        {'symbol': 'UKX', 'name': 'FTSE 100', 'region': 'Europe'},
        {'symbol': 'DAX', 'name': 'DAX', 'region': 'Europe'},
        {'symbol': 'CAC', 'name': 'CAC 40', 'region': 'Europe'},
        {'symbol': 'NKY', 'name': 'Nikkei 225', 'region': 'Asia'},
        {'symbol': 'HSI', 'name': 'Hang Seng', 'region': 'Asia'},
        {'symbol': 'SHCOMP', 'name': 'Shanghai Composite', 'region': 'Asia'}
    ]
    
    return render_template('settings.html', 
                         plugins_with_settings=plugins_with_settings,
                         settings=app_settings,
                         available_indices=available_indices)

@settings_bp.route('/set_theme', methods=['POST'])
def set_theme():
    """AJAX endpoint to set theme preference"""
    try:
        data = request.get_json()
        theme = data.get('theme', 'light')
        
        # Validate theme
        if theme not in ['light', 'dark', 'system']:
            return jsonify({'success': False, 'error': 'Invalid theme'}), 400
        
        # Save to session
        session['theme'] = theme
        
        return jsonify({'success': True, 'theme': theme})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/plugins')
def plugins():
    """Plugin management page"""
    try:
        # Get plugin manager from app
        plugin_manager = getattr(current_app, 'plugin_manager', None)
        
        if plugin_manager is None:
            flash('Plugin manager not initialized', 'error')
            return render_template('plugins.html', plugins={}, enabled_plugins=set())
        
        # Get all plugins organized by type
        all_plugins = plugin_manager.list_plugins()
        enabled_plugins = plugin_manager.enabled_plugins
        
        # Organize by type
        plugins_by_type = {
            'data_providers': {},
            'widgets': {},
            'analytics': {},
            'themes': {},
            'integrations': {}
        }
        
        for plugin_key, metadata in all_plugins.items():
            plugin_type = metadata['type']
            if plugin_type in plugins_by_type:
                plugins_by_type[plugin_type][plugin_key] = metadata
        
        return render_template('plugins.html', 
                             plugins=plugins_by_type,
                             enabled_plugins=enabled_plugins)
    
    except Exception as e:
        flash(f'Error loading plugins: {str(e)}', 'error')
        return render_template('plugins.html', plugins={}, enabled_plugins=set())


@settings_bp.route('/settings/api/plugins/toggle', methods=['POST'])
def toggle_plugin():
    """Enable or disable a plugin"""
    import logging
    logging.info(f"Toggle plugin called - User authenticated: {current_user.is_authenticated}")
    
    try:
        data = request.get_json()
        plugin_key = data.get('plugin_key')
        enable = data.get('enable', True)
        
        logging.info(f"Toggle request - plugin_key: {plugin_key}, enable: {enable}")
        
        if not plugin_key:
            return jsonify({'success': False, 'error': 'Plugin key required'}), 400
        
        # Parse plugin type and name
        parts = plugin_key.split('.')
        if len(parts) != 2:
            return jsonify({'success': False, 'error': 'Invalid plugin key format'}), 400
        
        plugin_type, plugin_name = parts
        
        # Get plugin manager
        plugin_manager = getattr(current_app, 'plugin_manager', None)
        if plugin_manager is None:
            return jsonify({'success': False, 'error': 'Plugin manager not initialized'}), 500
        
        # Toggle plugin
        if enable:
            plugin_manager.enable_plugin(plugin_type, plugin_name)
            message = f'Plugin {plugin_key} enabled'
        else:
            plugin_manager.disable_plugin(plugin_type, plugin_name)
            message = f'Plugin {plugin_key} disabled'
        
        return jsonify({'success': True, 'message': message})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/settings/api/plugins/apply-theme', methods=['POST'])
def apply_theme():
    """Apply a plugin theme"""
    try:
        data = request.get_json()
        theme_key = data.get('theme_key')
        
        if not theme_key:
            return jsonify({'success': False, 'error': 'Theme key required'}), 400
        
        # Parse theme key (e.g., 'themes.bloomberg_dark')
        parts = theme_key.split('.')
        if len(parts) != 2 or parts[0] != 'themes':
            return jsonify({'success': False, 'error': 'Invalid theme key format'}), 400
        
        theme_name = parts[1]
        
        # Get plugin manager
        plugin_manager = getattr(current_app, 'plugin_manager', None)
        if plugin_manager is None:
            return jsonify({'success': False, 'error': 'Plugin manager not initialized'}), 500
        
        # Get the theme plugin
        theme = plugin_manager.get_plugin('themes', theme_name)
        if theme is None:
            return jsonify({'success': False, 'error': f'Theme {theme_name} not found'}), 404
        
        # Generate CSS
        css = theme.generate_css()
        
        # Save theme preference to session
        session['active_plugin_theme'] = theme_key
        
        return jsonify({
            'success': True, 
            'message': f'Theme "{theme.get_name()}" applied successfully',
            'css': css
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/settings/api/plugins/reload', methods=['POST'])
def reload_plugin():
    """Hot-reload a plugin"""
    try:
        data = request.get_json()
        plugin_key = data.get('plugin_key')
        
        if not plugin_key:
            return jsonify({'success': False, 'error': 'Plugin key required'}), 400
        
        # Parse plugin type and name
        parts = plugin_key.split('.')
        if len(parts) != 2:
            return jsonify({'success': False, 'error': 'Invalid plugin key format'}), 400
        
        plugin_type, plugin_name = parts
        
        # Get plugin manager
        plugin_manager = getattr(current_app, 'plugin_manager', None)
        if plugin_manager is None:
            return jsonify({'success': False, 'error': 'Plugin manager not initialized'}), 500
        
        # Reload plugin
        plugin_manager.reload_plugin(plugin_type, plugin_name)
        
        return jsonify({'success': True, 'message': f'Plugin {plugin_key} reloaded'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500