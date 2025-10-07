# Risk Engine - Portfolio Risk Management

A Flask-based portfolio risk management application with real-time analytics and interactive charting. Features real-time market data, advanced risk analytics, and interactive dashboards for portfolio analysis.

## Key Features

- **Portfolio Management**: Auto-calculated portfolio weights from dollar allocations- **Portfolio Management** - Multi-asset portfolio tracking with real-time P&L

- **Real-Time Analytics**: Live P&L tracking with asset class breakdown-  **Risk Analytics** - VaR, volatility, Sharpe ratio, correlation analysis

- **Interactive Charts**: TradingView integration for professional analysis-  **Live Market Data** - Alpha Vantage & Yahoo Finance integration

- **Risk Assessment**: Sharpe ratios, correlations, and volatility metrics-  **Asset Diversification** - Class breakdown and allocation analysis

- **Multi-Source Data**: Alpha Vantage API with Yahoo Finance fallback- **Modular Architecture** - Clean separation of models, services, and routes

- **Smart Caching**: Multi-tier caching for optimal performance-  **Smart Caching** - Multi-tier caching for optimal performance

- **Theme System**: Light/Dark themes with system preference support- **Multi-symbol Support**: Simultaneous tracking of multiple assets


##  Quick Start

##  Technical Architecture

1. **Clone and setup** 
### Backend Stack

   ```bash
   git clone <repository>
   cd risk-engine
   python -m venv env

   ```
   
### Frontend Stack

- **TailwindCSS**: Utility-first CSS framework

2. **Install dependencies**- **DaisyUI**: Beautiful component library

   ```bash- **TradingView Lightweight Charts**: Professional charting library

   pip install -r requirements.txt- **Vanilla JavaScript**: Efficient client-side interactions

   ```

### Database Schema

3. **Run application**- **Portfolio**: Portfolio metadata and configuration

   ```bash- **PortfolioAsset**: Individual asset holdings with dynamic weights

   python app_modular.py- **StockData**: Historical price data cache

   ```- **StockAnalysisCache**: Analysis results cache for performance

- **PortfolioMetrics**: Historical performance tracking

4. **Access dashboard**- **Snapshot**: Portfolio state snapshots

   ```
   http://127.0.0.1:5000 
   
   ```
## 🚀 Getting Started

### Prerequisites

##  Usage- Python 3.8+

- Alpha Vantage API key (optional, falls back to Yahoo Finance)

- **Portfolio**: Add assets with dollar amounts - weights auto-calculated

- **Analytics**: Interactive TradingView charts and risk metrics  ### Installation

- **Dashboard**: Real-time P&L and asset allocation visualization

- **Settings**: Theme preferences and cache management1. **Clone the repository**

   ```bash

##  Architecture   git clone <repository-url>

   

``` cd risk-engine  ```

├── app_modular.py          # Main Flask application

├── models/                 # Database models

├── services/               # Business logic   

├── routes/                 # API endpoints 

├── templates/              # Jinja2 templates  

└── instance/               # Database storage   

# macOS/Linux

   source env/bin/activate

## ⚙️ Configuration


Set optional environment variables:

3. **Install dependencies**

```bash 
ALPHA_VANTAGE_API_KEY=your_key_here   
pip install flask flask-sqlalchemy pandas numpy yfinance alpha-vantage beautifulsoup4 requests

SECRET_KEY=your_secret_key  
```


4. **Set environment variables (optional)**


**Professional portfolio management with intelligent risk assessment**   # Windows
   set ALPHA_VANTAGE_API_KEY=your_api_key_here
   # macOS/Linux
   export ALPHA_VANTAGE_API_KEY=your_api_key_here


5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser to `http://127.0.0.1:5000`

## 📋 Usage Guide

### Creating Your First Portfolio

1. **Navigate to Portfolio Manager**
   - Click "Portfolio" in the navigation menu

2. **Add Assets**
   - Select asset symbol (e.g., AAPL, GOOGL)
   - Choose asset class from dropdown
   - Enter dollar allocation amount
   - Weights are calculated automatically based on allocations

3. **Use Preset Portfolios**
   - Choose from Conservative, Balanced, or Aggressive templates
   - Customize allocations as needed

### Analyzing Investments

1. **Stock Analysis**
   - Navigate to "Analysis" page
   - Enter stock symbol
   - View interactive TradingView charts
   - Analyze historical performance and volatility

2. **Portfolio Analytics**
   - Dashboard shows real-time P&L
   - View asset class breakdown
   - Monitor correlation matrices
   - Track daily performance changes

### Managing Settings

1. **Theme Preferences**
   - Choose Light, Dark, or System Default theme
   - Quick toggle via navbar dropdown
   - Preferences persist across sessions

2. **Risk Analysis Configuration**
   - Set custom risk-free rate for Sharpe ratio calculations
   - Configure analysis parameters

3. **Cache Management**
   - Clear cached data to force fresh API calls
   - Monitor cache performance and storage

## 🔧 Configuration

### Environment Variables
- `ALPHA_VANTAGE_API_KEY`: Your Alpha Vantage API key for premium data access
- `SECRET_KEY`: Flask secret key for session management (set in production)

### Database Configuration
The application uses SQLite by default with the following file:
- `risk_engine.db`: Main application database

### Cache Configuration
- **Memory Cache**: 5-minute timeout for live data
- **Database Cache**: 24-hour persistence for analysis data
- **API Rate Limits**: Intelligent throttling to respect provider limits

## Development

### Database Models
- **Portfolio**: Portfolio metadata
- **PortfolioAsset**: Individual holdings with auto-calculated weights
- **StockData**: OHLCV historical data cache
- **StockAnalysisCache**: Analysis metadata and cache control
- **PortfolioMetrics**: Performance tracking over time

### API Integration
- **Primary**: Alpha Vantage for comprehensive market data
- **Fallback**: Yahoo Finance via yfinance library
- **Rate Limiting**: Intelligent request throttling
- **Error Handling**: Graceful degradation when APIs are unavailable

## Security Considerations

- **Session Management**: Secure session handling for user preferences
- **API Key Protection**: Environment variable storage for sensitive keys
- **Input Validation**: Comprehensive validation for all user inputs
- **Error Handling**: Graceful error handling without exposing internals

## Future Enhancements

- **User Authentication**: Multi-user support with secure login
- **Advanced Analytics**: Monte Carlo simulations, VaR calculations
- **Backtesting Engine**: Historical portfolio performance simulation
- **Alert System**: Price and risk threshold notifications
- **Export Features**: PDF reports and CSV data exports
- **Mobile App**: Native mobile application for portfolio monitoring