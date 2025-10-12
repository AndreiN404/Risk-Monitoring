"""Service for analyzing financial news sentiment using FinBERT"""
import logging
from datetime import datetime, timedelta
from transformers import pipeline
from models.news import NewsArticle


# Initialize FinBERT pipeline (loaded once on startup)
_sentiment_pipeline = None


def get_sentiment_pipeline():
    """
    Get or initialize the FinBERT sentiment analysis pipeline.
    
    Returns:
        Hugging Face pipeline for sentiment analysis
    """
    global _sentiment_pipeline
    
    if _sentiment_pipeline is None:
        try:
            logging.info("Loading FinBERT model for sentiment analysis...")
            _sentiment_pipeline = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                top_k=None  # Return all scores
            )
            logging.info("FinBERT model loaded successfully")
        except Exception as e:
            logging.error(f"Error loading FinBERT model: {e}")
            raise
    
    return _sentiment_pipeline


def analyze_text_sentiment(text):
    """
    Analyze sentiment of a single text using FinBERT.
    
    Args:
        text: Text to analyze (news title or content)
        
    Returns:
        dict with 'label' (positive/negative/neutral) and 'scores' for each category
    """
    try:
        pipe = get_sentiment_pipeline()
        
        # Truncate text to avoid token limits (FinBERT max is 512 tokens)
        text = text[:512] if len(text) > 512 else text
        
        # Get predictions
        results = pipe(text)[0]
        
        # Convert to dict with all scores
        sentiment_scores = {
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 0.0
        }
        
        for result in results:
            label = result['label'].lower()
            score = result['score']
            sentiment_scores[label] = score
        
        # Determine primary sentiment
        primary_label = max(sentiment_scores, key=sentiment_scores.get)
        
        return {
            'label': primary_label,
            'scores': sentiment_scores,
            'confidence': sentiment_scores[primary_label]
        }
        
    except Exception as e:
        logging.error(f"Error analyzing sentiment: {e}")
        return {
            'label': 'neutral',
            'scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34},
            'confidence': 0.34
        }


def analyze_news_batch(articles, max_articles=100):
    """
    Analyze sentiment for a batch of news articles.
    
    Args:
        articles: List of NewsArticle objects or dicts with 'title' field
        max_articles: Maximum number of articles to analyze
        
    Returns:
        List of sentiment results
    """
    results = []
    
    for i, article in enumerate(articles[:max_articles]):
        if i % 10 == 0:
            logging.info(f"Analyzing sentiment for article {i+1}/{min(len(articles), max_articles)}")
        
        try:
            # Get title from article object or dict
            title = article.title if hasattr(article, 'title') else article.get('title', '')
            
            if not title:
                continue
            
            sentiment = analyze_text_sentiment(title)
            results.append({
                'title': title,
                'sentiment': sentiment['label'],
                'scores': sentiment['scores'],
                'confidence': sentiment['confidence']
            })
            
        except Exception as e:
            logging.debug(f"Error analyzing article: {e}")
            continue
    
    return results


def get_sentiment_summary(days=7):
    """
    Get sentiment summary for news articles from the last N days.
    
    Args:
        days: Number of days to analyze (default: 7)
        
    Returns:
        dict with overall sentiment statistics
    """
    try:
        # Get articles from last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_articles = NewsArticle.query.filter(
            NewsArticle.timestamp >= cutoff_date
        ).all()
        
        if not recent_articles:
            return {
                'total_articles': 0,
                'sentiment_counts': {'positive': 0, 'negative': 0, 'neutral': 0},
                'sentiment_percentages': {'positive': 0, 'negative': 0, 'neutral': 0},
                'average_scores': {'positive': 0, 'negative': 0, 'neutral': 0},
                'overall_sentiment': 'neutral',
                'days_analyzed': days
            }
        
        logging.info(f"Analyzing sentiment for {len(recent_articles)} articles from last {days} days")
        
        # Analyze all articles
        sentiment_results = analyze_news_batch(recent_articles)
        
        # Calculate statistics
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        sentiment_scores_sum = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
        
        for result in sentiment_results:
            label = result['sentiment']
            sentiment_counts[label] += 1
            
            # Sum up scores for averaging
            for sentiment_type, score in result['scores'].items():
                sentiment_scores_sum[sentiment_type] += score
        
        total = len(sentiment_results)
        
        # Calculate percentages
        sentiment_percentages = {
            'positive': round((sentiment_counts['positive'] / total) * 100, 1) if total > 0 else 0,
            'negative': round((sentiment_counts['negative'] / total) * 100, 1) if total > 0 else 0,
            'neutral': round((sentiment_counts['neutral'] / total) * 100, 1) if total > 0 else 0
        }
        
        # Calculate average scores
        average_scores = {
            'positive': round(sentiment_scores_sum['positive'] / total, 3) if total > 0 else 0,
            'negative': round(sentiment_scores_sum['negative'] / total, 3) if total > 0 else 0,
            'neutral': round(sentiment_scores_sum['neutral'] / total, 3) if total > 0 else 0
        }
        
        # Determine overall sentiment
        overall_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        return {
            'total_articles': total,
            'sentiment_counts': sentiment_counts,
            'sentiment_percentages': sentiment_percentages,
            'average_scores': average_scores,
            'overall_sentiment': overall_sentiment,
            'days_analyzed': days,
            'by_source': _group_by_source(sentiment_results, recent_articles)
        }
        
    except Exception as e:
        logging.error(f"Error getting sentiment summary: {e}")
        return {
            'total_articles': 0,
            'sentiment_counts': {'positive': 0, 'negative': 0, 'neutral': 0},
            'sentiment_percentages': {'positive': 0, 'negative': 0, 'neutral': 0},
            'average_scores': {'positive': 0, 'negative': 0, 'neutral': 0},
            'overall_sentiment': 'neutral',
            'days_analyzed': days,
            'error': str(e)
        }


def _group_by_source(sentiment_results, articles):
    """
    Group sentiment results by news source.
    
    Args:
        sentiment_results: List of sentiment analysis results
        articles: List of NewsArticle objects
        
    Returns:
        dict of sentiment counts by source
    """
    by_source = {}
    
    for i, article in enumerate(articles[:len(sentiment_results)]):
        source = article.ticker if hasattr(article, 'ticker') else 'Unknown'
        sentiment = sentiment_results[i]['sentiment']
        
        if source not in by_source:
            by_source[source] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
        
        by_source[source][sentiment] += 1
        by_source[source]['total'] += 1
    
    return by_source
