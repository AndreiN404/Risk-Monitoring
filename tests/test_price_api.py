"""
Quick test script to check stock price API
"""
from app import create_app
import os

# Create app
app = create_app(os.getenv('FLASK_CONFIG', 'default'))

with app.app_context():
    # Test the plugin manager
    pm = app.plugin_manager
    print(f"\n=== Plugin Manager ===")
    print(f"Plugin Manager: {pm}")
    print(f"Type: {type(pm)}")
    
    # Try to get yfinance plugin
    print(f"\n=== Looking for yfinance_provider ===")
    data_plugin = pm.get_enabled_plugin('data_providers', 'yfinance_provider')
    print(f"Data Plugin: {data_plugin}")
    
    if data_plugin:
        print(f"\n=== Testing quote fetch ===")
        print(f"Plugin Name: {data_plugin.get_name()}")
        print(f"Plugin Version: {data_plugin.get_version()}")
        
        # Test fetching a quote
        quote = data_plugin.get_quote('AAPL')
        print(f"Quote for AAPL: {quote}")
    else:
        print("ERROR: No data plugin available!")
        print("\n=== Available Plugins ===")
        for category in pm.plugins:
            print(f"\nCategory: {category}")
            for plugin_id, plugin in pm.plugins[category].items():
                print(f"  - {plugin_id}: {plugin}")
