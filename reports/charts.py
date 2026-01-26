"""
Chart generation for economic indicators report
Uses Plotly for interactive charts
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any


class ChartGenerator:
    """Generate charts for the economic indicators report"""

    # Color scheme matching the original report
    COLORS = {
        'primary': '#2E7D32',      # Dark green
        'secondary': '#FFA000',     # Amber/orange
        'tertiary': '#1565C0',      # Blue
        'positive': '#4CAF50',      # Green
        'negative': '#F44336',      # Red
        'neutral': '#9E9E9E',       # Grey
        'background': '#FFFFFF',
        'grid': '#E0E0E0',
        'text': '#333333'
    }

    LAYOUT_DEFAULTS = {
        'font': {'family': 'Arial, sans-serif', 'size': 12, 'color': '#333333'},
        'plot_bgcolor': 'white',
        'paper_bgcolor': 'white',
        'margin': {'l': 60, 'r': 30, 't': 50, 'b': 60},
        'hovermode': 'x unified'
    }

    def __init__(self):
        pass

    def _apply_layout(self, fig: go.Figure, title: str = None,
                      height: int = 400) -> go.Figure:
        """Apply consistent styling to figures"""
        layout_updates = {
            **self.LAYOUT_DEFAULTS,
            'height': height,
        }

        if title:
            layout_updates['title'] = {
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': self.COLORS['text']}
            }

        fig.update_layout(**layout_updates)

        # Update axes
        fig.update_xaxes(
            showgrid=True,
            gridcolor=self.COLORS['grid'],
            showline=True,
            linecolor=self.COLORS['grid']
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor=self.COLORS['grid'],
            showline=True,
            linecolor=self.COLORS['grid']
        )

        return fig

    def create_live_register_chart(self, df: pd.DataFrame) -> go.Figure:
        """
        Create Live Register chart with unadjusted and seasonally adjusted lines

        Args:
            df: DataFrame with columns 'date', unadjusted and seasonally adjusted values
        """
        fig = go.Figure()

        # Find the right column names (they vary)
        unadj_col = None
        sadj_col = None

        for col in df.columns:
            if 'unadjust' in col.lower():
                unadj_col = col
            elif 'seasonal' in col.lower() or 'adjust' in col.lower():
                sadj_col = col

        # Fallback to default names if not found
        if unadj_col is None:
            unadj_col = 'Persons on the Live Register (Unadjusted)'
        if sadj_col is None:
            sadj_col = 'Persons on the Live Register (Seasonally Adjusted)'

        # Unadjusted line
        if unadj_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[unadj_col],
                mode='lines',
                name='Unadjusted',
                line={'color': self.COLORS['primary'], 'width': 2}
            ))

        # Seasonally adjusted line
        if sadj_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[sadj_col],
                mode='lines',
                name='Seasonally adjusted',
                line={'color': self.COLORS['secondary'], 'width': 2}
            ))

        fig = self._apply_layout(fig, 'Live Register')

        fig.update_yaxes(
            title='Number of persons',
            tickformat=',',
            range=[150000, 200000]
        )

        fig.update_layout(
            legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'x': 0.5, 'xanchor': 'center'}
        )

        return fig

    def create_cpi_chart(self, df: pd.DataFrame) -> go.Figure:
        """
        Create Consumer Price Index chart showing CPI and Core CPI

        Args:
            df: DataFrame with columns 'date', 'cpi', 'core_cpi' (or similar)
        """
        fig = go.Figure()

        # Find CPI columns
        cpi_col = None
        core_col = None

        for col in df.columns:
            col_lower = col.lower()
            if 'core' in col_lower:
                core_col = col
            elif 'cpi' in col_lower or 'all items' in col_lower:
                cpi_col = col

        # Fallback
        if cpi_col is None:
            cpi_col = 'cpi'
        if core_col is None:
            core_col = 'core_cpi'

        # CPI line
        if cpi_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[cpi_col],
                mode='lines',
                name='CPI',
                line={'color': self.COLORS['primary'], 'width': 2}
            ))

        # Core CPI line
        if core_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[core_col],
                mode='lines',
                name='Core CPI',
                line={'color': self.COLORS['secondary'], 'width': 2}
            ))

        # Add 2% reference line
        fig.add_hline(y=2, line_dash='dash', line_color=self.COLORS['neutral'],
                     annotation_text='2% target')

        fig = self._apply_layout(fig, 'Annual Changes to Consumer Price')

        fig.update_yaxes(
            title='Percentage',
            tickformat='.1%' if df[cpi_col].max() < 1 else '.1f',
            range=[0, 10]
        )

        fig.update_layout(
            legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'x': 0.5, 'xanchor': 'center'}
        )

        return fig

    def create_pmi_chart(self, df: pd.DataFrame) -> go.Figure:
        """
        Create PMI chart showing Manufacturing, Services, and Construction PMIs

        Args:
            df: DataFrame with columns 'date', 'manufacturing_pmi', 'services_pmi', 'construction_pmi'
        """
        fig = go.Figure()

        # Manufacturing PMI
        if 'manufacturing_pmi' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['manufacturing_pmi'],
                mode='lines',
                name='Manufacturing PMI',
                line={'color': self.COLORS['primary'], 'width': 2}
            ))

        # Services PMI
        if 'services_pmi' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['services_pmi'],
                mode='lines',
                name='Services PMI',
                line={'color': self.COLORS['secondary'], 'width': 2}
            ))

        # Construction PMI
        if 'construction_pmi' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['construction_pmi'],
                mode='lines',
                name='Construction PMI',
                line={'color': self.COLORS['tertiary'], 'width': 2}
            ))

        # Add 50 reference line (expansion/contraction boundary)
        fig.add_hline(y=50, line_dash='dash', line_color=self.COLORS['neutral'],
                     annotation_text='Expansion/Contraction')

        fig = self._apply_layout(fig, 'Monthly PMIs')

        fig.update_yaxes(
            title='PMI Index',
            range=[30, 70]
        )

        fig.update_layout(
            legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'x': 0.5, 'xanchor': 'center'}
        )

        return fig

    def create_exchange_rate_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create exchange rate chart for EUR/GBP and EUR/USD"""
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        if 'eur_gbp' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['eur_gbp'],
                    mode='lines',
                    name='EUR/GBP',
                    line={'color': self.COLORS['primary'], 'width': 2}
                ),
                secondary_y=False
            )

        if 'eur_usd' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['eur_usd'],
                    mode='lines',
                    name='EUR/USD',
                    line={'color': self.COLORS['secondary'], 'width': 2}
                ),
                secondary_y=True
            )

        fig = self._apply_layout(fig, 'Exchange Rates')

        fig.update_yaxes(title_text="EUR/GBP", secondary_y=False)
        fig.update_yaxes(title_text="EUR/USD", secondary_y=True)

        fig.update_layout(
            legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'x': 0.5, 'xanchor': 'center'}
        )

        return fig

    def create_bond_spread_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create chart for Irish 10-year bond yield and spread to Bund"""
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        if 'ireland_10y' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['ireland_10y'],
                    mode='lines',
                    name='Ireland 10Y Yield',
                    line={'color': self.COLORS['primary'], 'width': 2}
                ),
                secondary_y=False
            )

        if 'spread' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['spread'],
                    mode='lines',
                    name='Spread to Bund',
                    line={'color': self.COLORS['secondary'], 'width': 2}
                ),
                secondary_y=True
            )

        fig = self._apply_layout(fig, '10-Year Government Bond')

        fig.update_yaxes(title_text="Yield (%)", secondary_y=False)
        fig.update_yaxes(title_text="Spread (%)", secondary_y=True)

        fig.update_layout(
            legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'x': 0.5, 'xanchor': 'center'}
        )

        return fig

    def create_commodity_chart(self, brent_df: pd.DataFrame,
                               gas_df: pd.DataFrame = None) -> go.Figure:
        """Create commodity prices chart"""
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        if not brent_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=brent_df['date'],
                    y=brent_df['brent_price'],
                    mode='lines',
                    name='Brent Crude ($/barrel)',
                    line={'color': self.COLORS['primary'], 'width': 2}
                ),
                secondary_y=False
            )

        if gas_df is not None and not gas_df.empty and 'gas_price_gbp_thm' in gas_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=gas_df['date'],
                    y=gas_df['gas_price_gbp_thm'],
                    mode='lines',
                    name='Natural Gas (GBp/Thm)',
                    line={'color': self.COLORS['secondary'], 'width': 2}
                ),
                secondary_y=True
            )

        fig = self._apply_layout(fig, 'Commodity Prices')

        fig.update_yaxes(title_text="Brent ($/barrel)", secondary_y=False)
        fig.update_yaxes(title_text="Gas (GBp/Thm)", secondary_y=True)

        fig.update_layout(
            legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'x': 0.5, 'xanchor': 'center'}
        )

        return fig

    def create_consumer_sentiment_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create consumer sentiment index chart"""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['sentiment'],
            mode='lines+markers',
            name='Consumer Sentiment Index',
            line={'color': self.COLORS['primary'], 'width': 2},
            marker={'size': 6}
        ))

        fig = self._apply_layout(fig, 'Consumer Sentiment Index')

        fig.update_yaxes(
            title='Index',
            range=[40, 80]
        )

        return fig

    def create_heatmap_table(self, data: Dict[str, pd.DataFrame]) -> go.Figure:
        """
        Create a heatmap-style table for the economic indicators

        This is more complex and would typically be done with HTML/CSS
        For now, returns a basic table figure
        """
        # This would need more work for full heatmap functionality
        # Returning a placeholder
        fig = go.Figure()
        fig.add_annotation(
            text="Heatmap table - see data tables below",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font={'size': 16}
        )
        return fig


# Test the module
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from data.markets import MarketDataFetcher

    chart_gen = ChartGenerator()
    market_fetcher = MarketDataFetcher()

    print("Testing PMI chart...")
    pmi_data = market_fetcher.get_pmi_data()
    pmi_chart = chart_gen.create_pmi_chart(pmi_data)
    pmi_chart.show()
