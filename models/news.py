from models.database import db

class NewsArticle(db.Model):
    """Model for storing news articles"""
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<NewsArticle {self.ticker} {self.title}>'

