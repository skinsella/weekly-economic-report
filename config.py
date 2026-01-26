"""
Configuration for Weekly Economic Indicators Report
"""
from datetime import datetime, timedelta
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / "cache"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = PROJECT_ROOT / "data"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Cache settings (in seconds)
CACHE_TTL = {
    "cso": 3600 * 6,      # 6 hours for CSO data
    "ecb": 3600 * 1,      # 1 hour for ECB exchange rates
    "markets": 900,        # 15 minutes for market data
    "bonds": 1800,         # 30 minutes for bond yields
}

# CSO StatBank table codes
CSO_TABLES = {
    "live_register": "LRM02",          # Monthly Live Register
    "cpi": "CPM01",                     # Consumer Price Index
    "construction_costs": "BHQ06",      # Construction Cost Index
}

# ECB Data Portal series keys
ECB_SERIES = {
    "eur_gbp": "EXR.D.GBP.EUR.SP00.A",
    "eur_usd": "EXR.D.USD.EUR.SP00.A",
}

# Yahoo Finance tickers
YAHOO_TICKERS = {
    "brent_crude": "BZ=F",
    "natural_gas_uk": "NG=F",  # US natural gas as proxy
    "ireland_10y": "^TNX",      # Using US 10Y as fallback
}

# Investing.com / alternative bond data
BOND_DATA = {
    "ireland_10y_url": "https://www.worldgovernmentbonds.com/country/ireland/",
    "germany_10y_url": "https://www.worldgovernmentbonds.com/country/germany/",
}

# PMI thresholds for heatmap colouring
PMI_THRESHOLDS = {
    "expansion": 50.0,      # Above 50 = expansion (green)
    "strong": 55.0,         # Strong expansion
    "contraction": 50.0,    # Below 50 = contraction (red)
    "severe": 45.0,         # Severe contraction
}

# Heatmap colour scheme
HEATMAP_COLORS = {
    "good": "#c6efce",      # Light green
    "neutral": "#ffeb9c",   # Light yellow
    "bad": "#ffc7ce",       # Light red
}

# Report settings
REPORT_TITLE = "Economic Indicators"
REPORT_AUTHOR = "Irish Economic Indicators Dashboard"

# Alert thresholds
ALERT_THRESHOLDS = {
    "pmi_contraction": 50.0,        # Below 50 = contraction warning
    "pmi_severe": 45.0,             # Below 45 = severe contraction
    "inflation_target": 2.0,        # ECB target
    "inflation_warning": 3.0,       # Above 3% = warning
    "inflation_critical": 5.0,      # Above 5% = critical
    "bond_spread_warning": 0.35,    # Spread above 35bps = warning
    "bond_spread_critical": 0.50,   # Spread above 50bps = critical
    "sentiment_warning": 55.0,      # Below 55 = pessimistic
    "sentiment_critical": 45.0,     # Below 45 = very pessimistic
}

# Theme settings
THEMES = {
    "light": {
        "background": "#FFFFFF",
        "secondary_background": "#F5F5F5",
        "text": "#333333",
        "card_background": "#FFFFFF",
        "border": "#E0E0E0",
        "primary": "#2E7D32",
        "chart_background": "#FFFFFF",
        "chart_grid": "#E0E0E0",
    },
    "dark": {
        "background": "#1E1E1E",
        "secondary_background": "#2D2D2D",
        "text": "#E0E0E0",
        "card_background": "#2D2D2D",
        "border": "#444444",
        "primary": "#4CAF50",
        "chart_background": "#1E1E1E",
        "chart_grid": "#444444",
    }
}

# Date range presets (in days)
DATE_PRESETS = {
    "3 months": 90,
    "6 months": 180,
    "1 year": 365,
    "2 years": 730,
}

# Date formatting
DATE_FORMAT = "%d %B %Y"
MONTH_FORMAT = "%b-%y"

def get_report_date():
    """Get the report date (most recent Saturday or today if Saturday)"""
    today = datetime.now()
    days_since_saturday = (today.weekday() + 2) % 7
    if days_since_saturday == 0:
        return today
    return today - timedelta(days=days_since_saturday)

def get_latest_data_month():
    """Get the latest month for which we expect data (usually previous month)"""
    today = datetime.now()
    # Most data is released with 1-month lag
    if today.day < 15:
        # Before mid-month, use 2 months ago
        first_of_month = today.replace(day=1)
        return (first_of_month - timedelta(days=1)).replace(day=1) - timedelta(days=1)
    else:
        # After mid-month, use previous month
        first_of_month = today.replace(day=1)
        return first_of_month - timedelta(days=1)
