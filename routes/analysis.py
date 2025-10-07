from flask import Blueprint, render_template, request, session, jsonify
import pandas as pd
from services.data_service import data_service
from services.risk_calculator import ProfessionalRiskEngine

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analysis', methods=['GET', 'POST'])
def analysis():
    """Stock analysis page with risk metrics"""
    results = {}
    chart_data = {}
    
    if request.method == 'POST':
        ticker = request.form['ticker'].upper()
        
        # Fetch stock data
        stock_data = data_service.fetch_stock_data([ticker])
        
        if not stock_data.empty:
            # Perform risk analysis
            risk_engine = ProfessionalRiskEngine(stock_data)
            results = risk_engine.analyze()
            
            # Prepare chart data for TradingView
            if 'Close' in stock_data.columns:
                chart_data = prepare_chart_data(stock_data, ticker)
    
    return render_template('analysis.html', results=results, chart_data=chart_data)

def prepare_chart_data(stock_data, ticker):
    """Prepare stock data for TradingView charts"""
    try:
        # Reset index to get dates as a column
        data_with_dates = stock_data.reset_index()
        
        # Prepare candlestick data
        chart_data = []
        for _, row in data_with_dates.iterrows():
            if 'Date' in row.index:
                date = row['Date']
            else:
                date = row.name if hasattr(row, 'name') else row.index[0]
            
            # Convert timestamp to milliseconds
            timestamp = int(pd.Timestamp(date).timestamp() * 1000)
            
            chart_data.append({
                'time': timestamp,
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']) if 'Volume' in row.index else 0
            })
        
        return {
            'ticker': ticker,
            'data': chart_data
        }
    except Exception as e:
        print(f"Error preparing chart data: {e}")
        return {}