"""
Weekly Economic Indicators Dashboard
Streamlit application for viewing and generating economic reports

Run with: streamlit run app.py
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.cso import CSODataFetcher
from data.ecb import ECBDataFetcher
from data.markets import MarketDataFetcher
from data.storage import DataCache, DataStore
from reports.charts import ChartGenerator
from reports.pdf_generator import PDFReportGenerator

# Page configuration
st.set_page_config(
    page_title="Irish Economic Indicators",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def get_fetchers():
    return {
        'cso': CSODataFetcher(),
        'ecb': ECBDataFetcher(),
        'markets': MarketDataFetcher(),
        'cache': DataCache(),
        'store': DataStore()
    }

@st.cache_resource
def get_chart_generator():
    return ChartGenerator()

def load_stored_data(store: DataStore, name: str):
    """Try to load data from store, return None if not found"""
    try:
        df = store.load_dataframe(name)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return None

# Cache data fetching with TTL
@st.cache_data(ttl=3600)  # 1 hour cache
def fetch_all_data():
    """Fetch all data sources - uses stored data when available"""
    fetchers = get_fetchers()
    store = fetchers['store']

    data = {}

    # Try stored data first, fall back to live fetch
    with st.spinner('Loading CSO data...'):
        stored_lr = load_stored_data(store, 'live_register')
        data['live_register'] = stored_lr if stored_lr is not None else fetchers['cso'].get_live_register(months=24)

        stored_cpi = load_stored_data(store, 'cpi')
        data['cpi'] = stored_cpi if stored_cpi is not None else fetchers['cso'].get_cpi(months=24)

        data['unemployment'] = fetchers['cso'].get_unemployment_rate()

    with st.spinner('Loading exchange rate data...'):
        stored_rates = load_stored_data(store, 'exchange_rates')
        data['exchange_rates'] = stored_rates if stored_rates is not None else fetchers['ecb'].get_exchange_rates(days=400)
        data['latest_rates'] = fetchers['ecb'].get_latest_rates()

        stored_monthly_rates = load_stored_data(store, 'monthly_exchange_rates')
        data['monthly_rates'] = stored_monthly_rates if stored_monthly_rates is not None else fetchers['ecb'].get_monthly_averages(months=15)

    with st.spinner('Loading market data...'):
        stored_brent = load_stored_data(store, 'brent_crude')
        data['brent'] = stored_brent if stored_brent is not None else fetchers['markets'].get_brent_crude(days=365)

        stored_gas = load_stored_data(store, 'natural_gas')
        data['gas'] = stored_gas if stored_gas is not None else fetchers['markets'].get_natural_gas(days=365)

        data['commodities'] = fetchers['markets'].get_latest_commodities()
        data['bonds'] = fetchers['markets'].get_bond_yields()

        stored_monthly_bonds = load_stored_data(store, 'monthly_bonds')
        data['monthly_bonds'] = stored_monthly_bonds if stored_monthly_bonds is not None else fetchers['markets'].get_monthly_bond_data(months=15)

        stored_pmi = load_stored_data(store, 'pmi_data')
        data['pmi'] = stored_pmi if stored_pmi is not None else fetchers['markets'].get_pmi_data()
        data['pmi_latest'] = fetchers['markets'].get_latest_pmi()

        stored_sentiment = load_stored_data(store, 'consumer_sentiment')
        data['sentiment'] = stored_sentiment if stored_sentiment is not None else fetchers['markets'].get_consumer_sentiment()
        data['sentiment_latest'] = fetchers['markets'].get_latest_sentiment()

        data['container'] = fetchers['markets'].get_container_costs()

        stored_insolvency = load_stored_data(store, 'insolvency')
        data['insolvency'] = stored_insolvency if stored_insolvency is not None else fetchers['markets'].get_insolvency_data()

    return data


def render_key_metrics(data):
    """Render the key metrics dashboard header"""
    st.markdown("### Key Indicators")

    cols = st.columns(5)

    # CPI
    with cols[0]:
        cpi_val = data['cpi']['cpi'].iloc[0] if not data['cpi'].empty else 2.8
        st.metric(
            label="Consumer Price Index",
            value=f"{cpi_val:.1f}%",
            delta=None
        )

    # Live Register
    with cols[1]:
        lr_col = [c for c in data['live_register'].columns if 'unadjust' in c.lower()]
        lr_val = data['live_register'][lr_col[0]].iloc[0] if lr_col else 172224
        st.metric(
            label="Live Register",
            value=f"{int(lr_val):,}",
            delta=None
        )

    # Consumer Sentiment
    with cols[2]:
        sent_val = data['sentiment_latest']['current']
        sent_change = data['sentiment_latest']['change']
        st.metric(
            label="Consumer Sentiment",
            value=f"{sent_val:.1f}",
            delta=f"{sent_change:+.1f}"
        )

    # Bond Spread
    with cols[3]:
        spread_val = data['bonds']['spread']
        st.metric(
            label="10Y Bond Spread",
            value=f"{spread_val:.3f}",
            delta=None
        )

    # EUR/GBP
    with cols[4]:
        eur_gbp = data['latest_rates']['eur_gbp']
        eur_gbp_change = data['latest_rates']['eur_gbp_wow']
        st.metric(
            label="EUR/GBP",
            value=f"£{eur_gbp:.3f}",
            delta=f"{eur_gbp_change:+.2f}%"
        )


def render_commentary(data):
    """Generate and render commentary bullets"""
    st.markdown("### Weekly Commentary")

    commentary = []

    # Live Register
    lr_col = [c for c in data['live_register'].columns if 'unadjust' in c.lower()]
    if lr_col and len(data['live_register']) > 1:
        lr_current = int(data['live_register'][lr_col[0]].iloc[0])
        lr_prev = int(data['live_register'][lr_col[0]].iloc[1])
        lr_change = lr_current - lr_prev
        unemployment = data['unemployment']['rate']
        commentary.append(
            f"The monthly Live Register (unadjusted) stood at **{lr_current:,}**, "
            f"{'up' if lr_change > 0 else 'down'} by {abs(lr_change):,} from the previous month. "
            f"The seasonally adjusted unemployment rate was **{unemployment}%**."
        )

    # Container costs
    container = data['container']
    commentary.append(
        f"The market average rate for a 40ft container from Asia to North Europe was "
        f"**${container['current']:,}**. Week-on-week this was {container['wow']:+.2f}% "
        f"and {container['yoy']:+.2f}% year-on-year."
    )

    # Natural Gas
    gas = data['commodities'].get('gas', {})
    commentary.append(
        f"UK Natural Gas futures traded between {gas.get('low', 87.50):.2f} and "
        f"{gas.get('high', 106.77):.2f} GBp/Thm. The closing price was "
        f"**{gas.get('price', 104.15):.2f} GBp/Thm**."
    )

    # Brent Crude
    brent = data['commodities'].get('brent', {})
    commentary.append(
        f"Brent crude oil spot price was trading at **${brent.get('price', 66.91):.2f}** a barrel, "
        f"{brent.get('wow', 0):+.2f}% week-on-week and {brent.get('yoy', 0):+.2f}% year-on-year."
    )

    # PMI
    pmi = data['pmi_latest']
    commentary.append(
        f"In {pmi['date']}, Manufacturing PMI was **{pmi['manufacturing']['current']:.1f}** "
        f"({'up' if pmi['manufacturing']['change'] > 0 else 'down'} from {pmi['manufacturing']['previous']:.1f}), "
        f"Services PMI was **{pmi['services']['current']:.1f}**, and "
        f"Construction PMI was **{pmi['construction']['current']:.1f}**."
    )

    # Exchange rates
    rates = data['latest_rates']
    commentary.append(
        f"The Euro was trading at **£{rates['eur_gbp']:.3f}** against Sterling "
        f"and **${rates['eur_usd']:.3f}** against the Dollar ({rates['eur_usd_wow']:+.2f}% WoW)."
    )

    # Bond spread
    bonds = data['bonds']
    commentary.append(
        f"The Irish 10-year government bond yield was **{bonds['ireland_10y']:.3f}%** "
        f"with a spread of **{bonds['spread']:.3f}** over German Bunds."
    )

    # Consumer sentiment
    sent = data['sentiment_latest']
    commentary.append(
        f"In {sent['date']}, Irish consumer sentiment was **{sent['current']:.1f}**, "
        f"{'up' if sent['change'] > 0 else 'down'} from {sent['previous']:.1f} the previous month."
    )

    for bullet in commentary:
        st.markdown(f"• {bullet}")

    return commentary


def render_charts(data):
    """Render all charts"""
    chart_gen = get_chart_generator()

    st.markdown("### Charts")

    # Row 1: Live Register and CPI
    col1, col2 = st.columns(2)

    with col1:
        if not data['live_register'].empty:
            fig = chart_gen.create_live_register_chart(data['live_register'])
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not data['cpi'].empty:
            fig = chart_gen.create_cpi_chart(data['cpi'])
            st.plotly_chart(fig, use_container_width=True)

    # Row 2: PMI
    if not data['pmi'].empty:
        fig = chart_gen.create_pmi_chart(data['pmi'])
        st.plotly_chart(fig, use_container_width=True)

    # Row 3: Exchange rates and Bonds
    col1, col2 = st.columns(2)

    with col1:
        if not data['monthly_rates'].empty:
            fig = chart_gen.create_exchange_rate_chart(data['monthly_rates'])
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not data['monthly_bonds'].empty:
            fig = chart_gen.create_bond_spread_chart(data['monthly_bonds'])
            st.plotly_chart(fig, use_container_width=True)

    # Row 4: Commodities and Sentiment
    col1, col2 = st.columns(2)

    with col1:
        if not data['brent'].empty:
            fig = chart_gen.create_commodity_chart(data['brent'], data['gas'])
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not data['sentiment'].empty:
            fig = chart_gen.create_consumer_sentiment_chart(data['sentiment'])
            st.plotly_chart(fig, use_container_width=True)


def render_heatmap_table(data):
    """Render the heatmap data table"""
    st.markdown("### Economic Indicator Heatmap")

    # Build the heatmap dataframe
    pmi_df = data['pmi'].copy()
    sentiment_df = data['sentiment'].copy()
    rates_df = data['monthly_rates'].copy()
    bonds_df = data['monthly_bonds'].copy()

    # Merge all data on date
    pmi_df['month'] = pmi_df['date'].dt.strftime('%b-%y')
    sentiment_df['month'] = sentiment_df['date'].dt.strftime('%b-%y')
    rates_df['month'] = rates_df['date'].dt.strftime('%b-%y')
    bonds_df['month'] = bonds_df['date'].dt.strftime('%b-%y')

    # Create combined table
    heatmap_data = pmi_df[['month', 'manufacturing_pmi', 'services_pmi', 'construction_pmi']].copy()
    heatmap_data = heatmap_data.merge(sentiment_df[['month', 'sentiment']], on='month', how='left')
    heatmap_data = heatmap_data.merge(rates_df[['month', 'eur_gbp', 'eur_usd']], on='month', how='left')
    heatmap_data = heatmap_data.merge(bonds_df[['month', 'ireland_10y', 'spread']], on='month', how='left')

    # Rename columns
    heatmap_data.columns = ['Month', 'Manufacturing PMI', 'Services PMI', 'Construction PMI',
                           'Consumer Sentiment', 'EUR/GBP', 'EUR/USD', 'Ireland 10Y', 'Spread to Bund']

    # Style the dataframe
    def color_pmi(val):
        if pd.isna(val):
            return ''
        if val >= 55:
            return 'background-color: #c6efce'
        elif val >= 50:
            return 'background-color: #e2f0d9'
        elif val >= 45:
            return 'background-color: #ffc7ce'
        else:
            return 'background-color: #ff9999'

    def color_sentiment(val):
        if pd.isna(val):
            return ''
        if val >= 65:
            return 'background-color: #c6efce'
        elif val >= 55:
            return 'background-color: #ffeb9c'
        else:
            return 'background-color: #ffc7ce'

    styled = heatmap_data.style.applymap(
        color_pmi,
        subset=['Manufacturing PMI', 'Services PMI', 'Construction PMI']
    ).applymap(
        color_sentiment,
        subset=['Consumer Sentiment']
    ).format({
        'Manufacturing PMI': '{:.1f}',
        'Services PMI': '{:.1f}',
        'Construction PMI': '{:.1f}',
        'Consumer Sentiment': '{:.1f}',
        'EUR/GBP': '{:.3f}',
        'EUR/USD': '{:.3f}',
        'Ireland 10Y': '{:.3f}',
        'Spread to Bund': '{:.3f}'
    })

    st.dataframe(styled, use_container_width=True, height=400)


def render_data_tables(data):
    """Render raw data tables for inspection"""
    st.markdown("### Raw Data")

    tabs = st.tabs(["Live Register", "CPI", "PMI", "Exchange Rates", "Bonds", "Sentiment", "Insolvency"])

    with tabs[0]:
        st.dataframe(data['live_register'], use_container_width=True)

    with tabs[1]:
        st.dataframe(data['cpi'], use_container_width=True)

    with tabs[2]:
        st.dataframe(data['pmi'], use_container_width=True)

    with tabs[3]:
        st.dataframe(data['monthly_rates'], use_container_width=True)

    with tabs[4]:
        st.dataframe(data['monthly_bonds'], use_container_width=True)

    with tabs[5]:
        st.dataframe(data['sentiment'], use_container_width=True)

    with tabs[6]:
        st.dataframe(data['insolvency'], use_container_width=True)


def render_sidebar():
    """Render sidebar with controls"""
    st.sidebar.title("📊 Economic Indicators")
    st.sidebar.markdown("Weekly Report Dashboard")

    st.sidebar.markdown("---")

    # Report date
    report_date = st.sidebar.date_input(
        "Report Date",
        value=datetime.now(),
        max_value=datetime.now()
    )

    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    # Data source status
    st.sidebar.markdown("### Data Sources")
    st.sidebar.markdown("""
    - ✅ CSO Ireland (StatBank)
    - ✅ ECB Statistical Warehouse
    - ✅ Yahoo Finance
    - ⚠️ PMI (cached data)
    - ⚠️ Consumer Sentiment (cached)
    """)

    st.sidebar.markdown("---")

    # About
    st.sidebar.markdown("### About")
    st.sidebar.markdown("""
    A dashboard tracking key Irish and European
    economic indicators with live data.

    **Last updated:** {}
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M')))

    return report_date


def main():
    """Main application"""
    # Render sidebar
    report_date = render_sidebar()

    # Title
    st.title("Economic Indicators")
    st.markdown(f"**{report_date.strftime('%d %B %Y')}**")

    st.markdown("---")

    # Fetch data
    try:
        data = fetch_all_data()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.stop()

    # Render components
    render_key_metrics(data)

    st.markdown("---")

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Commentary", "📈 Charts", "🗓️ Heatmap", "📊 Data"])

    with tab1:
        commentary = render_commentary(data)

    with tab2:
        render_charts(data)

    with tab3:
        render_heatmap_table(data)

    with tab4:
        render_data_tables(data)

    # Footer
    st.markdown("---")
    st.markdown("*Irish Economic Indicators Dashboard*")


if __name__ == "__main__":
    main()
