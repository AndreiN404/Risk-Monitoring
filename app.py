import os
import warnings
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Suppress warnings
warnings.filterwarnings('ignore')

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Ensure SECRET_KEY is set
    if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
        import secrets
        app.config['SECRET_KEY'] = secrets.token_hex(32)
        print(" WARNING: Using generated SECRET_KEY. Set SECRET_KEY in .env for production!")
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize database
    from models import db
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes import main_bp, portfolio_bp, analysis_bp, settings_bp, news_bp, markets_bp
    from routes.api import api_bp
    from routes.auth import auth_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
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
        
        # Create tables if they don't exist
        db.create_all()
        
        # Create default admin user if no users exist
        from models.user import User
        if User.query.count() == 0:
            print("Creating default admin user...")
            admin = User(username='admin', email='admin@risk-monitoring.local', is_admin=True)
            admin.set_password('Admin123!@#')  # CHANGE THIS IN PRODUCTION
            db.session.add(admin)
            db.session.commit()
            print("✓ Default admin user created (username: admin, password: Admin123!@#)")
            print("  ⚠️  IMPORTANT: Change the default password immediately!")
    
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
    
    # ========================================================================
    # Health Check Endpoint (for Docker/Kubernetes)
    # ========================================================================
    @app.route('/health')
    def health_check():
        """
        Health check endpoint for container orchestration.
        Returns 200 if all critical services are operational.
        """
        from flask import jsonify
        import time
        
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        # Check database connection
        try:
            from models import db
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Check Redis connection (if configured)
        try:
            import redis
            redis_url = app.config.get('REDIS_URL')
            if redis_url:
                r = redis.from_url(redis_url)
                r.ping()
                health_status['checks']['redis'] = 'healthy'
            else:
                health_status['checks']['redis'] = 'not_configured'
        except Exception as e:
            health_status['checks']['redis'] = f'unhealthy: {str(e)}'
            # Redis is optional, don't mark overall health as unhealthy
        
        # Return appropriate status code
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    
    # ========================================================================
    # Metrics Endpoint (for Prometheus)
    # ========================================================================
    @app.route('/metrics')
    def metrics():
        """
        Prometheus metrics endpoint.
        Requires prometheus_client package.
        """
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from flask import Response
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
        except ImportError:
            return "Prometheus client not installed", 501
    
    return app

# ============================================================================
# Create app instance for WSGI servers (Gunicorn, uWSGI, etc.)
# ============================================================================
app = create_app(os.getenv('FLASK_CONFIG', 'default'))

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.getenv('FLASK_CONFIG', 'default')
    
    # Create app instance
    app = create_app(config_name)
    
    # Run the application
    debug_mode = app.config.get('DEBUG', False)
    app.run(debug=debug_mode)