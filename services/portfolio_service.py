from models import db, Portfolio, PortfolioAsset
from datetime import datetime
from services.data_service import data_service

class PortfolioService:
    """Service for portfolio management operations"""
    
    @staticmethod
    def calculate_portfolio_weights(portfolio_id=None):
        """Calculate dynamic weights based on allocation amounts"""
        if portfolio_id:
            assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio_id).all()
        else:
            # Get the first (or default) portfolio
            portfolio = Portfolio.query.first()
            if not portfolio:
                return {}
            assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
        
        if not assets:
            return {}
        
        # Calculate total allocation
        total_allocation = sum(asset.allocation for asset in assets)
        
        if total_allocation == 0:
            return {}
        
        # Calculate weights as percentages
        weights = {}
        for asset in assets:
            weights[asset.symbol] = asset.allocation / total_allocation
        
        return weights

    @staticmethod
    def update_portfolio_weights(portfolio_id=None):
        """Update all portfolio asset weights based on current allocations"""
        weights = PortfolioService.calculate_portfolio_weights(portfolio_id)
        
        if portfolio_id:
            assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio_id).all()
        else:
            portfolio = Portfolio.query.first()
            if not portfolio:
                return
            assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
        
        # Update weights in database
        for asset in assets:
            if asset.symbol in weights:
                asset.weight = weights[asset.symbol]
        
        try:
            db.session.commit()
            print(f"Updated weights for {len(assets)} assets")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating weights: {e}")

    @staticmethod
    def get_or_create_default_portfolio():
        """Get the default portfolio or create one if none exists"""
        portfolio = Portfolio.query.first()
        if not portfolio:
            portfolio = Portfolio(name='My Portfolio')
            db.session.add(portfolio)
            db.session.commit()
        return portfolio

    @staticmethod
    def add_asset_to_portfolio(portfolio_id, symbol, asset_class, allocation, purchase_price=None, quantity=None, purchase_date=None):
        """Add an asset to a portfolio"""
        # Check if asset already exists in portfolio
        existing_asset = PortfolioAsset.query.filter_by(
            portfolio_id=portfolio_id, 
            symbol=symbol
        ).first()
        
        if existing_asset:
            # Update existing asset
            existing_asset.allocation = allocation
            existing_asset.asset_class = asset_class
            if purchase_price is not None:
                existing_asset.purchase_price = purchase_price
            if quantity is not None:
                existing_asset.quantity = quantity
            if purchase_date is not None:
                existing_asset.purchase_date = purchase_date
        else:
            # Create new asset
            asset = PortfolioAsset(
                portfolio_id=portfolio_id,
                symbol=symbol,
                asset_class=asset_class,
                weight=0,  # Will be calculated dynamically
                allocation=allocation,
                purchase_price=purchase_price,
                quantity=quantity,
                purchase_date=purchase_date
            )
            db.session.add(asset)
        
        try:
            db.session.commit()
            # Update all weights after adding/updating asset
            PortfolioService.update_portfolio_weights(portfolio_id)
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error adding asset to portfolio: {e}")
            return False

    @staticmethod
    def remove_asset_from_portfolio(portfolio_id, symbol):
        """Remove an asset from a portfolio"""
        asset = PortfolioAsset.query.filter_by(
            portfolio_id=portfolio_id, 
            symbol=symbol
        ).first()
        
        if asset:
            db.session.delete(asset)
            try:
                db.session.commit()
                # Update all weights after removing asset
                PortfolioService.update_portfolio_weights(portfolio_id)
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Error removing asset from portfolio: {e}")
                return False
        return False

    @staticmethod
    def get_portfolio_assets(portfolio_id):
        """Get all assets in a portfolio"""
        return PortfolioAsset.query.filter_by(portfolio_id=portfolio_id).all()

    @staticmethod
    def get_portfolio_summary(portfolio_id):
        """Get portfolio summary with total allocation and asset count"""
        assets = PortfolioService.get_portfolio_assets(portfolio_id)
        total_allocation = sum(asset.allocation for asset in assets)
        
        return {
            'total_assets': len(assets),
            'total_allocation': total_allocation,
            'assets': assets
        }

    @staticmethod
    def rebalance_portfolio(portfolio_id, target_allocations):
        """Rebalance portfolio to target allocations"""
        try:
            for symbol, allocation in target_allocations.items():
                asset = PortfolioAsset.query.filter_by(
                    portfolio_id=portfolio_id, 
                    symbol=symbol
                ).first()
                
                if asset:
                    asset.allocation = allocation
            
            db.session.commit()
            # Update all weights after rebalancing
            PortfolioService.update_portfolio_weights(portfolio_id)
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error rebalancing portfolio: {e}")
            return False

    @staticmethod
    def calculate_portfolio_pnl(portfolio_id, current_prices):
        """Calculate portfolio P&L based on purchase prices and current prices"""
        assets = PortfolioService.get_portfolio_assets(portfolio_id)
        total_pnl = 0
        total_invested = 0
        
        for asset in assets:
            if asset.purchase_price and asset.quantity and asset.symbol in current_prices:
                current_price = current_prices[asset.symbol]
                invested_amount = asset.purchase_price * asset.quantity
                current_value = current_price * asset.quantity
                asset_pnl = current_value - invested_amount
                
                total_pnl += asset_pnl
                total_invested += invested_amount
        
        pnl_percentage = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'total_pnl': total_pnl,
            'total_invested': total_invested,
            'pnl_percentage': pnl_percentage
        }

# Create a default instance
portfolio_service = PortfolioService()

def get_portfolio_data():
    """Get current portfolio from database with accurate P&L calculation"""
    portfolio = Portfolio.query.first()
    if not portfolio:
        return None, 0, 0, 0  # assets, total_value, total_cost, total_pnl
    
    assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
    total_cost = sum(asset.allocation for asset in assets)  # Initial cost basis (what was paid)
    
    # Get current market values
    symbols = [asset.symbol for asset in assets]
    
    if not symbols:
        return assets, total_cost, total_cost, 0
    
    try:
        live_prices = fetch_live_prices(symbols)
    except Exception as e:
        print(f"Error fetching live prices: {e}")
        # If we can't get live prices, assume no change
        return assets, total_cost, total_cost, 0
    
    # Calculate current value based on actual purchase prices
    total_current_value = 0
    
    for asset in assets:
        if asset.symbol in live_prices and live_prices[asset.symbol] is not None:
            current_price = live_prices[asset.symbol]
            
            if hasattr(asset, 'purchase_price') and hasattr(asset, 'quantity') and asset.purchase_price and asset.quantity:
                # Use actual purchase price and quantity for precise P&L
                current_value = current_price * asset.quantity
                total_current_value += current_value
                print(f"{asset.symbol}: {asset.quantity} shares @ ${current_price:.2f} = ${current_value:.2f} (bought @ ${asset.purchase_price:.2f})")
            else:
                # Fallback: estimate based on allocation and price changes from recent data
                try:
                    # Get recent historical data to establish a baseline
                    historical_data = data_service.fetch_stock_data([asset.symbol], period="5d", interval="daily")
                    
                    if not historical_data.empty:
                        # Handle both single and multi-column DataFrame cases
                        if 'Close' in historical_data.columns:
                            if hasattr(historical_data['Close'], 'columns'):
                                # Multi-column case (when fetching multiple tickers)
                                if asset.symbol in historical_data['Close'].columns:
                                    baseline_price = historical_data['Close'][asset.symbol].iloc[0]
                                else:
                                    baseline_price = current_price  # Use current price as baseline
                            else:
                                # Single column case
                                baseline_price = historical_data['Close'].iloc[0]
                        else:
                            baseline_price = current_price  # Use current price as baseline
                        
                        # Calculate price change ratio and apply to allocation
                        price_change_ratio = current_price / baseline_price
                        current_value = asset.allocation * price_change_ratio
                        total_current_value += current_value
                        print(f"{asset.symbol}: Estimated value ${current_value:.2f} (baseline: ${baseline_price:.2f}, current: ${current_price:.2f})")
                    else:
                        # No historical data, use allocation
                        total_current_value += asset.allocation
                        print(f"{asset.symbol}: Using allocation ${asset.allocation:.2f} (no historical data)")
                        
                except Exception as e:
                    print(f"Error calculating estimated value for {asset.symbol}: {e}")
                    # Ultimate fallback: use allocation as current value
                    total_current_value += asset.allocation
        else:
            # No live price available, use allocation as current value
            total_current_value += asset.allocation
            print(f"{asset.symbol}: No live price available, using allocation ${asset.allocation:.2f}")
    
    total_pnl = total_current_value - total_cost
    
    return assets, total_current_value, total_cost, total_pnl

def fetch_live_prices(symbols, force_refresh=False):
    """
    Fetch current/latest prices for given symbols using Alpha Vantage and yfinance
    Uses 5-minute caching to avoid unnecessary API calls unless force_refresh is True
    """
    import yfinance as yf
    import time
    from alpha_vantage.timeseries import TimeSeries
    from datetime import datetime
    
    # Use the data service cache
    cache_key = f"live_prices_{'-'.join(sorted(symbols))}"
    
    # Check cache first (unless force refresh is requested)
    if not force_refresh and hasattr(data_service, '_data_cache'):
        cached_data, cached_time = data_service._data_cache.get(cache_key, (None, None))
        if cached_data and (datetime.now() - cached_time).seconds < data_service.cache_timeout:
            print(f"Using cached live prices for {symbols} (fetched {(datetime.now() - cached_time).seconds}s ago)")
            return cached_data
    
    if force_refresh:
        print(f"Force refreshing live prices for {symbols}")
    else:
        print(f"Fetching fresh live prices for {symbols}")
    
    live_prices = {}
    ts = TimeSeries(key=data_service.alpha_vantage_api_key, output_format='pandas')
    
    for symbol in symbols:
        try:
            # For free Alpha Vantage tier, use daily data as intraday is premium only
            try:
                data, _ = ts.get_daily(symbol=symbol, outputsize='compact')
                if not data.empty:
                    # Get the most recent close price from daily data
                    latest_price = data['4. close'].iloc[0]  # Most recent daily close
                    live_prices[symbol] = float(latest_price)
                    print(f"Alpha Vantage daily price for {symbol}: ${latest_price:.2f}")
                else:
                    raise Exception("No daily data from Alpha Vantage")
            except Exception as av_error:
                error_msg = str(av_error).lower()
                print(f"Alpha Vantage failed for {symbol}: {av_error}")
                
                # Check for specific daily rate limit message
                if 'our standard api rate limit is 25 requests per day' in error_msg:
                    print(f"Alpha Vantage daily rate limit (25 requests/day) exceeded for {symbol}. Switching to yfinance.")
                elif 'rate limit' in error_msg:
                    print(f"Alpha Vantage rate limit exceeded for {symbol}. Falling back to yfinance.")
                
                raise Exception("Alpha Vantage failed")
            
            # Add small delay to respect rate limits
            time.sleep(0.2)
            
        except Exception as e:
            print(f"Trying yfinance for {symbol} live price")
            try:
                # Use yfinance for more recent/intraday data
                ticker_data = yf.Ticker(symbol)
                
                # Try to get 1-day 1-minute data for most recent price
                hist = ticker_data.history(period="1d", interval="1m")
                if not hist.empty:
                    latest_price = float(hist['Close'].iloc[-1])
                    live_prices[symbol] = latest_price
                    print(f"yfinance live price for {symbol}: ${latest_price:.2f}")
                else:
                    # Fallback to recent daily data
                    hist_daily = ticker_data.history(period="2d")
                    if not hist_daily.empty:
                        latest_price = float(hist_daily['Close'].iloc[-1])
                        live_prices[symbol] = latest_price
                        print(f"yfinance daily price for {symbol}: ${latest_price:.2f}")
                    else:
                        print(f"No price data available for {symbol}")
                        live_prices[symbol] = None
                        
            except Exception as e2:
                print(f"Failed to get live price for {symbol}: {e2}")
                live_prices[symbol] = None
    
    # Cache the live prices with current timestamp
    if hasattr(data_service, '_data_cache'):
        data_service._data_cache[cache_key] = (live_prices, datetime.now())
    
    return live_prices

def calculate_portfolio_dashboard_data(force_refresh=False):
    """Calculate comprehensive dashboard data for portfolio analysis"""
    from services.risk_calculator import ProfessionalRiskEngine
    
    try:
        # Get portfolio data
        assets, total_current_value, total_cost, total_pnl = get_portfolio_data()
        
        if not assets:
            # Return object with None values
            class EmptyDashboard:
                def __init__(self):
                    self.total_pnl = 0
                    self.pnl_percentage = 0
                    self.total_value = 0
                    self.total_cost = 0
                    self.volatility = 0.0
                    self.sharpe_ratio = 0.0
                    self.var_95 = 0.0
                    self.var_99 = 0.0
                    self.es_95 = 0.0
                    self.max_drawdown = 0.0
                    self.beta = 0.0
                    self.annual_return = 0.0
                    self.sortino_ratio = 0.0
                    self.calmar_ratio = 0.0
                    self.skewness = 0.0
                    self.daily_pnl = 0.0
                    self.live_prices = {}
                    self.price_changes = {}
                    self.price_update_time = None
                    self.is_prices_cached = False
                    self.asset_class_breakdown = {}
                    self.correlation_matrix = None
                    self.message = "No assets in portfolio"
            return EmptyDashboard()
        
        # Get symbols and fetch stock data
        symbols = [asset.symbol for asset in assets]
        
        # For portfolio-level analysis, we need to aggregate data
        individual_data = {}
        
        for asset in assets:
            try:
                # Fetch individual stock data
                stock_data = data_service.fetch_stock_data([asset.symbol])
                
                if not stock_data.empty:
                    # Perform risk analysis for each asset
                    risk_engine = ProfessionalRiskEngine(stock_data)
                    metrics = risk_engine.analyze()
                    
                    # Store individual asset metrics
                    individual_data[asset.symbol] = {
                        'weight': asset.weight,
                        'allocation': asset.allocation,
                        'metrics': metrics
                    }
                    
            except Exception as e:
                print(f"Error analyzing {asset.symbol}: {e}")
                individual_data[asset.symbol] = {
                    'weight': asset.weight,
                    'allocation': asset.allocation,
                    'metrics': {"Error": f"Analysis failed: {e}"}
                }
        
        # Create dashboard data object with attributes for template access
        class DashboardData:
            def __init__(self, total_value, total_cost, total_pnl, individual_data):
                self.total_value = total_value
                self.total_cost = total_cost
                self.total_pnl = total_pnl
                self.pnl_percentage = (total_pnl / total_cost * 100) if total_cost > 0 else 0
                self.total_assets = len(assets)
                self.individual_data = individual_data
                
                # Initialize all required attributes with defaults first
                self.volatility = 0.0
                self.sharpe_ratio = 0.0
                self.var_95 = 0.0
                self.var_99 = 0.0
                self.es_95 = 0.0  # Expected Shortfall 95%
                self.max_drawdown = 0.0
                self.beta = 0.0
                self.annual_return = 0.0
                self.sortino_ratio = 0.0
                self.calmar_ratio = 0.0
                self.daily_pnl = 0.0
                self.live_prices = {}
                self.price_changes = {}
                self.price_update_time = None
                self.is_prices_cached = False
                self.asset_class_breakdown = {}
                self.correlation_matrix = None
                self.skewness = 0.0
                
                # Calculate portfolio-level risk metrics
                self._calculate_portfolio_metrics()
                
                # Get live prices for assets
                self.live_prices = self._get_live_prices()
            
            def _calculate_portfolio_metrics(self):
                """Calculate portfolio-level risk metrics"""
                try:
                    # Get all portfolio symbols for combined analysis
                    symbols = [asset.symbol for asset in assets]
                    
                    if symbols and len(symbols) > 0:
                        # For now, let's use simple calculations for demonstration
                        # In a real application, you'd want more sophisticated portfolio-level metrics
                        
                        # Calculate a simple average volatility from individual assets
                        total_weight = sum(asset.weight for asset in assets if asset.weight)
                        weighted_volatility = 0.0
                        
                        for asset in assets:
                            try:
                                # Get individual asset data
                                asset_data = data_service.fetch_stock_data([asset.symbol], period="3mo")
                                if not asset_data.empty and 'Close' in asset_data.columns:
                                    # Calculate daily returns
                                    if hasattr(asset_data['Close'], 'columns') and asset.symbol in asset_data['Close'].columns:
                                        prices = asset_data['Close'][asset.symbol]
                                    else:
                                        prices = asset_data['Close']
                                    
                                    returns = prices.pct_change().dropna()
                                    if len(returns) > 1:
                                        asset_volatility = returns.std() * (252 ** 0.5)  # Annualized
                                        weight = asset.weight if asset.weight else (1.0 / len(assets))
                                        weighted_volatility += asset_volatility * weight
                                        
                                        # For the first asset, calculate some basic metrics
                                        if self.volatility == 0.0:  # First valid calculation
                                            self.volatility = asset_volatility
                                            self.sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0.0
                                            self.var_95 = returns.quantile(0.05)  # 5% VaR
                                            self.var_99 = returns.quantile(0.01)  # 1% VaR
                                            
                                            # Calculate Expected Shortfall (ES) 95%
                                            var_95_threshold = returns.quantile(0.05)
                                            es_returns = returns[returns <= var_95_threshold]
                                            self.es_95 = es_returns.mean() if len(es_returns) > 0 else var_95_threshold
                                            
                                            # Calculate annual return
                                            self.annual_return = returns.mean() * 252  # Annualized
                                            
                                            # Calculate max drawdown
                                            cumulative_returns = (1 + returns).cumprod()
                                            running_max = cumulative_returns.expanding().max()
                                            drawdown = (cumulative_returns - running_max) / running_max
                                            self.max_drawdown = drawdown.min()
                                            
                                            # Calculate Sortino ratio (downside deviation)
                                            downside_returns = returns[returns < 0]
                                            downside_std = downside_returns.std() if len(downside_returns) > 0 else returns.std()
                                            self.sortino_ratio = returns.mean() / downside_std * (252 ** 0.5) if downside_std > 0 else 0.0
                                            
                                            # Calculate Calmar ratio (annual return / max drawdown)
                                            self.calmar_ratio = abs(self.annual_return / self.max_drawdown) if self.max_drawdown != 0 else 0.0
                                            
                                            # Calculate skewness
                                            self.skewness = returns.skew() if len(returns) > 2 else 0.0
                                            
                                            # For beta calculation, we'd need market data (SPY)
                                            # For now, set a default value
                                            self.beta = 1.0  # Default market beta
                                            
                                            self.daily_pnl = returns.iloc[-1] if len(returns) > 0 else 0.0
                                            
                            except Exception as e:
                                print(f"Error calculating metrics for {asset.symbol}: {e}")
                                continue
                        
                        # Update with weighted volatility if calculated
                        if weighted_volatility > 0:
                            self.volatility = weighted_volatility
                    
                    # Calculate asset class breakdown
                    self._calculate_asset_class_breakdown()
                    
                    # Calculate correlation matrix
                    self._calculate_correlation_matrix()
                    
                except Exception as e:
                    print(f"Error in portfolio metrics calculation: {e}")
                    # Keep default values that were already set
            
            def _calculate_asset_class_breakdown(self):
                """Calculate breakdown by asset class"""
                try:
                    breakdown = {}
                    total_portfolio_allocation = 0.0
                    
                    # First pass: calculate total allocation and count by asset class
                    for asset in assets:
                        asset_class = asset.asset_class if asset.asset_class else 'Other'
                        allocation = asset.allocation if asset.allocation else 0.0
                        total_portfolio_allocation += allocation
                        
                        if asset_class not in breakdown:
                            breakdown[asset_class] = {
                                'count': 0,
                                'total_allocation': 0.0,
                                'symbols': []
                            }
                        breakdown[asset_class]['count'] += 1
                        breakdown[asset_class]['total_allocation'] += allocation
                        breakdown[asset_class]['symbols'].append(asset.symbol)
                    
                    # Second pass: convert to percentages if total > 0
                    if total_portfolio_allocation > 0:
                        for asset_class in breakdown:
                            breakdown[asset_class]['total_allocation'] = (
                                breakdown[asset_class]['total_allocation'] / total_portfolio_allocation * 100
                            )
                    
                    self.asset_class_breakdown = breakdown
                except Exception as e:
                    print(f"Error calculating asset class breakdown: {e}")
                    self.asset_class_breakdown = {}
            
            def _calculate_correlation_matrix(self):
                """Calculate correlation matrix for portfolio assets"""
                try:
                    symbols = [asset.symbol for asset in assets]
                    if len(symbols) > 1:
                        # Fetch data for correlation calculation
                        portfolio_data = data_service.fetch_stock_data(symbols, period="3mo")
                        if not portfolio_data.empty and 'Close' in portfolio_data.columns:
                            # Calculate returns for correlation
                            if hasattr(portfolio_data['Close'], 'columns'):
                                returns_data = portfolio_data['Close'].pct_change().dropna()
                                correlation_matrix = returns_data.corr()
                                # Convert to simple HTML table
                                self.correlation_matrix = correlation_matrix.to_html(classes='table table-sm', float_format='%.2f')
                            else:
                                self.correlation_matrix = None
                        else:
                            self.correlation_matrix = None
                    else:
                        self.correlation_matrix = None
                except Exception as e:
                    print(f"Error calculating correlation matrix: {e}")
                    self.correlation_matrix = None
            
            def _get_live_prices(self):
                """Get current live prices for all portfolio assets"""
                import datetime
                live_prices = {}
                price_changes = {}
                
                try:
                    for asset in assets:
                        try:
                            # Fetch current price data
                            current_data = data_service.fetch_stock_data([asset.symbol], period="1d", interval="1m")
                            if not current_data.empty and 'Close' in current_data.columns:
                                if hasattr(current_data['Close'], 'columns') and asset.symbol in current_data['Close'].columns:
                                    prices = current_data['Close'][asset.symbol]
                                else:
                                    prices = current_data['Close']
                                
                                current_price = float(prices.iloc[-1])
                                live_prices[asset.symbol] = current_price
                                
                                # Calculate price change percentage if we have enough data
                                if len(prices) > 1:
                                    previous_price = float(prices.iloc[-2])
                                    if previous_price > 0:
                                        price_change = ((current_price - previous_price) / previous_price) * 100
                                        price_changes[asset.symbol] = price_change
                                    else:
                                        price_changes[asset.symbol] = 0.0
                                else:
                                    price_changes[asset.symbol] = 0.0
                            else:
                                live_prices[asset.symbol] = 0.0
                                price_changes[asset.symbol] = 0.0
                        except Exception as e:
                            print(f"Error getting live price for {asset.symbol}: {e}")
                            live_prices[asset.symbol] = 0.0
                            price_changes[asset.symbol] = 0.0
                    
                    # Update instance attributes
                    self.price_changes = price_changes
                    self.price_update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.is_prices_cached = False  # Assume fresh data for now
                    
                except Exception as e:
                    print(f"Error getting live prices: {e}")
                
                return live_prices
        
        return DashboardData(total_current_value, total_cost, total_pnl, individual_data)
        
    except Exception as e:
        print(f"Error calculating dashboard data: {e}")
        # Return object with error
        class ErrorDashboard:
            def __init__(self, error_msg):
                self.total_pnl = 0
                self.pnl_percentage = 0
                self.total_value = 0
                self.total_cost = 0
                self.volatility = 0.0
                self.sharpe_ratio = 0.0
                self.var_95 = 0.0
                self.var_99 = 0.0
                self.es_95 = 0.0
                self.max_drawdown = 0.0
                self.beta = 0.0
                self.annual_return = 0.0
                self.sortino_ratio = 0.0
                self.calmar_ratio = 0.0
                self.daily_pnl = 0.0
                self.live_prices = {}
                self.price_changes = {}
                self.price_update_time = None
                self.is_prices_cached = False
                self.asset_class_breakdown = {}
                self.correlation_matrix = None
                self.skewness = 0.0
                self.error = error_msg
        return ErrorDashboard(f"Dashboard calculation failed: {e}")