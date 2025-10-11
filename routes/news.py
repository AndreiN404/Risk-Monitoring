from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.news_service import fetch_news_from_sources, save_articles_to_db
from models.news import NewsArticle
from models.database import db

news_bp = Blueprint('news', __name__)

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
    except Exception as e:
        recent_articles = []
        flash(f'Error loading news from database: {str(e)}', 'warning')
    
    return render_template('news.html', articles=recent_articles)
