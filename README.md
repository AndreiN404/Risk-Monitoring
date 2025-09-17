# Risk Engine

A comprehensive portfolio risk management and analysis platform built with Flask, featuring real-time market data, interactive charting, and sophisticated risk analytics.

## 🚀 Features Overview

### 📊 Portfolio Management
- **Asset Management**: Add/remove assets with support for multiple asset classes
- **Real-time P&L Tracking**: Live profit/loss calculations with color-coded performance indicators
- **Asset Class Diversification**: Track investments across US Equity, International Equity, Fixed Income, REITs, Commodities, Crypto, and Cash
- **Preset Portfolios**: Quick-start with Conservative, Balanced, or Aggressive allocation templates

### 📈 Interactive Charts & Analysis
- **TradingView Lightweight Charts**: Professional-grade candlestick charts for historical price analysis
- **Multi-timeframe Support**: View 1-day to 1-year historical data
- **Volume Analysis**: Integrated volume charts with price data
- **Chart Controls**: Interactive zooming, panning, and crosshair functionality
- **Real-time Data Integration**: Live price updates with historical context

### 🔍 Risk Analytics
- **Portfolio Risk Metrics**: Comprehensive risk analysis including volatility, Sharpe ratio, and correlation matrices
- **Individual Asset Analysis**: Detailed risk/return profiles for each holding
- **Asset Class Breakdown**: Portfolio composition analysis by asset class
- **Daily P&L Tracking**: Monitor daily portfolio performance changes
- **Risk-Free Rate Configuration**: Customizable benchmark for Sharpe ratio calculations

### ⚡ Performance Optimization
- **Multi-tier Caching System**: 
  - Memory cache for immediate data access
  - Database cache for persistent storage
  - API fallback for fresh data
- **Database-Backed Analysis Cache**: Stores analysis data for faster repeated lookups
- **Smart Cache Management**: Automatic cache invalidation and manual cache clearing
- **Rate Limit Protection**: Intelligent API usage to stay within provider limits

### 🎨 User Experience
- **Light/Dark Theme Toggle**: 
  - Three theme options: Light, Dark, System Default
  - Instant theme switching via navbar dropdown
  - System preference detection and auto-switching
  - Persistent theme preferences across sessions
- **Responsive Design**: Mobile-friendly interface using DaisyUI components
- **Real-time Updates**: AJAX-powered features for seamless user experience
- **Flash Messaging**: Clear feedback for user actions and system status

### 📡 Data Sources & Integration
- **Alpha Vantage API**: Professional market data for comprehensive analysis
- **Yahoo Finance (yfinance)**: Reliable backup data source
- **Live Price Feeds**: Real-time market data integration
- **Historical Data**: Up to 1 year of daily OHLCV data
- **Multi-symbol Support**: Simultaneous tracking of multiple assets

## 🏗️ Technical Architecture

### Backend Stack
- **Flask**: Lightweight Python web framework
- **SQLAlchemy**: Database ORM with SQLite backend
- **Pandas & NumPy**: Advanced data manipulation and numerical computing
- **yfinance**: Yahoo Finance API integration
- **Alpha Vantage**: Professional market data API

### Frontend Stack
- **TailwindCSS**: Utility-first CSS framework
- **DaisyUI**: Beautiful component library
- **TradingView Lightweight Charts**: Professional charting library
- **Vanilla JavaScript**: Efficient client-side interactions

### Database Schema
- **Portfolio**: Portfolio metadata and configuration
- **PortfolioAsset**: Individual asset holdings with dynamic weights
- **StockData**: Historical price data cache
- **StockAnalysisCache**: Analysis results cache for performance
- **PortfolioMetrics**: Historical performance tracking
- **Snapshot**: Portfolio state snapshots

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Alpha Vantage API key (optional, falls back to Yahoo Finance)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd risk-engine
   ```

2. **Create virtual environment**
   ```bash
   python -m venv env
   # Windows
   .\env\Scripts\activate
   # macOS/Linux
   source env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install flask flask-sqlalchemy pandas numpy yfinance alpha-vantage beautifulsoup4 requests
   ```

4. **Set environment variables (optional)**
   ```bash
   # Windows
   set ALPHA_VANTAGE_API_KEY=your_api_key_here
   # macOS/Linux
   export ALPHA_VANTAGE_API_KEY=your_api_key_here
   ```

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

## 🎯 Key Features Deep Dive

### Dynamic Portfolio Weights
Unlike traditional portfolio managers that require manual weight entry, Risk Engine automatically calculates portfolio weights based on your dollar allocations:

- **Add $50,000 AAPL + $30,000 GOOGL + $20,000 BND = 50%/30%/20% allocation**
- **Automatic rebalancing** when assets are added or removed
- **Real-time weight updates** maintaining 100% allocation

### Interactive Charting
Powered by TradingView Lightweight Charts for professional-grade analysis:
- **Candlestick charts** with OHLC data
- **Volume indicators** synchronized with price action
- **Interactive controls** for zooming and crosshair analysis
- **Mobile-responsive** design for analysis on any device

### Multi-tier Caching
Sophisticated caching system for optimal performance:
1. **Memory Cache**: Instant access to recently fetched data
2. **Database Cache**: Persistent storage for historical analysis
3. **API Fallback**: Fresh data when cache expires
4. **Smart Invalidation**: Automatic cache refresh and manual clearing

### Theme System
Comprehensive theming with system integration:
- **Light Theme**: Clean, professional appearance for daytime use
- **Dark Theme**: Reduced eye strain for late-night trading
- **System Default**: Automatically follows your OS preference
- **Instant Switching**: No page refresh required

## 🛠️ Development

### Project Structure
```
risk-engine/
├── app.py                 # Main Flask application
├── risk_engine.db         # SQLite database
├── templates/            # HTML templates
│   ├── base.html         # Base template with theming
│   ├── index.html        # Dashboard
│   ├── portfolio.html    # Portfolio management
│   ├── analysis.html     # Stock analysis with charts
│   └── settings.html     # Configuration and preferences
├── static/              # Static assets
├── instance/            # Instance-specific files
└── env/                 # Virtual environment
```

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

## 🔒 Security Considerations

- **Session Management**: Secure session handling for user preferences
- **API Key Protection**: Environment variable storage for sensitive keys
- **Input Validation**: Comprehensive validation for all user inputs
- **Error Handling**: Graceful error handling without exposing internals

## 🚀 Future Enhancements

- **User Authentication**: Multi-user support with secure login
- **Advanced Analytics**: Monte Carlo simulations, VaR calculations
- **Backtesting Engine**: Historical portfolio performance simulation
- **Alert System**: Price and risk threshold notifications
- **Export Features**: PDF reports and CSV data exports
- **Mobile App**: Native mobile application for portfolio monitoring

**Risk Engine** - Professional Portfolio Risk Management Made Simple