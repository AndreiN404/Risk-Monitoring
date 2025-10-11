"""Background scheduler for periodic tasks"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# Global scheduler instance
scheduler = None

def fetch_news_task():
    """
    Background task to fetch news from multiple RSS feeds every 5 minutes
    Runs independently of HTTP requests
    """
    try:
        from services.news_service import fetch_news_from_sources, save_articles_to_db
        from models.database import db
        from flask import current_app
        
        with current_app.app_context():
            logging.info("Starting scheduled news fetch from RSS feeds...")
            articles = fetch_news_from_sources()
            
            if articles:
                saved_count, skipped_count = save_articles_to_db(articles)
                logging.info(f"Scheduled fetch: Retrieved {len(articles)} articles, saved {saved_count} new ones")
            else:
                logging.warning("Scheduled fetch: No articles found")
                
    except Exception as e:
        logging.error(f"Error in scheduled news fetch: {e}", exc_info=True)

def init_scheduler(app):
    """
    Initialize the background scheduler with the Flask app
    
    Args:
        app: Flask application instance
    """
    global scheduler
    
    if scheduler is not None:
        logging.warning("Scheduler already initialized")
        return scheduler
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add news fetching job - runs every 5 minutes
    scheduler.add_job(
        func=lambda: fetch_news_task(),
        trigger=IntervalTrigger(minutes=5),
        id='fetch_news_job',
        name='Fetch news from Finviz every 5 minutes',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logging.info("Background scheduler started - news will be fetched every 5 minutes")
    
    # Shutdown scheduler when app stops
    import atexit
    atexit.register(lambda: scheduler.shutdown())
    
    # Run initial fetch immediately
    with app.app_context():
        try:
            logging.info("Running initial news fetch on startup...")
            fetch_news_task()
        except Exception as e:
            logging.error(f"Error in initial news fetch: {e}")
    
    return scheduler

def get_scheduler():
    """Get the scheduler instance"""
    return scheduler

def shutdown_scheduler():
    """Shutdown the scheduler"""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logging.info("Background scheduler stopped")
