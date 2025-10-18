from flask import Blueprint, render_template, request, session, jsonify, current_app, flash
from flask_login import login_required
import pandas as pd

analysis_bp = Blueprint('analysis', __name__)

# Protect all routes in this blueprint
@analysis_bp.before_request
@login_required
def require_login():
    """Require authentication for all analysis routes"""
    pass

@analysis_bp.route('/analysis', methods=['GET', 'POST'])
def analysis():
    """Stock analysis page with risk metrics - Plugin-driven architecture"""
    results = {}
    chart_data = {}
    
    if request.method == 'POST':
        ticker = request.form['ticker'].upper()
        
        # Get plugin manager
        pm = current_app.plugin_manager
        
        # Get data provider plugin (yfinance by default)
        data_plugin = pm.get_enabled_plugin('data_providers', 'yfinance_provider')
        if not data_plugin:
            flash('No data provider plugin available. Please enable a data provider.', 'error')
            return render_template('analysis.html', results={}, chart_data={})
        
        try:
            # Fetch stock data via plugin
            stock_data = data_plugin.get_historical_data(ticker, period='1y')
            
            if stock_data is not None and not stock_data.empty:
                # Get analytics plugin for risk calculations
                risk_plugin = pm.get_enabled_plugin('analytics', 'risk_calculator_plugin')
                
                if risk_plugin:
                    # Use plugin for risk analysis
                    results = risk_plugin.calculate_metrics(ticker, stock_data)
                else:
                    # Fallback: use standalone risk calculations
                    from services.risk_calculator import ProfessionalRiskEngine
                    risk_engine = ProfessionalRiskEngine(stock_data)
                    results = risk_engine.analyze()
                
                # Prepare chart data for TradingView
                if 'Close' in stock_data.columns:
                    chart_data = prepare_chart_data(stock_data, ticker)
            else:
                flash(f'No data found for ticker {ticker}', 'warning')
                
        except Exception as e:
            flash(f'Error fetching data for {ticker}: {str(e)}', 'error')
            print(f"Analysis error: {e}")
    
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