from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from models import db, Portfolio, PortfolioAsset
from services.portfolio_service import portfolio_service, get_portfolio_data

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio')
def portfolio_manager():
    """Portfolio management page"""
    portfolio, total_current_value, total_cost, total_pnl = get_portfolio_data()
    return render_template('portfolio.html', 
                         portfolio=portfolio, 
                         total_value=total_current_value,
                         total_cost=total_cost,
                         total_pnl=total_pnl)

@portfolio_bp.route('/add_asset', methods=['POST'])
def add_asset():
    """Add asset to portfolio"""
    symbol = request.form.get('symbol', '').upper().strip()
    asset_class = request.form.get('asset_class')
    allocation_str = request.form.get('allocation', '0')
    purchase_price = request.form.get('purchase_price')
    quantity = request.form.get('quantity')
    purchase_date = request.form.get('purchase_date')
    
    if not symbol or not asset_class:
        flash('Please provide symbol and asset class.', 'error')
        return redirect(url_for('portfolio.portfolio_manager'))
    
    # Convert optional fields
    purchase_price_val = None
    quantity_val = None
    purchase_date_val = None
    allocation = 0
    
    if purchase_price and purchase_price.strip():
        try:
            purchase_price_val = float(purchase_price)
        except ValueError:
            flash('Invalid purchase price.', 'error')
            return redirect(url_for('portfolio.portfolio_manager'))
    
    if quantity and quantity.strip():
        try:
            quantity_val = float(quantity)
        except ValueError:
            flash('Invalid quantity.', 'error')
            return redirect(url_for('portfolio.portfolio_manager'))
    
    if purchase_date and purchase_date.strip():
        try:
            purchase_date_val = datetime.strptime(purchase_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Calculate allocation based on what's provided
    if purchase_price_val and quantity_val:
        # Best case: we have both price and quantity
        allocation = purchase_price_val * quantity_val
        print(f"Calculated allocation: ${purchase_price_val} × {quantity_val} = ${allocation}")
    elif allocation_str and allocation_str.strip():
        # User provided allocation manually (fallback mode)
        try:
            allocation = float(allocation_str)
            if allocation <= 0:
                flash('Allocation must be greater than 0.', 'error')
                return redirect(url_for('portfolio.portfolio_manager'))
            
            # If we have price but no quantity, calculate quantity
            if purchase_price_val and not quantity_val:
                quantity_val = allocation / purchase_price_val
                print(f"Calculated quantity: ${allocation} ÷ ${purchase_price_val} = {quantity_val} shares")
            # If we have quantity but no price, calculate price
            elif quantity_val and not purchase_price_val:
                purchase_price_val = allocation / quantity_val
                print(f"Calculated purchase price: ${allocation} ÷ {quantity_val} = ${purchase_price_val} per share")
        except ValueError:
            flash('Invalid allocation amount.', 'error')
            return redirect(url_for('portfolio.portfolio_manager'))
    else:
        flash('Please provide either (purchase price AND quantity) OR allocation amount.', 'error')
        return redirect(url_for('portfolio.portfolio_manager'))
    
    # Get or create portfolio
    portfolio = portfolio_service.get_or_create_default_portfolio()
    
    # Check if asset already exists
    existing_asset = PortfolioAsset.query.filter_by(
        portfolio_id=portfolio.id, 
        symbol=symbol
    ).first()
    
    if existing_asset:
        flash(f'{symbol} is already in your portfolio. Remove it first to update.', 'error')
        return redirect(url_for('portfolio.portfolio_manager'))
    
    # Add new asset using portfolio service
    success = portfolio_service.add_asset_to_portfolio(
        portfolio.id,
        symbol,
        asset_class,
        allocation,
        purchase_price_val,
        quantity_val,
        purchase_date_val
    )
    
    if success:
        flash(f'{symbol} added to portfolio successfully! (${allocation:.2f})', 'success')
    else:
        flash(f'Error adding {symbol} to portfolio.', 'error')
    
    return redirect(url_for('portfolio.portfolio_manager'))

@portfolio_bp.route('/remove_asset', methods=['POST'])
def remove_asset():
    """Remove asset from portfolio"""
    symbol = request.form.get('symbol')
    
    asset = PortfolioAsset.query.filter_by(symbol=symbol).first()
    if asset:
        success = portfolio_service.remove_asset_from_portfolio(asset.portfolio_id, symbol)
        if success:
            flash(f'{symbol} removed from portfolio.', 'success')
        else:
            flash(f'Error removing {symbol} from portfolio.', 'error')
    else:
        flash('Asset not found.', 'error')
    
    return redirect(url_for('portfolio.portfolio_manager'))

@portfolio_bp.route('/load_preset', methods=['POST'])
def load_preset():
    """Load preset portfolio allocations"""
    preset = request.form.get('preset')
    
    # Define preset portfolios
    presets = {
        'conservative': {
            'BND': 40,   # Bonds ETF
            'VTI': 40,   # Total Stock Market ETF
            'VEA': 20    # International Developed Markets ETF
        },
        'balanced': {
            'VTI': 50,   # Total Stock Market ETF
            'VEA': 25,   # International Developed Markets ETF
            'BND': 25    # Bonds ETF
        },
        'aggressive': {
            'VTI': 60,   # Total Stock Market ETF
            'VEA': 30,   # International Developed Markets ETF
            'VWO': 10    # Emerging Markets ETF
        },
        'tech_focus': {
            'QQQ': 40,   # NASDAQ 100 ETF
            'VTI': 30,   # Total Stock Market ETF
            'SCHG': 30   # Large Cap Growth ETF
        }
    }
    
    if preset not in presets:
        flash('Invalid preset selected.', 'error')
        return redirect(url_for('portfolio.portfolio_manager'))
    
    # Clear existing portfolio
    portfolio = portfolio_service.get_or_create_default_portfolio()
    existing_assets = portfolio_service.get_portfolio_assets(portfolio.id)
    
    for asset in existing_assets:
        portfolio_service.remove_asset_from_portfolio(portfolio.id, asset.symbol)
    
    # Add preset assets
    preset_data = presets[preset]
    for symbol, allocation in preset_data.items():
        portfolio_service.add_asset_to_portfolio(
            portfolio.id,
            symbol,
            'ETF',  # Default to ETF for presets
            allocation
        )
    
    flash(f'{preset.title()} portfolio loaded successfully!', 'success')
    return redirect(url_for('portfolio.portfolio_manager'))

@portfolio_bp.route('/rebalance_portfolio', methods=['POST'])
def rebalance_portfolio():
    """Rebalance portfolio to target allocations"""
    portfolio = portfolio_service.get_or_create_default_portfolio()
    
    # Get target allocations from form
    target_allocations = {}
    for key, value in request.form.items():
        if key.startswith('allocation_'):
            symbol = key.replace('allocation_', '')
            try:
                target_allocations[symbol] = float(value)
            except ValueError:
                flash(f'Invalid allocation for {symbol}', 'error')
                return redirect(url_for('portfolio.portfolio_manager'))
    
    # Rebalance using portfolio service
    success = portfolio_service.rebalance_portfolio(portfolio.id, target_allocations)
    
    if success:
        flash('Portfolio rebalanced successfully!', 'success')
    else:
        flash('Error rebalancing portfolio.', 'error')
    
    return redirect(url_for('portfolio.portfolio_manager'))