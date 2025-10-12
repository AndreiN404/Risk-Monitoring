import os
import warnings
from flask import Flask

# Suppress warnings
warnings.filterwarnings('ignore')

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize database
    from models import db
    db.init_app(app)
    
    # Register blueprints
    from routes import main_bp, portfolio_bp, analysis_bp, settings_bp, news_bp, markets_bp
    from routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(markets_bp)
    app.register_blueprint(api_bp)
    
    # Initialize database within app context
    with app.app_context():
        from utils.database import init_database
        if not init_database():
            print("Warning: Database initialization failed")
    
    # Initialize background scheduler for periodic tasks
    from services.scheduler import init_scheduler
    init_scheduler(app)
    
    # Initialize plugin manager
    from core.plugin_manager import init_plugin_manager
    with app.app_context():
        try:
            plugin_manager = init_plugin_manager()
            app.plugin_manager = plugin_manager
            print(f"✓ Plugin Manager initialized: {len(plugin_manager.enabled_plugins)} plugins loaded")
        except Exception as e:
            print(f"Warning: Plugin manager initialization failed: {e}")
    
    # Add context processor for plugin themes
    @app.context_processor
    def inject_plugin_theme():
        """Inject active plugin theme CSS into all templates"""
        from flask import session
        theme_css = ''
        active_theme = session.get('active_plugin_theme')
        
        # Set Bloomberg Dark as default theme if no theme is set
        if not active_theme:
            active_theme = 'themes.bloomberg_dark'
            session['active_plugin_theme'] = active_theme
        
        if active_theme:
            try:
                # Parse theme key (e.g., 'themes.bloomberg_dark')
                parts = active_theme.split('.')
                if len(parts) == 2 and parts[0] == 'themes':
                    theme_name = parts[1]
                    plugin_manager = getattr(app, 'plugin_manager', None)
                    if plugin_manager:
                        theme = plugin_manager.get_plugin('themes', theme_name)
                        if theme:
                            theme_css = theme.generate_css()
            except Exception as e:
                print(f"Warning: Failed to load plugin theme: {e}")
        
        return {'plugin_theme_css': theme_css}
    
    return app

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.getenv('FLASK_CONFIG', 'default')
    
    # Create app instance
    app = create_app(config_name)
    
    # Run the application
    debug_mode = app.config.get('DEBUG', False)
    app.run(debug=debug_mode)