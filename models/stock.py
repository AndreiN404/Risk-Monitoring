from models.database import db

class StockData(db.Model):
    """Model for storing historical stock price data"""
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Create unique constraint on ticker and date
    __table_args__ = (db.UniqueConstraint('ticker', 'date', name='unique_ticker_date'),)

    def __repr__(self):
        return f'<StockData {self.ticker} {self.date}>'

class StockAnalysisCache(db.Model):
    """Model for caching stock analysis metadata"""
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    period = db.Column(db.String(10), nullable=False, default='1y')
    data_start_date = db.Column(db.Date, nullable=False)
    data_end_date = db.Column(db.Date, nullable=False)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    row_count = db.Column(db.Integer, nullable=False, default=0)
    is_valid = db.Column(db.Boolean, nullable=False, default=True)
    
    # Create unique constraint on ticker and period
    __table_args__ = (db.UniqueConstraint('ticker', 'period', name='unique_ticker_period'),)

    def __repr__(self):
        return f'<StockAnalysisCache {self.ticker} {self.period}>'

class RiskMetrics(db.Model):
    """Model for storing calculated risk metrics for stocks"""
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_data.id'), nullable=False)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<RiskMetrics {self.metric_name}: {self.metric_value}>'