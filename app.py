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
import io

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.cso import CSODataFetcher
from data.ecb import ECBDataFetcher
from data.markets import MarketDataFetcher
from data.storage import DataCache, DataStore
from reports.charts import ChartGenerator
from config import ALERT_THRESHOLDS, THEMES, DATE_PRESETS

# Page configuration
st.set_page_config(
    page_title="Irish Economic Indicators",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# THEME & STYLING (Feature 10: Dark Mode)
# ============================================================================

def init_session_state():
    """Initialize session state variables"""
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    if 'start_date' not in st.session_state:
        st.session_state.start_date = datetime.now() - timedelta(days=365)
    if 'end_date' not in st.session_state:
        st.session_state.end_date = datetime.now()
    if 'compare_yoy' not in st.session_state:
        st.session_state.compare_yoy = False
    if 'data_fetch_times' not in st.session_state:
        st.session_state.data_fetch_times = {}


def apply_theme():
    """Apply custom CSS based on current theme (Feature 10: Dark Mode)"""
    theme = THEMES[st.session_state.theme]

    css = f"""
    <style>
        /* Main theme colors */
        .stApp {{
            background-color: {theme['background']};
        }}

        /* Mobile responsiveness (Feature 7) */
        @media (max-width: 768px) {{
            .metric-container {{
                flex-direction: column;
            }}
            .stMetric {{
                margin-bottom: 1rem;
            }}
            [data-testid="column"] {{
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }}
        }}

        /* Card styling */
        .metric-card {{
            background-color: {theme['card_background']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
        }}

        /* Alert styling */
        .alert-warning {{
            background-color: #FFF3CD;
            border-left: 4px solid #FFC107;
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 4px;
        }}

        .alert-critical {{
            background-color: #F8D7DA;
            border-left: 4px solid #DC3545;
            padding: 0.75rem;
            margin: 0.5rem 0;
            border-radius: 4px;
        }}

        /* Loading skeleton */
        .skeleton {{
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
            border-radius: 4px;
            height: 60px;
        }}

        @keyframes loading {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}

        /* Cache indicator colors */
        .cache-fresh {{ color: #4CAF50; }}
        .cache-stale {{ color: #FFC107; }}
        .cache-old {{ color: #F44336; }}

        /* Dark mode specific overrides */
        {''.join([f'''
        .stApp [data-testid="stMarkdownContainer"] {{
            color: {theme['text']};
        }}
        ''' if st.session_state.theme == 'dark' else ''])}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ============================================================================
# URL PARAMETERS (Feature 9: Bookmark/Share)
# ============================================================================

def read_url_params():
    """Read and apply URL parameters"""
    params = st.query_params

    if 'theme' in params:
        st.session_state.theme = params['theme']
    if 'start' in params:
        try:
            st.session_state.start_date = datetime.strptime(params['start'], '%Y-%m-%d')
        except ValueError:
            pass
    if 'end' in params:
        try:
            st.session_state.end_date = datetime.strptime(params['end'], '%Y-%m-%d')
        except ValueError:
            pass
    if 'compare' in params:
        st.session_state.compare_yoy = params['compare'] == 'true'


def update_url_params():
    """Update URL parameters based on current state"""
    st.query_params['theme'] = st.session_state.theme
    st.query_params['start'] = st.session_state.start_date.strftime('%Y-%m-%d')
    st.query_params['end'] = st.session_state.end_date.strftime('%Y-%m-%d')
    st.query_params['compare'] = 'true' if st.session_state.compare_yoy else 'false'


# ============================================================================
# DATA FETCHING WITH ERROR HANDLING (Feature 1: Graceful Failures)
# ============================================================================

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


@st.cache_data(ttl=3600)
def fetch_all_data():
    """Fetch all data sources with graceful error handling (Feature 1)"""
    fetchers = get_fetchers()
    store = fetchers['store']

    data = {}
    errors = []
    fetch_times = {}

    # CSO Data
    try:
        with st.spinner('Loading CSO data...'):
            fetch_times['CSO'] = datetime.now()
            stored_lr = load_stored_data(store, 'live_register')
            data['live_register'] = stored_lr if stored_lr is not None else fetchers['cso'].get_live_register(months=24)

            stored_cpi = load_stored_data(store, 'cpi')
            data['cpi'] = stored_cpi if stored_cpi is not None else fetchers['cso'].get_cpi(months=24)

            data['unemployment'] = fetchers['cso'].get_unemployment_rate()
    except Exception as e:
        errors.append(('CSO Data (Live Register, CPI)', str(e)))
        data['live_register'] = pd.DataFrame()
        data['cpi'] = pd.DataFrame()
        data['unemployment'] = {'rate': None, 'date': None}

    # ECB Data
    try:
        with st.spinner('Loading exchange rate data...'):
            fetch_times['ECB'] = datetime.now()
            stored_rates = load_stored_data(store, 'exchange_rates')
            data['exchange_rates'] = stored_rates if stored_rates is not None else fetchers['ecb'].get_exchange_rates(days=400)
            data['latest_rates'] = fetchers['ecb'].get_latest_rates()

            stored_monthly_rates = load_stored_data(store, 'monthly_exchange_rates')
            data['monthly_rates'] = stored_monthly_rates if stored_monthly_rates is not None else fetchers['ecb'].get_monthly_averages(months=15)
    except Exception as e:
        errors.append(('ECB Exchange Rates', str(e)))
        data['exchange_rates'] = pd.DataFrame()
        data['latest_rates'] = {'eur_gbp': None, 'eur_usd': None, 'eur_gbp_wow': 0, 'eur_usd_wow': 0}
        data['monthly_rates'] = pd.DataFrame()

    # Market Data
    try:
        with st.spinner('Loading market data...'):
            fetch_times['Markets'] = datetime.now()
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
    except Exception as e:
        errors.append(('Market Data', str(e)))
        data['brent'] = pd.DataFrame()
        data['gas'] = pd.DataFrame()
        data['commodities'] = {}
        data['bonds'] = {'ireland_10y': None, 'germany_10y': None, 'spread': None}
        data['monthly_bonds'] = pd.DataFrame()
        data['pmi'] = pd.DataFrame()
        data['pmi_latest'] = {'manufacturing': {}, 'services': {}, 'construction': {}, 'date': ''}
        data['sentiment'] = pd.DataFrame()
        data['sentiment_latest'] = {'current': None, 'previous': None, 'change': 0, 'date': ''}
        data['container'] = {'current': 0, 'wow': 0, 'yoy': 0}
        data['insolvency'] = pd.DataFrame()

    # Store fetch times in session state
    st.session_state.data_fetch_times = fetch_times

    return data, errors


# ============================================================================
# ALERTS & THRESHOLDS (Feature 5)
# ============================================================================

def check_alerts(data):
    """Check data against thresholds and return alerts"""
    alerts = []

    # Check PMI
    pmi_latest = data.get('pmi_latest', {})
    for pmi_type in ['manufacturing', 'services', 'construction']:
        pmi_data = pmi_latest.get(pmi_type, {})
        current = pmi_data.get('current')
        if current is not None:
            if current < ALERT_THRESHOLDS['pmi_severe']:
                alerts.append({
                    'level': 'critical',
                    'message': f"{pmi_type.title()} PMI at {current:.1f} - severe contraction"
                })
            elif current < ALERT_THRESHOLDS['pmi_contraction']:
                alerts.append({
                    'level': 'warning',
                    'message': f"{pmi_type.title()} PMI at {current:.1f} - contraction territory"
                })

    # Check Inflation (CPI)
    if not data.get('cpi', pd.DataFrame()).empty:
        cpi_val = data['cpi']['cpi'].iloc[0] if 'cpi' in data['cpi'].columns else None
        if cpi_val is not None:
            if cpi_val > ALERT_THRESHOLDS['inflation_critical']:
                alerts.append({
                    'level': 'critical',
                    'message': f"Inflation at {cpi_val:.1f}% - well above ECB target"
                })
            elif cpi_val > ALERT_THRESHOLDS['inflation_warning']:
                alerts.append({
                    'level': 'warning',
                    'message': f"Inflation at {cpi_val:.1f}% - above ECB target"
                })

    # Check Bond Spread
    bonds = data.get('bonds', {})
    spread = bonds.get('spread')
    if spread is not None:
        if spread > ALERT_THRESHOLDS['bond_spread_critical']:
            alerts.append({
                'level': 'critical',
                'message': f"Bond spread at {spread:.3f} - elevated risk premium"
            })
        elif spread > ALERT_THRESHOLDS['bond_spread_warning']:
            alerts.append({
                'level': 'warning',
                'message': f"Bond spread at {spread:.3f} - above normal levels"
            })

    # Check Consumer Sentiment
    sentiment = data.get('sentiment_latest', {})
    sent_val = sentiment.get('current')
    if sent_val is not None:
        if sent_val < ALERT_THRESHOLDS['sentiment_critical']:
            alerts.append({
                'level': 'critical',
                'message': f"Consumer sentiment at {sent_val:.1f} - very pessimistic"
            })
        elif sent_val < ALERT_THRESHOLDS['sentiment_warning']:
            alerts.append({
                'level': 'warning',
                'message': f"Consumer sentiment at {sent_val:.1f} - below neutral"
            })

    return alerts


def render_alerts(alerts):
    """Render alert banners"""
    if not alerts:
        return

    st.markdown("### Alerts")
    for alert in alerts:
        if alert['level'] == 'critical':
            st.error(f"⚠️ {alert['message']}")
        else:
            st.warning(f"⚡ {alert['message']}")


def render_error_banner(errors):
    """Render error banner for failed data sources (Feature 1)"""
    if not errors:
        return

    with st.expander(f"⚠️ {len(errors)} data source(s) unavailable", expanded=False):
        for source, error in errors:
            st.warning(f"**{source}**: {error}")
        st.info("Dashboard is showing available data. Some sections may be incomplete.")


# ============================================================================
# DATE FILTERING (Feature 2: Date Range Selector)
# ============================================================================

def filter_dataframe_by_date(df, date_column='date'):
    """Filter DataFrame by selected date range"""
    if df is None or df.empty:
        return df

    if date_column not in df.columns:
        return df

    start = st.session_state.start_date
    end = st.session_state.end_date

    df_filtered = df.copy()
    df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')

    mask = (df_filtered[date_column] >= pd.Timestamp(start)) & (df_filtered[date_column] <= pd.Timestamp(end))
    return df_filtered[mask]


# ============================================================================
# DOWNLOAD OPTIONS (Feature 3)
# ============================================================================

def convert_df_to_csv(df):
    """Convert DataFrame to CSV bytes"""
    return df.to_csv(index=False).encode('utf-8')


def create_excel_download(data):
    """Create Excel file with multiple sheets"""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        datasets = {
            'Live Register': data.get('live_register', pd.DataFrame()),
            'CPI': data.get('cpi', pd.DataFrame()),
            'PMI': data.get('pmi', pd.DataFrame()),
            'Exchange Rates': data.get('monthly_rates', pd.DataFrame()),
            'Bonds': data.get('monthly_bonds', pd.DataFrame()),
            'Sentiment': data.get('sentiment', pd.DataFrame()),
            'Insolvency': data.get('insolvency', pd.DataFrame()),
        }

        for sheet_name, df in datasets.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    return output.getvalue()


def render_download_section(data):
    """Render download buttons (Feature 3)"""
    st.markdown("### Download Data")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Combined CSV (current view)
        combined_data = []
        for name, df in [('live_register', data.get('live_register')),
                         ('cpi', data.get('cpi')),
                         ('pmi', data.get('pmi'))]:
            if df is not None and not df.empty:
                df_copy = df.copy()
                df_copy['dataset'] = name
                combined_data.append(df_copy)

        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            csv_data = convert_df_to_csv(combined_df)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"economic_indicators_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col2:
        # Excel with multiple sheets
        try:
            excel_data = create_excel_download(data)
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=f"economic_indicators_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception:
            st.button("Download Excel", disabled=True, help="Excel export unavailable")

    with col3:
        # Copy shareable link
        link = f"?theme={st.session_state.theme}&start={st.session_state.start_date.strftime('%Y-%m-%d')}&end={st.session_state.end_date.strftime('%Y-%m-%d')}"
        st.text_input("Shareable Link", value=link, help="Copy this to share current view")


# ============================================================================
# COMPARISON VIEW (Feature 4: Year-over-Year)
# ============================================================================

def get_yoy_comparison(df, date_column='date', value_columns=None):
    """Add year-over-year comparison columns"""
    if df is None or df.empty:
        return df

    if date_column not in df.columns:
        return df

    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

    if value_columns is None:
        value_columns = [col for col in df.columns if col != date_column and df[col].dtype in ['float64', 'int64']]

    for col in value_columns:
        df[f'{col}_yoy'] = df[col].pct_change(periods=12) * 100

    return df


# ============================================================================
# CACHING INDICATOR (Feature 8)
# ============================================================================

def render_cache_status():
    """Render cache freshness indicators"""
    st.sidebar.markdown("### Data Freshness")

    fetch_times = st.session_state.get('data_fetch_times', {})

    if not fetch_times:
        st.sidebar.text("No data loaded yet")
        return

    now = datetime.now()

    for source, fetch_time in fetch_times.items():
        age = now - fetch_time
        age_minutes = age.total_seconds() / 60

        if age_minutes < 15:
            status = "🟢"
            css_class = "cache-fresh"
        elif age_minutes < 60:
            status = "🟡"
            css_class = "cache-stale"
        else:
            status = "🔴"
            css_class = "cache-old"

        if age_minutes < 1:
            age_str = "just now"
        elif age_minutes < 60:
            age_str = f"{int(age_minutes)}m ago"
        else:
            age_str = f"{int(age_minutes / 60)}h ago"

        st.sidebar.markdown(f"{status} **{source}**: {age_str}")


# ============================================================================
# LOADING STATES (Feature 6)
# ============================================================================

def render_loading_skeleton():
    """Render loading placeholder"""
    st.markdown("""
        <div class="skeleton" style="height: 100px; margin-bottom: 1rem;"></div>
        <div class="skeleton" style="height: 60px; margin-bottom: 1rem;"></div>
        <div class="skeleton" style="height: 300px;"></div>
    """, unsafe_allow_html=True)


# ============================================================================
# METRICS & DASHBOARD COMPONENTS
# ============================================================================

def render_key_metrics(data):
    """Render the key metrics dashboard header (Feature 7: Responsive)"""
    st.markdown("### Key Indicators")

    # Responsive: fewer columns on mobile handled via CSS
    cols = st.columns(5)

    # CPI
    with cols[0]:
        if not data.get('cpi', pd.DataFrame()).empty and 'cpi' in data['cpi'].columns:
            cpi_val = data['cpi']['cpi'].iloc[0]
            # Alert color based on threshold
            delta_color = "inverse" if cpi_val > ALERT_THRESHOLDS['inflation_warning'] else "normal"
            st.metric(
                label="Consumer Price Index",
                value=f"{cpi_val:.1f}%",
                delta=None
            )
        else:
            st.metric(label="Consumer Price Index", value="N/A")

    # Live Register
    with cols[1]:
        if not data.get('live_register', pd.DataFrame()).empty:
            lr_col = [c for c in data['live_register'].columns if 'unadjust' in c.lower()]
            if lr_col:
                lr_val = data['live_register'][lr_col[0]].iloc[0]
                st.metric(
                    label="Live Register",
                    value=f"{int(lr_val):,}",
                    delta=None
                )
            else:
                st.metric(label="Live Register", value="N/A")
        else:
            st.metric(label="Live Register", value="N/A")

    # Consumer Sentiment
    with cols[2]:
        sentiment = data.get('sentiment_latest', {})
        sent_val = sentiment.get('current')
        sent_change = sentiment.get('change', 0)
        if sent_val is not None:
            st.metric(
                label="Consumer Sentiment",
                value=f"{sent_val:.1f}",
                delta=f"{sent_change:+.1f}"
            )
        else:
            st.metric(label="Consumer Sentiment", value="N/A")

    # Bond Spread
    with cols[3]:
        bonds = data.get('bonds', {})
        spread_val = bonds.get('spread')
        if spread_val is not None:
            st.metric(
                label="10Y Bond Spread",
                value=f"{spread_val:.3f}",
                delta=None
            )
        else:
            st.metric(label="10Y Bond Spread", value="N/A")

    # EUR/GBP
    with cols[4]:
        rates = data.get('latest_rates', {})
        eur_gbp = rates.get('eur_gbp')
        eur_gbp_change = rates.get('eur_gbp_wow', 0)
        if eur_gbp is not None:
            st.metric(
                label="EUR/GBP",
                value=f"£{eur_gbp:.3f}",
                delta=f"{eur_gbp_change:+.2f}%"
            )
        else:
            st.metric(label="EUR/GBP", value="N/A")


def render_commentary(data):
    """Generate and render commentary bullets"""
    st.markdown("### Weekly Commentary")

    commentary = []

    # Live Register
    if not data.get('live_register', pd.DataFrame()).empty:
        lr_col = [c for c in data['live_register'].columns if 'unadjust' in c.lower()]
        if lr_col and len(data['live_register']) > 1:
            lr_current = int(data['live_register'][lr_col[0]].iloc[0])
            lr_prev = int(data['live_register'][lr_col[0]].iloc[1])
            lr_change = lr_current - lr_prev
            unemployment = data.get('unemployment', {}).get('rate', 'N/A')
            commentary.append(
                f"The monthly Live Register (unadjusted) stood at **{lr_current:,}**, "
                f"{'up' if lr_change > 0 else 'down'} by {abs(lr_change):,} from the previous month. "
                f"The seasonally adjusted unemployment rate was **{unemployment}%**."
            )

    # Container costs
    container = data.get('container', {})
    if container.get('current'):
        commentary.append(
            f"The market average rate for a 40ft container from Asia to North Europe was "
            f"**${container['current']:,}**. Week-on-week this was {container.get('wow', 0):+.2f}% "
            f"and {container.get('yoy', 0):+.2f}% year-on-year."
        )

    # Natural Gas
    gas = data.get('commodities', {}).get('gas', {})
    if gas:
        commentary.append(
            f"UK Natural Gas futures traded between {gas.get('low', 0):.2f} and "
            f"{gas.get('high', 0):.2f} GBp/Thm. The closing price was "
            f"**{gas.get('price', 0):.2f} GBp/Thm**."
        )

    # Brent Crude
    brent = data.get('commodities', {}).get('brent', {})
    if brent:
        commentary.append(
            f"Brent crude oil spot price was trading at **${brent.get('price', 0):.2f}** a barrel, "
            f"{brent.get('wow', 0):+.2f}% week-on-week and {brent.get('yoy', 0):+.2f}% year-on-year."
        )

    # PMI
    pmi = data.get('pmi_latest', {})
    if pmi.get('date'):
        mfg = pmi.get('manufacturing', {})
        svc = pmi.get('services', {})
        con = pmi.get('construction', {})
        commentary.append(
            f"In {pmi['date']}, Manufacturing PMI was **{mfg.get('current', 0):.1f}** "
            f"({'up' if mfg.get('change', 0) > 0 else 'down'} from {mfg.get('previous', 0):.1f}), "
            f"Services PMI was **{svc.get('current', 0):.1f}**, and "
            f"Construction PMI was **{con.get('current', 0):.1f}**."
        )

    # Exchange rates
    rates = data.get('latest_rates', {})
    if rates.get('eur_gbp'):
        commentary.append(
            f"The Euro was trading at **£{rates['eur_gbp']:.3f}** against Sterling "
            f"and **${rates.get('eur_usd', 0):.3f}** against the Dollar ({rates.get('eur_usd_wow', 0):+.2f}% WoW)."
        )

    # Bond spread
    bonds = data.get('bonds', {})
    if bonds.get('ireland_10y'):
        commentary.append(
            f"The Irish 10-year government bond yield was **{bonds['ireland_10y']:.3f}%** "
            f"with a spread of **{bonds.get('spread', 0):.3f}** over German Bunds."
        )

    # Consumer sentiment
    sent = data.get('sentiment_latest', {})
    if sent.get('current'):
        commentary.append(
            f"In {sent.get('date', 'recent month')}, Irish consumer sentiment was **{sent['current']:.1f}**, "
            f"{'up' if sent.get('change', 0) > 0 else 'down'} from {sent.get('previous', 0):.1f} the previous month."
        )

    if commentary:
        for bullet in commentary:
            st.markdown(f"• {bullet}")
    else:
        st.info("Commentary unavailable - insufficient data")

    return commentary


def render_charts(data):
    """Render all charts"""
    chart_gen = get_chart_generator()

    st.markdown("### Charts")

    # Row 1: Live Register and CPI
    col1, col2 = st.columns(2)

    with col1:
        lr_data = data.get('live_register', pd.DataFrame())
        if not lr_data.empty:
            fig = chart_gen.create_live_register_chart(lr_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Live Register data unavailable")

    with col2:
        cpi_data = data.get('cpi', pd.DataFrame())
        if not cpi_data.empty:
            fig = chart_gen.create_cpi_chart(cpi_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("CPI data unavailable")

    # Row 2: PMI
    pmi_data = data.get('pmi', pd.DataFrame())
    if not pmi_data.empty:
        fig = chart_gen.create_pmi_chart(pmi_data)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("PMI data unavailable")

    # Row 3: Exchange rates and Bonds
    col1, col2 = st.columns(2)

    with col1:
        rates_data = data.get('monthly_rates', pd.DataFrame())
        if not rates_data.empty:
            fig = chart_gen.create_exchange_rate_chart(rates_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Exchange rate data unavailable")

    with col2:
        bonds_data = data.get('monthly_bonds', pd.DataFrame())
        if not bonds_data.empty:
            fig = chart_gen.create_bond_spread_chart(bonds_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Bond data unavailable")

    # Row 4: Commodities and Sentiment
    col1, col2 = st.columns(2)

    with col1:
        brent_data = data.get('brent', pd.DataFrame())
        gas_data = data.get('gas', pd.DataFrame())
        if not brent_data.empty:
            fig = chart_gen.create_commodity_chart(brent_data, gas_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Commodity data unavailable")

    with col2:
        sentiment_data = data.get('sentiment', pd.DataFrame())
        if not sentiment_data.empty:
            fig = chart_gen.create_consumer_sentiment_chart(sentiment_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sentiment data unavailable")


def render_heatmap_table(data):
    """Render the heatmap data table"""
    st.markdown("### Economic Indicator Heatmap")

    pmi_df = data.get('pmi', pd.DataFrame())
    sentiment_df = data.get('sentiment', pd.DataFrame())
    rates_df = data.get('monthly_rates', pd.DataFrame())
    bonds_df = data.get('monthly_bonds', pd.DataFrame())

    if pmi_df.empty:
        st.info("Insufficient data for heatmap")
        return

    # Build the heatmap dataframe
    pmi_df = pmi_df.copy()
    pmi_df['month'] = pd.to_datetime(pmi_df['date']).dt.strftime('%b-%y')

    heatmap_data = pmi_df[['month', 'manufacturing_pmi', 'services_pmi', 'construction_pmi']].copy()

    if not sentiment_df.empty:
        sentiment_df = sentiment_df.copy()
        sentiment_df['month'] = pd.to_datetime(sentiment_df['date']).dt.strftime('%b-%y')
        heatmap_data = heatmap_data.merge(sentiment_df[['month', 'sentiment']], on='month', how='left')

    if not rates_df.empty:
        rates_df = rates_df.copy()
        rates_df['month'] = pd.to_datetime(rates_df['date']).dt.strftime('%b-%y')
        heatmap_data = heatmap_data.merge(rates_df[['month', 'eur_gbp', 'eur_usd']], on='month', how='left')

    if not bonds_df.empty:
        bonds_df = bonds_df.copy()
        bonds_df['month'] = pd.to_datetime(bonds_df['date']).dt.strftime('%b-%y')
        heatmap_data = heatmap_data.merge(bonds_df[['month', 'ireland_10y', 'spread']], on='month', how='left')

    # Rename columns
    col_mapping = {
        'month': 'Month',
        'manufacturing_pmi': 'Manufacturing PMI',
        'services_pmi': 'Services PMI',
        'construction_pmi': 'Construction PMI',
        'sentiment': 'Consumer Sentiment',
        'eur_gbp': 'EUR/GBP',
        'eur_usd': 'EUR/USD',
        'ireland_10y': 'Ireland 10Y',
        'spread': 'Spread to Bund'
    }
    heatmap_data = heatmap_data.rename(columns={k: v for k, v in col_mapping.items() if k in heatmap_data.columns})

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

    pmi_cols = [c for c in ['Manufacturing PMI', 'Services PMI', 'Construction PMI'] if c in heatmap_data.columns]
    sentiment_cols = [c for c in ['Consumer Sentiment'] if c in heatmap_data.columns]

    styled = heatmap_data.style
    if pmi_cols:
        styled = styled.applymap(color_pmi, subset=pmi_cols)
    if sentiment_cols:
        styled = styled.applymap(color_sentiment, subset=sentiment_cols)

    # Format numeric columns
    format_dict = {}
    for col in heatmap_data.columns:
        if 'PMI' in col or 'Sentiment' in col:
            format_dict[col] = '{:.1f}'
        elif col in ['EUR/GBP', 'EUR/USD', 'Ireland 10Y', 'Spread to Bund']:
            format_dict[col] = '{:.3f}'

    if format_dict:
        styled = styled.format(format_dict)

    st.dataframe(styled, use_container_width=True, height=400)


def render_data_tables(data):
    """Render raw data tables for inspection"""
    st.markdown("### Raw Data")

    tabs = st.tabs(["Live Register", "CPI", "PMI", "Exchange Rates", "Bonds", "Sentiment", "Insolvency"])

    with tabs[0]:
        df = data.get('live_register', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")

    with tabs[1]:
        df = data.get('cpi', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")

    with tabs[2]:
        df = data.get('pmi', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")

    with tabs[3]:
        df = data.get('monthly_rates', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")

    with tabs[4]:
        df = data.get('monthly_bonds', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")

    with tabs[5]:
        df = data.get('sentiment', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")

    with tabs[6]:
        df = data.get('insolvency', pd.DataFrame())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Data unavailable")


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar with controls"""
    st.sidebar.title("📊 Economic Indicators")
    st.sidebar.markdown("Weekly Report Dashboard")

    st.sidebar.markdown("---")

    # Theme toggle (Feature 10: Dark Mode)
    st.sidebar.markdown("### Settings")
    theme = st.sidebar.selectbox(
        "Theme",
        options=['light', 'dark'],
        index=0 if st.session_state.theme == 'light' else 1,
        key='theme_select'
    )
    if theme != st.session_state.theme:
        st.session_state.theme = theme
        st.rerun()

    st.sidebar.markdown("---")

    # Date range selector (Feature 2)
    st.sidebar.markdown("### Date Range")

    # Preset buttons
    preset_cols = st.sidebar.columns(2)
    for i, (label, days) in enumerate(DATE_PRESETS.items()):
        col = preset_cols[i % 2]
        if col.button(label, key=f"preset_{label}", use_container_width=True):
            st.session_state.start_date = datetime.now() - timedelta(days=days)
            st.session_state.end_date = datetime.now()
            st.rerun()

    # Custom date inputs
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start = st.date_input(
            "From",
            value=st.session_state.start_date,
            max_value=datetime.now(),
            key='start_date_input'
        )
        if start != st.session_state.start_date.date():
            st.session_state.start_date = datetime.combine(start, datetime.min.time())

    with col2:
        end = st.date_input(
            "To",
            value=st.session_state.end_date,
            max_value=datetime.now(),
            key='end_date_input'
        )
        if end != st.session_state.end_date.date():
            st.session_state.end_date = datetime.combine(end, datetime.min.time())

    # Comparison toggle (Feature 4)
    st.sidebar.markdown("---")
    st.session_state.compare_yoy = st.sidebar.checkbox(
        "Compare Year-over-Year",
        value=st.session_state.compare_yoy,
        help="Overlay previous year data on charts"
    )

    st.sidebar.markdown("---")

    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.session_state.data_fetch_times = {}
        st.rerun()

    # Cache status (Feature 8)
    render_cache_status()

    st.sidebar.markdown("---")

    # Data source status
    st.sidebar.markdown("### Data Sources")
    st.sidebar.markdown("""
    - CSO Ireland (StatBank)
    - ECB Statistical Warehouse
    - Yahoo Finance
    - PMI (cached data)
    - Consumer Sentiment (cached)
    """)

    st.sidebar.markdown("---")

    # About
    st.sidebar.markdown("### About")
    st.sidebar.markdown("""
    A dashboard tracking key Irish and European
    economic indicators with live data.

    **Last updated:** {}
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M')))

    return st.session_state.end_date


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application"""
    # Initialize
    init_session_state()
    read_url_params()
    apply_theme()

    # Render sidebar
    report_date = render_sidebar()

    # Update URL params
    update_url_params()

    # Title
    st.title("Economic Indicators")
    st.markdown(f"**{report_date.strftime('%d %B %Y')}**")

    st.markdown("---")

    # Fetch data with error handling
    data, errors = fetch_all_data()

    # Show errors if any (Feature 1)
    render_error_banner(errors)

    # Check and display alerts (Feature 5)
    alerts = check_alerts(data)
    if alerts:
        render_alerts(alerts)
        st.markdown("---")

    # Render key metrics
    render_key_metrics(data)

    st.markdown("---")

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Commentary", "📈 Charts", "🗓️ Heatmap", "📊 Data", "⬇️ Download"])

    with tab1:
        commentary = render_commentary(data)

    with tab2:
        render_charts(data)

    with tab3:
        render_heatmap_table(data)

    with tab4:
        render_data_tables(data)

    with tab5:
        render_download_section(data)

    # Footer
    st.markdown("---")
    st.markdown("*Irish Economic Indicators Dashboard*")


if __name__ == "__main__":
    main()
