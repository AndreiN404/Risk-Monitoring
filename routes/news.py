from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from services.news_service import fetch_news_from_sources, save_articles_to_db
# Sentiment analysis is optional (requires torch/transformers)
try:
    from services.sentiment_service import get_sentiment_summary
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    def get_sentiment_summary(*args, **kwargs):
        return {"error": "Sentiment analysis not available (transformers not installed)"}
        
from models.news import NewsArticle
from models.database import db

news_bp = Blueprint('news', __name__)

# Protect all routes in this blueprint
@news_bp.before_request
@login_required
def require_login():
    """Require authentication for all news routes"""
    pass

@news_bp.route('/news', methods=['GET', 'POST'])
def news():
    """News page to display latest financial news articles"""
    if request.method == 'POST':
        action = request.form.get('action', 'fetch')
        
        if action == 'clear':
            # Clear all news articles from database
            try:
                count = NewsArticle.query.delete()
                db.session.commit()
                flash(f'Successfully cleared {count} articles from database', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error clearing database: {str(e)}', 'danger')
        else:
            # Fetch latest news from RSS feeds
            try:
                articles = fetch_news_from_sources()
                if articles:
                    saved_count, skipped_count = save_articles_to_db(articles)
                    flash(f'Successfully fetched {len(articles)} articles, saved {saved_count} new ones ({skipped_count} duplicates)', 'success')
                else:
                    flash('No articles found', 'warning')
            except Exception as e:
                flash(f'Error fetching news: {str(e)}', 'danger')
        return redirect(url_for('news.news'))
    
    # Display recent news articles from the database
    try:
        recent_articles = NewsArticle.query.order_by(NewsArticle.timestamp.desc()).limit(50).all()
        
        # Get sentiment summary for last 7 days
        sentiment_summary = get_sentiment_summary(days=7)
    except Exception as e:
        recent_articles = []
        sentiment_summary = None
        flash(f'Error loading news from database: {str(e)}', 'warning')
    
    return render_template('news.html', articles=recent_articles, sentiment=sentiment_summary)


@news_bp.route('/api/news/sentiment', methods=['GET'])
def get_sentiment():
    """API endpoint to get sentiment analysis"""
    try:
        days = request.args.get('days', 7, type=int)
        sentiment_summary = get_sentiment_summary(days=days)
        return jsonify(sentiment_summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
