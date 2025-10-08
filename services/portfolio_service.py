from models import db, Portfolio, PortfolioAsset, Transaction
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
        """Add an asset to a portfolio
        
        Args:
            allocation: Total $ amount invested (optional if purchase_price and quantity provided)
            purchase_price: Price per share when purchased
            quantity: Number of shares
            
        Note: If purchase_price and quantity are provided, allocation is calculated automatically
        """
        if purchase_price is not None and quantity is not None:
            calculated_allocation = purchase_price * quantity
            if allocation is None or allocation == 0:
                allocation = calculated_allocation
            else:
                # If user provided allocation too, validate it matches
                if abs(allocation - calculated_allocation) > 0.01:
                    print(f"Warning: Provided allocation ${allocation} doesn't match purchase_price × quantity = ${calculated_allocation}")
                    print(f"Using calculated allocation ${calculated_allocation}")
                allocation = calculated_allocation
        
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
                purchase_date=purchase_date,
                realized_pnl=0.0
            )
            db.session.add(asset)
        
        try:
            db.session.commit()
            
            # Record the BUY transaction
            if purchase_price and quantity:
                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    transaction_type='BUY',
                    quantity=quantity,
                    price=purchase_price,
                    total_amount=purchase_price * quantity,
                    transaction_date=purchase_date if purchase_date else datetime.now(),
                    notes='Initial purchase'
                )
                db.session.add(transaction)
                db.session.commit()
            
            # Update all weights after adding/updating asset
            PortfolioService.update_portfolio_weights(portfolio_id)
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error adding asset to portfolio: {e}")
            return False

    @staticmethod
    def sell_asset(portfolio_id, symbol, quantity_to_sell, sell_price, sell_date=None):
        """Sell shares of an asset and track realized P&L
        
        Args:
            portfolio_id: ID of the portfolio
            symbol: Stock symbol
            quantity_to_sell: Number of shares to sell
            sell_price: Price per share for the sale
            sell_date: Date of sale (optional, defaults to now)
        
        Returns:
            dict with success status, realized P&L, and message
        """
        asset = PortfolioAsset.query.filter_by(
            portfolio_id=portfolio_id,
            symbol=symbol
        ).first()
        
        if not asset:
            return {
                'success': False,
                'message': f'Asset {symbol} not found in portfolio',
                'realized_pnl': 0
            }
        
        if not asset.quantity or asset.quantity <= 0:
            return {
                'success': False,
                'message': f'No shares of {symbol} to sell',
                'realized_pnl': 0
            }
        
        if quantity_to_sell > asset.quantity:
            return {
                'success': False,
                'message': f'Cannot sell {quantity_to_sell} shares. Only {asset.quantity} shares available.',
                'realized_pnl': 0
            }
        
        # Calculate realized P&L for this sale
        # P&L = (sell_price - purchase_price) × quantity_to_sell
        cost_basis = asset.purchase_price if asset.purchase_price else (asset.allocation / asset.quantity)
        sale_proceeds = sell_price * quantity_to_sell
        sale_cost = cost_basis * quantity_to_sell
        realized_pnl = sale_proceeds - sale_cost
        
        # Update asset
        remaining_quantity = asset.quantity - quantity_to_sell
        
        if remaining_quantity <= 0.0001:  # Essentially zero (floating point tolerance)
            # Sold all shares - remove asset from portfolio
            db.session.delete(asset)
        else:
            # Update quantity and allocation
            asset.quantity = remaining_quantity
            asset.allocation = cost_basis * remaining_quantity
            asset.realized_pnl = (asset.realized_pnl or 0) + realized_pnl
        
        try:
            # Record the SELL transaction
            transaction = Transaction(
                portfolio_id=portfolio_id,
                symbol=symbol,
                transaction_type='SELL',
                quantity=quantity_to_sell,
                price=sell_price,
                total_amount=sale_proceeds,
                transaction_date=sell_date if sell_date else datetime.now(),
                notes=f'Sold {quantity_to_sell} shares',
                realized_pnl=realized_pnl
            )
            db.session.add(transaction)
            db.session.commit()
            
            # Update weights
            PortfolioService.update_portfolio_weights(portfolio_id)
            
            return {
                'success': True,
                'message': f'Successfully sold {quantity_to_sell} shares of {symbol}',
                'realized_pnl': realized_pnl,
                'remaining_quantity': remaining_quantity,
                'sale_proceeds': sale_proceeds
            }
        except Exception as e:
            db.session.rollback()
            print(f"Error selling asset: {e}")
            return {
                'success': False,
                'message': f'Error processing sale: {str(e)}',
                'realized_pnl': 0
            }

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
    def get_transaction_history(portfolio_id, symbol=None, limit=None):
        """Get transaction history for portfolio or specific symbol
        
        Args:
            portfolio_id: ID of the portfolio
            symbol: Optional symbol to filter by
            limit: Optional limit on number of transactions
        
        Returns:
            List of Transaction objects
        """
        query = Transaction.query.filter_by(portfolio_id=portfolio_id)
        
        if symbol:
            query = query.filter_by(symbol=symbol)
        
        query = query.order_by(Transaction.transaction_date.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    @staticmethod
    def get_realized_pnl_summary(portfolio_id):
        """Get summary of realized P&L by symbol
        
        Returns:
            dict with total realized P&L and breakdown by symbol
        """
        transactions = Transaction.query.filter_by(
            portfolio_id=portfolio_id,
            transaction_type='SELL'
        ).all()
        
        total_realized_pnl = 0
        by_symbol = {}
        
        for txn in transactions:
            if txn.realized_pnl:
                total_realized_pnl += txn.realized_pnl
                
                if txn.symbol not in by_symbol:
                    by_symbol[txn.symbol] = {
                        'realized_pnl': 0,
                        'total_sold': 0,
                        'sale_proceeds': 0,
                        'transactions': 0
                    }
                
                by_symbol[txn.symbol]['realized_pnl'] += txn.realized_pnl
                by_symbol[txn.symbol]['total_sold'] += txn.quantity
                by_symbol[txn.symbol]['sale_proceeds'] += txn.total_amount
                by_symbol[txn.symbol]['transactions'] += 1
        
        return {
            'total_realized_pnl': total_realized_pnl,
            'by_symbol': by_symbol
        }

    @staticmethod
    def get_unrealized_pnl(portfolio_id):
        """Calculate unrealized P&L for current holdings"""
        from services.portfolio_service import get_portfolio_data
        
        portfolio, total_value, total_cost, total_pnl = get_portfolio_data()
        
        if not portfolio:
            return 0
        
        # Unrealized P&L is the current total P&L
        # (doesn't include realized P&L which was already locked in)
        return total_pnl
        
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

def get_live_prices_for_portfolio():
    """Get live prices for all portfolio assets - optimized for async loading"""
    import datetime
    from services.data_service import data_service
    
    portfolio = Portfolio.query.first()
    if not portfolio:
        return {'prices': {}, 'changes': {}, 'update_time': None}
    
    assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
    if not assets:
        return {'prices': {}, 'changes': {}, 'update_time': None}
    
    live_prices = {}
    price_changes = {}
    
    # Use batch fetching if possible
    symbols = [asset.symbol for asset in assets]
    cache_key = f"live_prices_{'-'.join(sorted(symbols))}"
    
    # Check cache first (5 minute expiry for live prices)
    if hasattr(data_service, '_data_cache') and cache_key in data_service._data_cache:
        cached_data, cached_time = data_service._data_cache[cache_key]
        if (datetime.datetime.now() - cached_time).seconds < 300:  # 5 minutes
            return cached_data
    
    try:
        # Fetch all prices in batch if possible
        for asset in assets:
            try:
                current_data = data_service.fetch_stock_data([asset.symbol], period="5d")
                if not current_data.empty and 'Close' in current_data.columns:
                    if hasattr(current_data['Close'], 'columns') and asset.symbol in current_data['Close'].columns:
                        prices = current_data['Close'][asset.symbol]
                    else:
                        prices = current_data['Close']
                    
                    current_price = float(prices.iloc[-1])
                    live_prices[asset.symbol] = current_price
                    
                    # Calculate price change percentage
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
        
        result = {
            'prices': live_prices,
            'changes': price_changes,
            'update_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Cache the result
        if hasattr(data_service, '_data_cache'):
            data_service._data_cache[cache_key] = (result, datetime.datetime.now())
        
        return result
        
    except Exception as e:
        print(f"Error getting live prices: {e}")
        return {'prices': {}, 'changes': {}, 'update_time': None, 'error': str(e)}

def calculate_correlation_matrix():
    """Calculate correlation matrix - optimized for async loading"""
    from services.data_service import data_service
    import datetime
    
    portfolio = Portfolio.query.first()
    if not portfolio:
        return None
    
    assets = PortfolioAsset.query.filter_by(portfolio_id=portfolio.id).all()
    symbols = [asset.symbol for asset in assets]
    
    if len(symbols) < 2:
        return None
    
    cache_key = f"correlation_{'-'.join(sorted(symbols))}"
    
    # Check cache (1 hour expiry for correlation matrix)
    if hasattr(data_service, '_data_cache') and cache_key in data_service._data_cache:
        cached_data, cached_time = data_service._data_cache[cache_key]
        if (datetime.datetime.now() - cached_time).seconds < 3600:  # 1 hour
            return cached_data
    
    try:
        # Fetch data for correlation calculation (use 1mo for faster loading)
        portfolio_data = data_service.fetch_stock_data(symbols, period="1mo")
        if not portfolio_data.empty and 'Close' in portfolio_data.columns:
            # Calculate returns for correlation
            if hasattr(portfolio_data['Close'], 'columns'):
                returns_data = portfolio_data['Close'].pct_change().dropna()
                correlation_matrix = returns_data.corr()
                # Convert to HTML table
                matrix_html = correlation_matrix.to_html(classes='table table-sm', float_format='%.2f')
                
                # Cache the result
                if hasattr(data_service, '_data_cache'):
                    data_service._data_cache[cache_key] = (matrix_html, datetime.datetime.now())
                
                return matrix_html
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"Error calculating correlation matrix: {e}")
        return None

def get_portfolio_data():
    """Get current portfolio from database with accurate P&L calculation - OPTIMIZED"""
    from sqlalchemy.orm import joinedload
    
    # Use eager loading to prevent N+1 queries
    portfolio = Portfolio.query.options(joinedload(Portfolio.assets)).first()
    if not portfolio:
        return None, 0, 0, 0  # assets, total_value, total_cost, total_pnl
    
    assets = portfolio.assets  # Already loaded via joinedload
    
    # Calculate total cost properly based on purchase_price * quantity
    total_cost = 0
    for asset in assets:
        if asset.purchase_price and asset.quantity:
            # Correct: cost = purchase_price × quantity
            total_cost += asset.purchase_price * asset.quantity
        elif asset.allocation:
            # Fallback: use allocation if no purchase data
            total_cost += asset.allocation
    
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
    
    # Calculate current value based on actual shares owned
    total_current_value = 0
    
    for asset in assets:
        if asset.symbol in live_prices and live_prices[asset.symbol] is not None:
            current_price = live_prices[asset.symbol]
            
            if asset.purchase_price and asset.quantity:
                # Correct calculation: current_price × quantity
                current_value = current_price * asset.quantity
                cost_basis = asset.purchase_price * asset.quantity
                total_current_value += current_value
                print(f"{asset.symbol}: {asset.quantity} shares @ ${current_price:.2f} = ${current_value:.2f} (cost: ${cost_basis:.2f})")
            else:
                # Fallback: use allocation if no purchase/quantity data
                total_current_value += asset.allocation if asset.allocation else 0
                print(f"{asset.symbol}: Using allocation ${asset.allocation:.2f} (no purchase data)")
        else:
            # No live price available, use cost basis
            if asset.purchase_price and asset.quantity:
                cost_basis = asset.purchase_price * asset.quantity
                total_current_value += cost_basis
                print(f"{asset.symbol}: No live price, using cost basis ${cost_basis:.2f}")
            else:
                total_current_value += asset.allocation if asset.allocation else 0
                print(f"{asset.symbol}: No live price or purchase data, using allocation ${asset.allocation:.2f}")
    
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

def calculate_portfolio_dashboard_data(force_refresh=False, lightweight=False):
    """Calculate comprehensive dashboard data for portfolio analysis
    
    Args:
        force_refresh: Force refresh of cached data
        lightweight: If True, use cached data when available and skip some calculations
    """
    from services.risk_calculator import ProfessionalRiskEngine
    import datetime
    
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
        
        # Create dashboard data object with attributes for template access
        class DashboardData:
            def __init__(self, total_value, total_cost, total_pnl, assets_list, lightweight=True, force_refresh=False):
                self.total_value = total_value
                self.total_cost = total_cost
                self.total_pnl = total_pnl
                self.pnl_percentage = (total_pnl / total_cost * 100) if total_cost > 0 else 0
                self.total_assets = len(assets_list)
                self.lightweight = lightweight
                
                # Initialize all required attributes with defaults first
                self.volatility = 0.0
                self.sharpe_ratio = 0.0
                self.var_95 = 0.0
                self.var_99 = 0.0
                self.es_95 = 0.0
                self.max_drawdown = 0.0
                self.beta = 1.0
                self.annual_return = 0.0
                self.sortino_ratio = 0.0
                self.calmar_ratio = 0.0
                self.daily_pnl = 0.0
                self.live_prices = {}
                self.price_changes = {}
                self.price_update_time = None
                self.is_prices_cached = True
                self.asset_class_breakdown = {}
                self.correlation_matrix = None
                self.skewness = 0.0
                
                # Calculate basic metrics
                self._calculate_asset_class_breakdown(assets_list)
                
                # Always calculate metrics, but use cache if available in lightweight mode
                if lightweight and not force_refresh:
                    # Try to load from cache first
                    if not self._load_cached_metrics():
                        # No cache available, calculate anyway
                        print("No cache available, calculating metrics...")
                        self._calculate_portfolio_metrics(assets_list)
                else:
                    # Always calculate in non-lightweight mode or force refresh
                    self._calculate_portfolio_metrics(assets_list)
                
                # Load live prices (needed for dashboard display)
                self._load_live_prices(assets_list)
            
            def _load_live_prices(self, assets_list):
                """Load live prices for dashboard display"""
                try:
                    price_data = get_live_prices_for_portfolio()
                    self.live_prices = price_data.get('prices', {})
                    self.price_changes = price_data.get('changes', {})
                    self.price_update_time = price_data.get('update_time')
                except Exception as e:
                    print(f"Error loading live prices: {e}")
                    self.live_prices = {}
                    self.price_changes = {}
                    self.price_update_time = None
            
            def _load_cached_metrics(self):
                """Load cached metrics from previous calculation"""
                cache_key = "dashboard_metrics_cache"
                if hasattr(data_service, '_data_cache') and cache_key in data_service._data_cache:
                    cached_metrics, cached_time = data_service._data_cache[cache_key]
                    # Use cache if less than 1 hour old
                    if (datetime.datetime.now() - cached_time).seconds < 3600:
                        for key, value in cached_metrics.items():
                            setattr(self, key, value)
                        self.is_prices_cached = True
                        return True
                return False
            
            def _calculate_portfolio_metrics(self, assets_list):
                """Calculate portfolio-level risk metrics"""
                try:
                    if not assets_list or len(assets_list) == 0:
                        return
                    
                    # Calculate weighted metrics from cached data when possible
                    total_weight = sum(asset.weight for asset in assets_list if asset.weight)
                    weighted_volatility = 0.0
                    
                    for asset in assets_list:
                        try:
                            # Use shorter period for faster loading (1mo instead of 3mo)
                            asset_data = data_service.fetch_stock_data([asset.symbol], period="1mo")
                            if not asset_data.empty and 'Close' in asset_data.columns:
                                if hasattr(asset_data['Close'], 'columns') and asset.symbol in asset_data['Close'].columns:
                                    prices = asset_data['Close'][asset.symbol]
                                else:
                                    prices = asset_data['Close']
                                
                                returns = prices.pct_change().dropna()
                                if len(returns) > 1:
                                    asset_volatility = returns.std() * (252 ** 0.5)
                                    weight = asset.weight if asset.weight else (1.0 / len(assets_list))
                                    weighted_volatility += asset_volatility * weight
                                    
                                    # Calculate metrics only for first asset to save time
                                    if self.volatility == 0.0:
                                        self.volatility = asset_volatility
                                        self.sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0.0
                                        self.var_95 = returns.quantile(0.05)
                                        self.var_99 = returns.quantile(0.01)
                                        
                                        var_95_threshold = returns.quantile(0.05)
                                        es_returns = returns[returns <= var_95_threshold]
                                        self.es_95 = es_returns.mean() if len(es_returns) > 0 else var_95_threshold
                                        
                                        self.annual_return = returns.mean() * 252
                                        
                                        cumulative_returns = (1 + returns).cumprod()
                                        running_max = cumulative_returns.expanding().max()
                                        drawdown = (cumulative_returns - running_max) / running_max
                                        self.max_drawdown = drawdown.min()
                                        
                                        downside_returns = returns[returns < 0]
                                        downside_std = downside_returns.std() if len(downside_returns) > 0 else returns.std()
                                        self.sortino_ratio = returns.mean() / downside_std * (252 ** 0.5) if downside_std > 0 else 0.0
                                        
                                        self.calmar_ratio = abs(self.annual_return / self.max_drawdown) if self.max_drawdown != 0 else 0.0
                                        self.skewness = returns.skew() if len(returns) > 2 else 0.0
                                        self.daily_pnl = returns.iloc[-1] if len(returns) > 0 else 0.0
                                        
                        except Exception as e:
                            print(f"Error calculating metrics for {asset.symbol}: {e}")
                            continue
                    
                    if weighted_volatility > 0:
                        self.volatility = weighted_volatility
                    
                    # Cache the calculated metrics
                    metrics_to_cache = {
                        'volatility': self.volatility,
                        'sharpe_ratio': self.sharpe_ratio,
                        'var_95': self.var_95,
                        'var_99': self.var_99,
                        'es_95': self.es_95,
                        'max_drawdown': self.max_drawdown,
                        'beta': self.beta,
                        'annual_return': self.annual_return,
                        'sortino_ratio': self.sortino_ratio,
                        'calmar_ratio': self.calmar_ratio,
                        'skewness': self.skewness,
                        'daily_pnl': self.daily_pnl
                    }
                    if hasattr(data_service, '_data_cache'):
                        data_service._data_cache["dashboard_metrics_cache"] = (metrics_to_cache, datetime.datetime.now())
                    
                except Exception as e:
                    print(f"Error in portfolio metrics calculation: {e}")
            
            def _calculate_asset_class_breakdown(self, assets_list):
                """Calculate breakdown by asset class"""
                try:
                    breakdown = {}
                    total_portfolio_allocation = 0.0
                    
                    for asset in assets_list:
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
                    
                    if total_portfolio_allocation > 0:
                        for asset_class in breakdown:
                            breakdown[asset_class]['total_allocation'] = (
                                breakdown[asset_class]['total_allocation'] / total_portfolio_allocation * 100
                            )
                    
                    self.asset_class_breakdown = breakdown
                except Exception as e:
                    print(f"Error calculating asset class breakdown: {e}")
                    self.asset_class_breakdown = {}
        
        return DashboardData(total_current_value, total_cost, total_pnl, assets, lightweight=lightweight, force_refresh=force_refresh)
        
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