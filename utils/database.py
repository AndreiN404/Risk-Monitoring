from models import db
from sqlalchemy import inspect, text

def init_database():
    """Initialize database with all necessary tables and migrations"""
    try:
        # Create all tables
        db.create_all()
        print("Database tables created successfully.")
        
        # Add missing columns for backward compatibility
        inspector = inspect(db.engine)
        
        # Check and add missing columns to stock_data table
        if 'stock_data' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('stock_data')]
            
            if 'created_at' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE stock_data ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP'))
                        conn.commit()
                    print("Added created_at column to stock_data table")
                except Exception as e:
                    print(f"Note: Could not add created_at column to stock_data: {e}")
        
        # Check and add missing columns to portfolio_asset table
        if 'portfolio_asset' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('portfolio_asset')]
            
            # Add missing columns if they don't exist
            if 'purchase_price' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN purchase_price FLOAT'))
                        conn.commit()
                    print("Added purchase_price column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add purchase_price column: {e}")
            
            if 'quantity' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN quantity FLOAT'))
                        conn.commit()
                    print("Added quantity column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add quantity column: {e}")
            
            if 'purchase_date' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN purchase_date DATE'))
                        conn.commit()
                    print("Added purchase_date column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add purchase_date column: {e}")
            
            if 'realized_pnl' not in columns:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE portfolio_asset ADD COLUMN realized_pnl FLOAT DEFAULT 0.0'))
                        conn.commit()
                    print("Added realized_pnl column to portfolio_asset table")
                except Exception as e:
                    print(f"Note: Could not add realized_pnl column: {e}")
        
        print("Database initialization completed successfully.")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def reset_database():
    """Reset database by dropping and recreating all tables"""
    try:
        db.drop_all()
        print("Database tables dropped.")
        return init_database()
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

def check_database_health():
    """Check if database is accessible and has required tables"""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = [
            'portfolio', 
            'portfolio_asset', 
            'stock_data', 
            'stock_analysis_cache',
            'risk_metrics',
            'portfolio_metrics',
            'snapshot',
            'transaction'
        ]
        
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            return False
        
        print("Database health check passed.")
        return True
        
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False