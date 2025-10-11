"""Service for fetching news articles from RSS feeds of financial news sources"""
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
import feedparser
from models.database import db
from models.news import NewsArticle


# RSS feeds from major financial news sources
NEWS_SOURCES = {
    'MarketWatch': 'https://www.marketwatch.com/rss/topstories',
    'CNBC': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
    'Yahoo Finance': 'https://finance.yahoo.com/news/rssindex',
    'Seeking Alpha': 'https://seekingalpha.com/feed.xml',
    'Benzinga': 'https://www.benzinga.com/feed',
    'Investing.com': 'https://www.investing.com/rss/news.rss',
}


def _parse_entry_timestamp(entry, source_name):
    """
    Parse timestamp from RSS feed entry with multiple fallback methods.
    
    Args:
        entry: RSS feed entry object
        source_name: Name of the source for logging
        
    Returns:
        datetime object or None if parsing fails
    """
    timestamp = None
    
    # Try published_parsed first
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            timestamp = datetime(*entry.published_parsed[:6])
            logging.debug(f"{source_name}: Using published_parsed: {timestamp}")
        except Exception as e:
            logging.debug(f"{source_name}: Error with published_parsed: {e}")
    
    # Try updated_parsed as fallback
    if not timestamp and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        try:
            timestamp = datetime(*entry.updated_parsed[:6])
            logging.debug(f"{source_name}: Using updated_parsed: {timestamp}")
        except Exception as e:
            logging.debug(f"{source_name}: Error with updated_parsed: {e}")
    
    # Try parsing published string directly
    if not timestamp and hasattr(entry, 'published'):
        try:
            timestamp = parsedate_to_datetime(entry.published)
            logging.debug(f"{source_name}: Parsed published string: {timestamp}")
        except Exception as e:
            logging.debug(f"{source_name}: Error parsing published string: {e}")
    
    return timestamp


def _parse_feed_entries(feed, source_name, max_articles=10):
    """
    Parse entries from an RSS feed.
    
    Args:
        feed: Parsed RSS feed object
        source_name: Name of the source
        max_articles: Maximum number of articles to extract
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    for entry in feed.entries[:max_articles]:
        try:
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()
            
            if not title or not link:
                continue
            
            # Parse timestamp
            timestamp = _parse_entry_timestamp(entry, source_name)
            
            # Use current time if no timestamp found
            if not timestamp:
                timestamp = datetime.now()
                logging.warning(f"{source_name}: No timestamp for '{title[:50]}...', using current time")
            
            articles.append({
                'ticker': source_name,
                'title': title,
                'link': link,
                'timestamp': timestamp.isoformat()
            })
            
        except Exception as e:
            logging.debug(f"Error parsing entry from {source_name}: {e}")
            continue
    
    return articles




def fetch_news_from_sources():
    """
    Fetch latest news articles from multiple RSS feeds.
    
    Returns:
        List of news articles sorted by timestamp (newest first)
    """
    all_articles = []
    
    for source_name, feed_url in NEWS_SOURCES.items():
        try:
            logging.info(f"Fetching news from {source_name}...")
            
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logging.warning(f"Feed parsing issue for {source_name}: {feed.bozo_exception}")
            
            # Parse entries from feed
            articles = _parse_feed_entries(feed, source_name)
            all_articles.extend(articles)
            
            logging.info(f"Fetched {len(articles)} articles from {source_name}")
            
        except Exception as e:
            logging.error(f"Error fetching from {source_name}: {e}")
            continue
    
    # Sort articles by timestamp (newest first)
    all_articles.sort(key=lambda x: datetime.fromisoformat(x['timestamp']), reverse=True)
    
    logging.info(f"Total articles fetched: {len(all_articles)}")
    return all_articles


def save_articles_to_db(articles):
    """
    Save fetched articles to the database, avoiding duplicates.
    
    Args:
        articles: List of articles to save
        
    Returns:
        Tuple of (saved_count, skipped_count)
    """
    saved_count = 0
    skipped_count = 0
    
    for article in articles:
        try:
            # Generate unique ID based on hash of title and link
            article_id = hash((article['title'], article['link']))
            
            # Check if article already exists
            existing = NewsArticle.query.filter_by(id=article_id).first()
            if existing:
                skipped_count += 1
                continue
            
            # Create new article
            new_article = NewsArticle(
                id=article_id,
                ticker=article.get('ticker', 'GENERAL'),
                title=article['title'],
                link=article['link'],
                timestamp=datetime.fromisoformat(article['timestamp']) if article.get('timestamp') else datetime.now(),
            )
            
            db.session.add(new_article)
            saved_count += 1
            
        except Exception as e:
            logging.error(f"Error saving article '{article.get('title', 'unknown')}': {e}")
            continue
    
    try:
        db.session.commit()
        logging.info(f"Saved {saved_count} new articles to database (skipped {skipped_count} duplicates)")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error committing articles to database: {e}")
        saved_count = 0
    
    return saved_count, skipped_count


