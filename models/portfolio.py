from models.database import db

class Portfolio(db.Model):
    """Model for portfolio management"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='My Portfolio')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f'<Portfolio {self.name}>'

class PortfolioAsset(db.Model):
    """Model for individual assets within a portfolio"""
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    asset_class = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    allocation = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=True)  # Average price per share
    quantity = db.Column(db.Float, nullable=True)        # Current number of shares owned
    purchase_date = db.Column(db.Date, nullable=True)    # Date of initial purchase
    realized_pnl = db.Column(db.Float, default=0.0)      # Realized P&L from sells
    
    portfolio = db.relationship('Portfolio', backref='assets')

    def __repr__(self):
        return f'<PortfolioAsset {self.symbol} {self.weight}%>'

class Transaction(db.Model):
    """Model for tracking individual buy/sell transactions"""
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # 'BUY' or 'SELL'
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)  # quantity × price
    transaction_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    notes = db.Column(db.String(200), nullable=True)
    realized_pnl = db.Column(db.Float, nullable=True)  # Only for SELL transactions
    
    portfolio = db.relationship('Portfolio', backref='transactions')

    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.quantity} {self.symbol} @ ${self.price}>'

class PortfolioMetrics(db.Model):
    """Model for storing calculated portfolio-level metrics"""
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<PortfolioMetrics {self.metric_name}: {self.metric_value}>'

class Snapshot(db.Model):
    """Model for portfolio snapshots at specific points in time"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    description = db.Column(db.String(200), nullable=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=True)

    def __repr__(self):
        return f'<Snapshot {self.timestamp} - {self.description}>'