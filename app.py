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
    from routes import main_bp, portfolio_bp, analysis_bp, settings_bp, news_bp
    from routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(api_bp)
    
    # Initialize database within app context
    with app.app_context():
        from utils.database import init_database
        if not init_database():
            print("Warning: Database initialization failed")
    
    # Initialize background scheduler for periodic tasks
    from services.scheduler import init_scheduler
    init_scheduler(app)
    
    return app

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.getenv('FLASK_CONFIG', 'default')
    
    # Create app instance
    app = create_app(config_name)
    
    # Run the application
    debug_mode = app.config.get('DEBUG', False)
    app.run(debug=debug_mode)