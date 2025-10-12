"""
Dark Mode Professional Theme
Bloomberg Terminal inspired color scheme with high contrast
Optimized for extended trading sessions
"""
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import ThemePlugin


class BloombergDarkTheme(ThemePlugin):
    """
    Professional dark theme inspired by Bloomberg Terminal
    - High contrast for readability
    - Reduced eye strain for long sessions
    - Orange accents for critical data
    - Optimized for financial data visualization
    """
    
    def get_name(self) -> str:
        return "Bloomberg Dark"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Professional dark theme inspired by Bloomberg Terminal with orange accents"
    
    def get_author(self) -> str:
        return "Terminal Team"
    
    def get_theme_id(self) -> str:
        return "bloomberg-dark"
    
    def get_colors(self) -> Dict:
        """
        Bloomberg-inspired color palette
        Focus on black background with orange highlights
        """
        return {
            # Primary colors
            'primary': '#FF8C00',      # Bloomberg Orange
            'secondary': '#1E1E1E',    # Dark Gray
            'accent': '#00A0DC',       # Bloomberg Blue
            
            # Background colors
            'background': '#000000',    # Pure Black
            'surface': '#0D0D0D',      # Slightly lighter black
            'card': '#1A1A1A',         # Card background
            
            # Text colors
            'text': '#FFFFFF',          # White text
            'text-muted': '#B0B0B0',   # Muted gray text
            'text-disabled': '#666666', # Disabled text
            
            # Semantic colors
            'success': '#00FF00',       # Bright green (gains)
            'warning': '#FFA500',       # Orange (caution)
            'error': '#FF0000',         # Bright red (losses)
            'info': '#00A0DC',         # Blue (information)
            
            # Border colors
            'border': '#333333',        # Subtle borders
            'border-focus': '#FF8C00',  # Orange focused borders
            
            # Interactive states
            'hover': '#2A2A2A',        # Hover background
            'active': '#3A3A3A',       # Active state
            'selected': '#FF8C00',     # Selected items
            
            # Chart specific
            'grid': '#1A1A1A',         # Chart grid lines
            'axis': '#666666',         # Chart axis
        }
    
    def get_fonts(self) -> Dict:
        """
        Typography optimized for financial data
        Monospace for numbers, sans-serif for text
        """
        return {
            'family': '"Roboto Mono", "IBM Plex Mono", "Consolas", monospace',
            'family-text': '"Inter", "Segoe UI", "Arial", sans-serif',
            'size': '14px',
            'size-small': '12px',
            'size-large': '16px',
            'size-heading': '24px',
            'weights': {
                'normal': 400,
                'medium': 500,
                'bold': 700
            },
            'line-height': '1.6'
        }
    
    def get_chart_colors(self) -> Dict:
        """
        Chart-specific colors for candlesticks and indicators
        """
        return {
            # Candlestick colors
            'up_candle': '#00FF00',      # Bright green
            'down_candle': '#FF0000',    # Bright red
            'up_candle_body': '#00AA00', # Solid green
            'down_candle_body': '#AA0000', # Solid red
            
            # Chart types
            'line': '#00A0DC',           # Blue line
            'area': '#00A0DC40',         # Transparent blue area
            'volume': '#FF8C0080',       # Transparent orange
            'volume_up': '#00FF0080',    # Transparent green
            'volume_down': '#FF000080',  # Transparent red
            
            # Moving averages
            'ma_fast': '#FFFF00',        # Yellow (fast MA)
            'ma_medium': '#00FFFF',      # Cyan (medium MA)
            'ma_slow': '#FF00FF',        # Magenta (slow MA)
            
            # Indicators
            'rsi': '#9333ea',            # Purple
            'macd': '#f59e0b',           # Amber
            'macd_signal': '#ef4444',    # Red
            'macd_histogram': '#3b82f6', # Blue
            'bollinger_upper': '#f97316', # Orange
            'bollinger_lower': '#f97316', # Orange
            'bollinger_middle': '#fbbf24', # Amber
            
            # Grid and axes
            'grid_lines': '#1A1A1A',
            'axis_text': '#666666',
            'crosshair': '#FF8C00'
        }
    
    def generate_css(self) -> str:
        """
        Generate complete CSS for the theme
        Includes all color variables, typography, and component styles
        """
        colors = self.get_colors()
        fonts = self.get_fonts()
        chart = self.get_chart_colors()
        
        css = f"""
        /* Bloomberg Dark Theme - Professional Financial Terminal */
        
        :root {{
            /* === Primary Colors === */
            --color-primary: {colors['primary']};
            --color-secondary: {colors['secondary']};
            --color-accent: {colors['accent']};
            
            /* === Background Colors === */
            --color-background: {colors['background']};
            --color-surface: {colors['surface']};
            --color-card: {colors['card']};
            
            /* === Text Colors === */
            --color-text: {colors['text']};
            --color-text-muted: {colors['text-muted']};
            --color-text-disabled: {colors['text-disabled']};
            
            /* === Semantic Colors === */
            --color-success: {colors['success']};
            --color-warning: {colors['warning']};
            --color-error: {colors['error']};
            --color-info: {colors['info']};
            
            /* === Border Colors === */
            --color-border: {colors['border']};
            --color-border-focus: {colors['border-focus']};
            
            /* === Interactive States === */
            --color-hover: {colors['hover']};
            --color-active: {colors['active']};
            --color-selected: {colors['selected']};
            
            /* === Chart Colors === */
            --chart-up: {chart['up_candle']};
            --chart-down: {chart['down_candle']};
            --chart-grid: {chart['grid_lines']};
            --chart-axis: {chart['axis_text']};
            --chart-crosshair: {chart['crosshair']};
            
            /* === Typography === */
            --font-family: {fonts['family']};
            --font-family-text: {fonts['family-text']};
            --font-size: {fonts['size']};
            --font-size-small: {fonts['size-small']};
            --font-size-large: {fonts['size-large']};
            --font-size-heading: {fonts['size-heading']};
            --font-weight-normal: {fonts['weights']['normal']};
            --font-weight-medium: {fonts['weights']['medium']};
            --font-weight-bold: {fonts['weights']['bold']};
            --line-height: {fonts['line-height']};
            
            /* === Spacing === */
            --spacing-xs: 4px;
            --spacing-sm: 8px;
            --spacing-md: 16px;
            --spacing-lg: 24px;
            --spacing-xl: 32px;
            
            /* === Border Radius === */
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 12px;
            
            /* === Shadows === */
            --shadow-sm: 0 1px 3px rgba(255, 140, 0, 0.1);
            --shadow-md: 0 4px 6px rgba(255, 140, 0, 0.15);
            --shadow-lg: 0 10px 25px rgba(255, 140, 0, 0.2);
            
            /* === Transitions === */
            --transition-fast: 150ms ease;
            --transition-normal: 300ms ease;
            --transition-slow: 500ms ease;
        }}
        
        /* === Base Styles === */
        body {{
            background-color: var(--color-background);
            color: var(--color-text);
            font-family: var(--font-family-text);
            font-size: var(--font-size);
            line-height: var(--line-height);
        }}
        
        /* === Typography === */
        h1, h2, h3, h4, h5, h6 {{
            font-family: var(--font-family-text);
            font-weight: var(--font-weight-bold);
            color: var(--color-text);
            margin: 0;
        }}
        
        h1 {{ font-size: var(--font-size-heading); }}
        h2 {{ font-size: calc(var(--font-size-heading) * 0.85); }}
        h3 {{ font-size: var(--font-size-large); }}
        
        /* === Numbers and Data === */
        .number, .price, .value {{
            font-family: var(--font-family);
            font-weight: var(--font-weight-medium);
            letter-spacing: 0.5px;
        }}
        
        /* === Cards and Panels === */
        .card, .panel {{
            background-color: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            padding: var(--spacing-md);
            transition: border-color var(--transition-fast);
        }}
        
        .card:hover {{
            border-color: var(--color-primary);
        }}
        
        /* === Buttons === */
        .btn-primary {{
            background-color: var(--color-primary);
            color: var(--color-background);
            border: none;
            padding: var(--spacing-sm) var(--spacing-md);
            border-radius: var(--radius-sm);
            font-weight: var(--font-weight-medium);
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        
        .btn-primary:hover {{
            background-color: #FFA500;
            box-shadow: var(--shadow-md);
        }}
        
        /* === Tables === */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: var(--font-family);
        }}
        
        th {{
            background-color: var(--color-surface);
            color: var(--color-primary);
            font-weight: var(--font-weight-bold);
            text-align: left;
            padding: var(--spacing-sm);
            border-bottom: 2px solid var(--color-border);
        }}
        
        td {{
            padding: var(--spacing-sm);
            border-bottom: 1px solid var(--color-border);
        }}
        
        tr:hover {{
            background-color: var(--color-hover);
        }}
        
        /* === Price Movement === */
        .text-success, .positive {{
            color: var(--color-success) !important;
        }}
        
        .text-error, .negative {{
            color: var(--color-error) !important;
        }}
        
        /* === Inputs === */
        input, select, textarea {{
            background-color: var(--color-surface);
            color: var(--color-text);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-sm);
            padding: var(--spacing-sm);
            font-family: var(--font-family-text);
            transition: border-color var(--transition-fast);
        }}
        
        input:focus, select:focus, textarea:focus {{
            outline: none;
            border-color: var(--color-border-focus);
            box-shadow: 0 0 0 3px rgba(255, 140, 0, 0.1);
        }}
        
        /* === Scrollbars === */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--color-surface);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--color-border);
            border-radius: var(--radius-sm);
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--color-primary);
        }}
        
        /* === Charts === */
        .chart-container {{
            background-color: var(--color-background);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
        }}
        
        /* === Alerts === */
        .alert {{
            padding: var(--spacing-md);
            border-radius: var(--radius-sm);
            border-left: 4px solid;
        }}
        
        .alert-info {{
            background-color: rgba(0, 160, 220, 0.1);
            border-left-color: var(--color-info);
        }}
        
        .alert-success {{
            background-color: rgba(0, 255, 0, 0.1);
            border-left-color: var(--color-success);
        }}
        
        .alert-warning {{
            background-color: rgba(255, 165, 0, 0.1);
            border-left-color: var(--color-warning);
        }}
        
        .alert-error {{
            background-color: rgba(255, 0, 0, 0.1);
            border-left-color: var(--color-error);
        }}
        
        /* === Animations === */
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .pulse {{
            animation: pulse 2s ease-in-out infinite;
        }}
        
        @keyframes slideIn {{
            from {{
                transform: translateX(-20px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        .slide-in {{
            animation: slideIn var(--transition-normal) ease-out;
        }}
        """
        
        return css
    
    def get_settings_schema(self) -> Dict:
        """Theme customization settings"""
        return {
            'type': 'object',
            'properties': {
                'accent_color': {
                    'type': 'string',
                    'title': 'Accent Color',
                    'default': '#FF8C00',
                    'description': 'Primary accent color (Bloomberg Orange)'
                },
                'font_size': {
                    'type': 'string',
                    'title': 'Base Font Size',
                    'enum': ['12px', '14px', '16px', '18px'],
                    'default': '14px',
                    'description': 'Base font size for all text'
                },
                'enable_animations': {
                    'type': 'boolean',
                    'title': 'Enable Animations',
                    'default': True,
                    'description': 'Enable smooth transitions and animations'
                },
                'high_contrast': {
                    'type': 'boolean',
                    'title': 'High Contrast Mode',
                    'default': False,
                    'description': 'Increase contrast for better visibility'
                },
                'show_grid_lines': {
                    'type': 'boolean',
                    'title': 'Show Chart Grid',
                    'default': True,
                    'description': 'Display grid lines on charts'
                }
            }
        }
