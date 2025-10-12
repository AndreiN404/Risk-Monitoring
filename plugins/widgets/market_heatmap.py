"""
Market Heatmap Widget
Visualize market performance across sectors and securities with color-coded tiles
Real-time updates with WebSocket support
"""
from typing import Dict, List
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import WidgetPlugin


class MarketHeatmapWidget(WidgetPlugin):
    """
    Advanced market heatmap widget with hierarchical visualization
    - Sector-based grouping
    - Size by market cap
    - Color by performance
    - Interactive drill-down
    - Real-time updates
    """
    
    def get_name(self) -> str:
        return "Market Heatmap"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Interactive heatmap showing market performance by sector and security"
    
    def get_author(self) -> str:
        return "Terminal Team"
    
    def get_widget_id(self) -> str:
        return "market-heatmap"
    
    def get_widget_category(self) -> str:
        return "market"
    
    def get_icon(self) -> str:
        return "📊"
    
    def get_default_size(self) -> tuple:
        return (12, 8)  # Full width, substantial height
    
    def get_min_size(self) -> tuple:
        return (6, 4)
    
    def get_data(self, params: Dict) -> Dict:
        """
        Fetch market data for heatmap visualization
        
        Args:
            params: {
                'universe': 'sp500' | 'nasdaq100' | 'dow30' | 'custom',
                'metric': 'change' | 'volume' | 'volatility',
                'timeframe': '1d' | '1w' | '1m' | 'ytd'
            }
        """
        universe = params.get('universe', 'sp500')
        metric = params.get('metric', 'change')
        timeframe = params.get('timeframe', '1d')
        
        # In production, fetch real data from data provider
        # For now, return structured data format
        
        # Sample data structure (replace with real data)
        sectors = {
            'Technology': [
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'change': 2.5, 'market_cap': 2800000000000, 'volume': 50000000},
                {'symbol': 'MSFT', 'name': 'Microsoft', 'change': 1.8, 'market_cap': 2500000000000, 'volume': 25000000},
                {'symbol': 'NVDA', 'name': 'NVIDIA', 'change': 3.2, 'market_cap': 1200000000000, 'volume': 40000000},
            ],
            'Financials': [
                {'symbol': 'JPM', 'name': 'JP Morgan', 'change': -0.5, 'market_cap': 450000000000, 'volume': 12000000},
                {'symbol': 'BAC', 'name': 'Bank of America', 'change': -0.8, 'market_cap': 300000000000, 'volume': 35000000},
            ],
            'Healthcare': [
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'change': 0.3, 'market_cap': 400000000000, 'volume': 8000000},
                {'symbol': 'UNH', 'name': 'UnitedHealth', 'change': 1.1, 'market_cap': 500000000000, 'volume': 3000000},
            ],
            'Energy': [
                {'symbol': 'XOM', 'name': 'Exxon Mobil', 'change': -1.2, 'market_cap': 350000000000, 'volume': 20000000},
                {'symbol': 'CVX', 'name': 'Chevron', 'change': -0.9, 'market_cap': 280000000000, 'volume': 8000000},
            ]
        }
        
        return {
            'sectors': sectors,
            'universe': universe,
            'metric': metric,
            'timeframe': timeframe,
            'last_update': 'Real-time',
            'total_securities': sum(len(stocks) for stocks in sectors.values())
        }
    
    def render(self, context: Dict) -> str:
        """
        Render heatmap visualization using HTML/CSS/JS
        Uses Treemap layout for hierarchical data
        """
        data = context.get('data', {})
        settings = context.get('settings', {})
        
        sectors = data.get('sectors', {})
        metric = data.get('metric', 'change')
        
        # Generate heatmap HTML
        html = f"""
        <div class="market-heatmap-widget h-full bg-base-100 rounded-lg shadow-lg p-4">
            <!-- Header -->
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                    <span class="text-2xl">{self.get_icon()}</span>
                    <div>
                        <h3 class="text-lg font-bold">{self.get_name()}</h3>
                        <p class="text-xs opacity-70">{data.get('universe', 'S&P 500').upper()} • {data.get('timeframe', '1D').upper()}</p>
                    </div>
                </div>
                <div class="flex gap-2">
                    <button class="btn btn-xs btn-ghost" onclick="refreshHeatmap('{self.get_widget_id()}')">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </button>
                </div>
            </div>
            
            <!-- Legend -->
            <div class="flex items-center gap-4 mb-3 text-xs">
                <div class="flex items-center gap-1">
                    <div class="w-4 h-4 bg-error"></div>
                    <span>-2%+</span>
                </div>
                <div class="flex items-center gap-1">
                    <div class="w-4 h-4 bg-warning"></div>
                    <span>-1%</span>
                </div>
                <div class="flex items-center gap-1">
                    <div class="w-4 h-4 bg-base-300"></div>
                    <span>0%</span>
                </div>
                <div class="flex items-center gap-1">
                    <div class="w-4 h-4 bg-success opacity-50"></div>
                    <span>+1%</span>
                </div>
                <div class="flex items-center gap-1">
                    <div class="w-4 h-4 bg-success"></div>
                    <span>+2%+</span>
                </div>
            </div>
            
            <!-- Heatmap Grid -->
            <div class="heatmap-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 2px; height: calc(100% - 120px);">
        """
        
        # Generate tiles for each sector and stock
        for sector, stocks in sectors.items():
            for stock in stocks:
                change = stock.get('change', 0)
                
                # Determine color based on change
                if change <= -2:
                    color_class = 'bg-error'
                elif change <= -0.5:
                    color_class = 'bg-warning'
                elif change < 0.5:
                    color_class = 'bg-base-300'
                elif change < 2:
                    color_class = 'bg-success opacity-50'
                else:
                    color_class = 'bg-success'
                
                # Arrow indicator
                arrow = '▲' if change > 0 else '▼' if change < 0 else '─'
                
                html += f"""
                <div class="heatmap-tile {color_class} rounded p-2 flex flex-col justify-between cursor-pointer hover:opacity-80 transition-opacity"
                     onclick="openStock('{stock['symbol']}')"
                     title="{stock['name']} • {sector}">
                    <div class="text-xs font-bold opacity-90">{stock['symbol']}</div>
                    <div class="text-lg font-bold">{change:+.1f}%</div>
                    <div class="text-xs opacity-70">{arrow} ${stock.get('market_cap', 0) / 1e9:.0f}B</div>
                </div>
                """
        
        html += """
            </div>
            
            <!-- Footer Stats -->
            <div class="mt-3 flex justify-between text-xs opacity-70">
                <span>{} securities</span>
                <span>Last update: {}</span>
            </div>
        </div>
        
        <script>
        function refreshHeatmap(widgetId) {{
            // Implement refresh logic
            console.log('Refreshing heatmap:', widgetId);
            location.reload();
        }}
        
        function openStock(symbol) {{
            // Open stock detail view
            window.location.href = `/analysis?symbol=${{symbol}}`;
        }}
        </script>
        
        <style>
        .heatmap-tile {{
            min-height: 80px;
            transition: all 0.2s ease;
        }}
        .heatmap-tile:hover {{
            transform: scale(1.05);
            z-index: 10;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        </style>
        """.format(
            data.get('total_securities', 0),
            data.get('last_update', 'Unknown')
        )
        
        return html
    
    def get_settings_schema(self) -> Dict:
        """Define widget settings"""
        return {
            'type': 'object',
            'properties': {
                'universe': {
                    'type': 'string',
                    'title': 'Market Universe',
                    'enum': ['sp500', 'nasdaq100', 'dow30', 'russell2000', 'custom'],
                    'default': 'sp500',
                    'description': 'Which market index to visualize'
                },
                'metric': {
                    'type': 'string',
                    'title': 'Display Metric',
                    'enum': ['change', 'volume', 'volatility', 'momentum'],
                    'default': 'change',
                    'description': 'What metric to color-code'
                },
                'timeframe': {
                    'type': 'string',
                    'title': 'Timeframe',
                    'enum': ['1d', '1w', '1m', '3m', 'ytd', '1y'],
                    'default': '1d',
                    'description': 'Performance period'
                },
                'group_by': {
                    'type': 'string',
                    'title': 'Group By',
                    'enum': ['sector', 'industry', 'market_cap', 'none'],
                    'default': 'sector',
                    'description': 'How to organize tiles'
                },
                'tile_size': {
                    'type': 'string',
                    'title': 'Tile Size Metric',
                    'enum': ['market_cap', 'volume', 'equal'],
                    'default': 'market_cap',
                    'description': 'What determines tile size'
                },
                'refresh_interval': {
                    'type': 'integer',
                    'title': 'Auto-refresh (seconds)',
                    'default': 60,
                    'minimum': 10,
                    'maximum': 3600
                },
                'show_labels': {
                    'type': 'boolean',
                    'title': 'Show Symbol Labels',
                    'default': True
                },
                'animate_changes': {
                    'type': 'boolean',
                    'title': 'Animate Color Changes',
                    'default': True
                }
            }
        }
