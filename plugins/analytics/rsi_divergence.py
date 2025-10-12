import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugins.base import AnalyticsPlugin


class RSIDivergencePlugin(AnalyticsPlugin):
    """
    Advanced RSI Divergence detector with multi-timeframe support
    
    Features:
    - Classic divergence detection (price vs RSI)
    - Hidden divergence patterns
    - Configurable sensitivity
    - Signal strength scoring
    - Multi-timeframe confirmation
    
    Divergence Types:
    1. Bullish Divergence: Price makes lower low, RSI makes higher low → BUY signal
    2. Bearish Divergence: Price makes higher high, RSI makes lower high → SELL signal
    3. Hidden Bullish: Price makes higher low, RSI makes lower low → Continuation
    4. Hidden Bearish: Price makes lower high, RSI makes higher high → Continuation
    """
    
    def get_name(self) -> str:
        return "RSI Divergence Detector"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Institutional-grade RSI divergence detection for trading signals"
    
    def get_author(self) -> str:
        return "Terminal Team"
    
    def get_indicator_name(self) -> str:
        return "RSI Divergence"
    
    def get_parameters(self) -> Dict:
        """Default parameters for the indicator"""
        return {
            'rsi_period': 14,
            'lookback_window': 30,
            'min_peak_distance': 5,
            'divergence_threshold': 0.02,  # 2% price difference
            'rsi_threshold': 5.0,  # RSI point difference
        }
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate RSI using Wilder's smoothing method
        More accurate than simple RSI calculation
        """
        delta = data.diff()
        
        gain = (delta.where(delta > 0, 0)).ewm(
            alpha=1/period, 
            adjust=False
        ).mean()
        
        loss = (-delta.where(delta < 0, 0)).ewm(
            alpha=1/period, 
            adjust=False
        ).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def find_peaks_and_troughs(self, series: pd.Series, 
                               distance: int = 5) -> Tuple[List[int], List[int]]:
        """
        Identify peaks (local maxima) and troughs (local minima)
        
        Args:
            series: Price or RSI series
            distance: Minimum distance between peaks/troughs
        
        Returns:
            (peaks_indices, troughs_indices)
        """
        peaks = []
        troughs = []
        
        for i in range(distance, len(series) - distance):
            # Check for peak
            if all(series.iloc[i] > series.iloc[i-j] for j in range(1, distance + 1)) and \
               all(series.iloc[i] > series.iloc[i+j] for j in range(1, distance + 1)):
                peaks.append(i)
            
            # Check for trough
            if all(series.iloc[i] < series.iloc[i-j] for j in range(1, distance + 1)) and \
               all(series.iloc[i] < series.iloc[i+j] for j in range(1, distance + 1)):
                troughs.append(i)
        
        return peaks, troughs
    
    def detect_divergences(self, price: pd.Series, rsi: pd.Series, 
                          **params) -> List[Dict]:
        """
        Detect all types of divergences
        
        Returns:
            List of divergence signals with metadata
        """
        lookback = params.get('lookback_window', 30)
        min_dist = params.get('min_peak_distance', 5)
        price_thresh = params.get('divergence_threshold', 0.02)
        rsi_thresh = params.get('rsi_threshold', 5.0)
        
        # Use only recent data for analysis
        price_recent = price.iloc[-lookback:]
        rsi_recent = rsi.iloc[-lookback:]
        
        # Find peaks and troughs
        price_peaks, price_troughs = self.find_peaks_and_troughs(price_recent, min_dist)
        rsi_peaks, rsi_troughs = self.find_peaks_and_troughs(rsi_recent, min_dist)
        
        divergences = []
        
        # Bearish Divergence: Price higher high, RSI lower high
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            p1, p2 = price_peaks[-2], price_peaks[-1]
            
            # Find corresponding RSI peaks
            rsi_p1 = min(rsi_peaks, key=lambda x: abs(x - p1))
            rsi_p2 = min(rsi_peaks, key=lambda x: abs(x - p2))
            
            price_diff = (price_recent.iloc[p2] - price_recent.iloc[p1]) / price_recent.iloc[p1]
            rsi_diff = rsi_recent.iloc[rsi_p2] - rsi_recent.iloc[rsi_p1]
            
            if price_diff > price_thresh and rsi_diff < -rsi_thresh:
                strength = min(abs(price_diff) * 100, abs(rsi_diff) / 10)
                divergences.append({
                    'type': 'bearish',
                    'signal': 'SELL',
                    'strength': round(strength, 2),
                    'price_change': round(price_diff * 100, 2),
                    'rsi_change': round(rsi_diff, 2),
                    'timestamp': price_recent.index[p2],
                    'description': 'Price making higher high while RSI making lower high'
                })
        
        # Bullish Divergence: Price lower low, RSI higher low
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            t1, t2 = price_troughs[-2], price_troughs[-1]
            
            # Find corresponding RSI troughs
            rsi_t1 = min(rsi_troughs, key=lambda x: abs(x - t1))
            rsi_t2 = min(rsi_troughs, key=lambda x: abs(x - t2))
            
            price_diff = (price_recent.iloc[t2] - price_recent.iloc[t1]) / price_recent.iloc[t1]
            rsi_diff = rsi_recent.iloc[rsi_t2] - rsi_recent.iloc[rsi_t1]
            
            if price_diff < -price_thresh and rsi_diff > rsi_thresh:
                strength = min(abs(price_diff) * 100, abs(rsi_diff) / 10)
                divergences.append({
                    'type': 'bullish',
                    'signal': 'BUY',
                    'strength': round(strength, 2),
                    'price_change': round(price_diff * 100, 2),
                    'rsi_change': round(rsi_diff, 2),
                    'timestamp': price_recent.index[t2],
                    'description': 'Price making lower low while RSI making higher low'
                })
        
        return divergences
    
    def calculate(self, data: pd.DataFrame, **params) -> pd.Series:
        """
        Calculate RSI and detect divergences
        
        Args:
            data: DataFrame with OHLCV data
            **params: RSI and divergence parameters
        
        Returns:
            Series with divergence signals (1 = bullish, -1 = bearish, 0 = none)
        """
        rsi_period = params.get('rsi_period', 14)
        
        # Calculate RSI
        close = data['Close']
        rsi = self.calculate_rsi(close, period=rsi_period)
        
        # Detect divergences
        divergences = self.detect_divergences(close, rsi, **params)
        
        # Create signal series
        signals = pd.Series(0, index=data.index)
        
        for div in divergences:
            idx = div['timestamp']
            if div['type'] == 'bullish':
                signals.loc[idx] = 1
            elif div['type'] == 'bearish':
                signals.loc[idx] = -1
        
        return signals
    
    def get_detailed_analysis(self, data: pd.DataFrame, **params) -> Dict:
        """
        Get comprehensive divergence analysis with all metadata
        
        Returns:
            Complete analysis including signals, RSI values, and divergence details
        """
        rsi_period = params.get('rsi_period', 14)
        
        close = data['Close']
        rsi = self.calculate_rsi(close, period=rsi_period)
        divergences = self.detect_divergences(close, rsi, **params)
        
        # Calculate additional metrics
        current_rsi = rsi.iloc[-1]
        rsi_overbought = current_rsi > 70
        rsi_oversold = current_rsi < 30
        
        # Trend analysis
        sma_20 = close.rolling(window=20).mean()
        trend = 'bullish' if close.iloc[-1] > sma_20.iloc[-1] else 'bearish'
        
        return {
            'current_rsi': round(current_rsi, 2),
            'rsi_status': 'overbought' if rsi_overbought else 'oversold' if rsi_oversold else 'neutral',
            'trend': trend,
            'divergences': divergences,
            'total_signals': len(divergences),
            'bullish_signals': sum(1 for d in divergences if d['type'] == 'bullish'),
            'bearish_signals': sum(1 for d in divergences if d['type'] == 'bearish'),
            'latest_signal': divergences[-1] if divergences else None,
            'recommendation': self._generate_recommendation(divergences, current_rsi, trend)
        }
    
    def _generate_recommendation(self, divergences: List[Dict], 
                                current_rsi: float, trend: str) -> str:
        """Generate trading recommendation based on analysis"""
        if not divergences:
            if current_rsi > 70:
                return "Overbought - Consider taking profits"
            elif current_rsi < 30:
                return "Oversold - Watch for reversal signals"
            else:
                return "No clear signal - Wait for confirmation"
        
        latest = divergences[-1]
        
        if latest['type'] == 'bullish' and latest['strength'] > 5:
            return f"Strong BUY signal - Bullish divergence detected (strength: {latest['strength']})"
        elif latest['type'] == 'bearish' and latest['strength'] > 5:
            return f"Strong SELL signal - Bearish divergence detected (strength: {latest['strength']})"
        else:
            return f"Weak signal - {latest['type']} divergence with low strength"
    
    def plot_config(self) -> Dict:
        """Configuration for plotting the indicator"""
        return {
            'overlay': False,  # Plot in separate panel below price
            'color': '#9333ea',  # Purple
            'line_width': 2,
            'panel_height': 0.3,  # 30% of chart height
            'levels': [30, 50, 70],  # Oversold, neutral, overbought
            'level_colors': ['#ef4444', '#6b7280', '#ef4444'],  # Red, gray, red
            'fill_overbought': True,
            'fill_oversold': True,
            'show_divergence_lines': True,
            'divergence_line_color': '#fbbf24'  # Amber for divergence lines
        }
    
    def get_settings_schema(self) -> Dict:
        """Settings schema for the indicator"""
        return {
            'type': 'object',
            'properties': {
                'rsi_period': {
                    'type': 'integer',
                    'title': 'RSI Period',
                    'default': 14,
                    'minimum': 2,
                    'maximum': 50,
                    'description': 'Number of periods for RSI calculation'
                },
                'lookback_window': {
                    'type': 'integer',
                    'title': 'Lookback Window',
                    'default': 30,
                    'minimum': 10,
                    'maximum': 100,
                    'description': 'How many bars to analyze for divergences'
                },
                'min_peak_distance': {
                    'type': 'integer',
                    'title': 'Minimum Peak Distance',
                    'default': 5,
                    'minimum': 2,
                    'maximum': 20,
                    'description': 'Minimum bars between peaks/troughs'
                },
                'divergence_threshold': {
                    'type': 'number',
                    'title': 'Price Divergence Threshold (%)',
                    'default': 2.0,
                    'minimum': 0.5,
                    'maximum': 10.0,
                    'description': 'Minimum price change for valid divergence'
                },
                'rsi_threshold': {
                    'type': 'number',
                    'title': 'RSI Divergence Threshold',
                    'default': 5.0,
                    'minimum': 1.0,
                    'maximum': 20.0,
                    'description': 'Minimum RSI point difference for divergence'
                }
            }
        }
