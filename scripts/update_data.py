#!/usr/bin/env python3
"""
Automated data update script for Weekly Economic Indicators
Run by GitHub Actions on schedule or manually

This script:
1. Fetches fresh data from all sources
2. Updates the cache files
3. Generates a data snapshot for the dashboard
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.cso import CSODataFetcher
from data.ecb import ECBDataFetcher
from data.markets import MarketDataFetcher
from data.pmi_scraper import PMIScraper
from data.storage import DataCache, DataStore


def log(message: str):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def update_cso_data(store: DataStore) -> dict:
    """Fetch and store CSO data"""
    log("Fetching CSO data...")
    fetcher = CSODataFetcher()
    results = {}

    try:
        # Live Register
        lr = fetcher.get_live_register(months=24)
        if not lr.empty:
            store.save_dataframe('live_register', lr)
            results['live_register'] = len(lr)
            log(f"  Live Register: {len(lr)} records")

        # CPI
        cpi = fetcher.get_cpi(months=24)
        if not cpi.empty:
            store.save_dataframe('cpi', cpi)
            results['cpi'] = len(cpi)
            log(f"  CPI: {len(cpi)} records")

        # Unemployment
        unemployment = fetcher.get_unemployment_rate()
        results['unemployment'] = unemployment
        log(f"  Unemployment rate: {unemployment.get('rate', 'N/A')}%")

    except Exception as e:
        log(f"  ERROR: {e}")
        results['error'] = str(e)

    return results


def update_ecb_data(store: DataStore) -> dict:
    """Fetch and store ECB data"""
    log("Fetching ECB exchange rate data...")
    fetcher = ECBDataFetcher()
    results = {}

    try:
        # Exchange rates
        rates = fetcher.get_exchange_rates(days=400)
        if not rates.empty:
            store.save_dataframe('exchange_rates', rates)
            results['exchange_rates'] = len(rates)
            log(f"  Exchange rates: {len(rates)} records")

        # Latest rates
        latest = fetcher.get_latest_rates()
        results['latest_rates'] = latest
        log(f"  Latest EUR/GBP: {latest.get('eur_gbp', 'N/A')}")
        log(f"  Latest EUR/USD: {latest.get('eur_usd', 'N/A')}")

        # Monthly averages
        monthly = fetcher.get_monthly_averages(months=15)
        if not monthly.empty:
            store.save_dataframe('monthly_exchange_rates', monthly)
            results['monthly_rates'] = len(monthly)

    except Exception as e:
        log(f"  ERROR: {e}")
        results['error'] = str(e)

    return results


def update_market_data(store: DataStore) -> dict:
    """Fetch and store market data"""
    log("Fetching market data...")
    fetcher = MarketDataFetcher()
    results = {}

    try:
        # Brent crude
        brent = fetcher.get_brent_crude(days=365)
        if not brent.empty:
            store.save_dataframe('brent_crude', brent)
            results['brent'] = len(brent)
            log(f"  Brent crude: {len(brent)} records")

        # Natural gas
        gas = fetcher.get_natural_gas(days=365)
        if not gas.empty:
            store.save_dataframe('natural_gas', gas)
            results['gas'] = len(gas)
            log(f"  Natural gas: {len(gas)} records")

        # Commodities summary
        commodities = fetcher.get_latest_commodities()
        results['commodities'] = commodities
        log(f"  Brent price: ${commodities.get('brent', {}).get('price', 'N/A')}")

        # Bond yields
        bonds = fetcher.get_bond_yields()
        results['bonds'] = bonds
        log(f"  Ireland 10Y: {bonds.get('ireland_10y', 'N/A')}%")
        log(f"  Spread: {bonds.get('spread', 'N/A')}")

        # Monthly bonds
        monthly_bonds = fetcher.get_monthly_bond_data(months=15)
        if not monthly_bonds.empty:
            store.save_dataframe('monthly_bonds', monthly_bonds)
            results['monthly_bonds'] = len(monthly_bonds)

        # Consumer sentiment
        sentiment = fetcher.get_consumer_sentiment()
        if not sentiment.empty:
            store.save_dataframe('consumer_sentiment', sentiment)
            results['sentiment'] = len(sentiment)
            log(f"  Consumer sentiment: {len(sentiment)} records")

        # Container costs
        container = fetcher.get_container_costs()
        results['container'] = container
        log(f"  Container cost: ${container.get('current', 'N/A')}")

        # Insolvency
        insolvency = fetcher.get_insolvency_data()
        if not insolvency.empty:
            store.save_dataframe('insolvency', insolvency)
            results['insolvency'] = len(insolvency)

    except Exception as e:
        log(f"  ERROR: {e}")
        results['error'] = str(e)

    return results


def update_pmi_data(store: DataStore) -> dict:
    """Fetch and store PMI data via scraping"""
    log("Scraping PMI data...")
    scraper = PMIScraper()
    results = {}

    try:
        # Latest PMI
        latest = scraper.get_latest_pmi_data()
        results['latest_pmi'] = {
            'manufacturing': latest.get('manufacturing', {}).get('value') if latest.get('manufacturing') else None,
            'services': latest.get('services', {}).get('value') if latest.get('services') else None,
            'construction': latest.get('construction', {}).get('value') if latest.get('construction') else None,
        }

        for pmi_type in ['manufacturing', 'services', 'construction']:
            value = results['latest_pmi'].get(pmi_type)
            source = latest.get(pmi_type, {}).get('source', 'unknown') if latest.get(pmi_type) else 'N/A'
            log(f"  {pmi_type.capitalize()} PMI: {value} (source: {source})")

        # Historical PMI
        historical = scraper.get_historical_pmi(months=15)
        if not historical.empty:
            store.save_dataframe('pmi_data', historical)
            results['pmi_records'] = len(historical)
            log(f"  Historical PMI: {len(historical)} records")

    except Exception as e:
        log(f"  ERROR: {e}")
        results['error'] = str(e)

    return results


def generate_snapshot(results: dict, cache_dir: Path):
    """Generate a JSON snapshot of the update results"""
    snapshot = {
        'updated_at': datetime.now().isoformat(),
        'results': results,
        'status': 'success' if not any('error' in r for r in results.values() if isinstance(r, dict)) else 'partial'
    }

    snapshot_file = cache_dir / 'last_update.json'
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)

    log(f"Snapshot saved to {snapshot_file}")


def main():
    """Main update function"""
    log("=" * 60)
    log("Weekly Economic Indicators - Data Update")
    log("=" * 60)

    # Check for force refresh flag
    force_refresh = os.environ.get('FORCE_REFRESH', 'false').lower() == 'true'
    if force_refresh:
        log("Force refresh enabled - clearing caches")

    # Initialize storage
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / 'cache'
    data_store_dir = project_root / 'data_store'

    cache_dir.mkdir(exist_ok=True)
    data_store_dir.mkdir(exist_ok=True)

    store = DataStore(data_store_dir)

    # Clear cache if force refresh
    if force_refresh:
        cache = DataCache(cache_dir)
        cache.clear()

    # Update all data sources
    results = {}

    results['cso'] = update_cso_data(store)
    results['ecb'] = update_ecb_data(store)
    results['market'] = update_market_data(store)
    results['pmi'] = update_pmi_data(store)

    # Generate snapshot
    generate_snapshot(results, cache_dir)

    log("=" * 60)
    log("Update complete!")
    log("=" * 60)

    # Return exit code based on results
    has_errors = any(
        'error' in r for r in results.values() if isinstance(r, dict)
    )

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
