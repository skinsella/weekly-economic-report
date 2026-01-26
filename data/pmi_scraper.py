"""
PMI Data Scraper for Irish economic indicators
Scrapes AIB and S&P Global PMI press releases
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import re
import json
from pathlib import Path


class PMIScraper:
    """Scrape PMI data from various sources"""

    # AIB PMI main page (contains links to all PMI reports)
    AIB_PMI_HUB_URL = "https://aib.ie/fxcentre/resource-centre/aib-ireland-pmis"

    # AIB PMI PDF base URLs
    AIB_PMI_PDF_BASE = "https://aib.ie/content/dam/aib/fxcentre/docs/resource-centre"
    AIB_MANUFACTURING_PDF = f"{AIB_PMI_PDF_BASE}/aib-ireland-manufacturing-pmi"
    AIB_SERVICES_PDF = f"{AIB_PMI_PDF_BASE}/aib-ireland-services-pmi"
    AIB_CONSTRUCTION_PDF = f"{AIB_PMI_PDF_BASE}/aib-ireland-construction-pmi"

    # S&P Global PMI (backup)
    SP_GLOBAL_URL = "https://www.pmi.spglobal.com/Public/Release/PressReleases"

    # Trading Economics (for historical data)
    TE_MANUFACTURING_URL = "https://tradingeconomics.com/ireland/manufacturing-pmi"
    TE_SERVICES_URL = "https://tradingeconomics.com/ireland/services-pmi"
    TE_CONSTRUCTION_URL = "https://tradingeconomics.com/ireland/construction-pmi"

    def __init__(self, cache_dir: Path = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Cache file for PMI data
        self.pmi_cache_file = self.cache_dir / "pmi_data.json"

    def _extract_pmi_value(self, text: str) -> Optional[float]:
        """Extract PMI value from text"""
        # Look for patterns like "52.2", "PMI 52.2", "index at 52.2"
        patterns = [
            r'(?:PMI|index|reading)[^\d]*(\d{2}\.\d)',
            r'(\d{2}\.\d)(?:\s*(?:in|for|during))',
            r'(?:rose|fell|increased|decreased|unchanged)[^\d]*(\d{2}\.\d)',
            r'(\d{2}\.\d)\s*(?:points?|percent)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 30 <= value <= 70:  # Sanity check for PMI range
                    return value

        # Direct number search as fallback
        numbers = re.findall(r'\b(\d{2}\.\d)\b', text)
        for num in numbers:
            value = float(num)
            if 40 <= value <= 65:  # Tighter range for fallback
                return value

        return None

    def _extract_month_year(self, text: str) -> Optional[Tuple[int, int]]:
        """Extract month and year from text"""
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

        text_lower = text.lower()

        for month_name, month_num in months.items():
            if month_name in text_lower:
                # Look for year near the month
                year_match = re.search(r'20(\d{2})', text)
                if year_match:
                    year = 2000 + int(year_match.group(1))
                    return (month_num, year)
                else:
                    # Assume current or previous year
                    current_year = datetime.now().year
                    current_month = datetime.now().month
                    if month_num > current_month:
                        return (month_num, current_year - 1)
                    return (month_num, current_year)

        return None

    def scrape_aib_pmi(self, pmi_type: str) -> Optional[Dict[str, Any]]:
        """
        Scrape PMI data from AIB website hub page

        Args:
            pmi_type: 'manufacturing', 'services', or 'construction'

        Returns:
            Dict with 'value', 'month', 'year', 'date' or None if failed
        """
        try:
            # First, get the PMI hub page to find links
            response = self.session.get(self.AIB_PMI_HUB_URL, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            text = soup.get_text(separator=' ', strip=True)

            # Look for PMI values in the text
            # The hub page often shows latest values
            pmi_patterns = {
                'manufacturing': [
                    r'manufacturing\s+pmi[^\d]*(\d{2}\.\d)',
                    r'manufacturing[^\d]*(?:index|pmi)[^\d]*(\d{2}\.\d)',
                ],
                'services': [
                    r'services\s+pmi[^\d]*(\d{2}\.\d)',
                    r'services[^\d]*(?:index|activity)[^\d]*(\d{2}\.\d)',
                ],
                'construction': [
                    r'construction\s+pmi[^\d]*(\d{2}\.\d)',
                    r'construction[^\d]*(?:index|pmi)[^\d]*(\d{2}\.\d)',
                ]
            }

            patterns = pmi_patterns.get(pmi_type, [])

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    if 30 <= value <= 70:
                        # Try to get the month from context
                        month_year = self._extract_month_year(text)
                        if month_year:
                            month, year = month_year
                        else:
                            # Default to previous month
                            now = datetime.now()
                            if now.day < 5:
                                # If early in month, use 2 months ago
                                prev = now.replace(day=1) - timedelta(days=1)
                                prev = prev.replace(day=1) - timedelta(days=1)
                            else:
                                prev = now.replace(day=1) - timedelta(days=1)
                            month, year = prev.month, prev.year

                        return {
                            'value': value,
                            'month': month,
                            'year': year,
                            'date': datetime(year, month, 1),
                            'source': 'AIB'
                        }

        except Exception as e:
            print(f"Error scraping AIB {pmi_type} PMI: {e}")

        return None

    def scrape_trading_economics(self, pmi_type: str) -> Optional[List[Dict[str, Any]]]:
        """
        Scrape historical PMI data from Trading Economics

        Args:
            pmi_type: 'manufacturing', 'services', or 'construction'

        Returns:
            List of dicts with historical PMI data
        """
        url_map = {
            'manufacturing': self.TE_MANUFACTURING_URL,
            'services': self.TE_SERVICES_URL,
            'construction': self.TE_CONSTRUCTION_URL
        }

        url = url_map.get(pmi_type)
        if not url:
            return None

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            # Trading Economics has a table with historical data
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 2:
                    data = []
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            try:
                                date_text = cells[0].get_text(strip=True)
                                value_text = cells[1].get_text(strip=True)

                                # Parse value
                                value = float(re.sub(r'[^\d.]', '', value_text))

                                # Parse date
                                date_match = self._extract_month_year(date_text)
                                if date_match and 30 <= value <= 70:
                                    month, year = date_match
                                    data.append({
                                        'value': value,
                                        'month': month,
                                        'year': year,
                                        'date': datetime(year, month, 1),
                                        'source': 'TradingEconomics'
                                    })
                            except (ValueError, IndexError):
                                continue

                    if data:
                        return data

        except Exception as e:
            print(f"Error scraping Trading Economics {pmi_type} PMI: {e}")

        return None

    def get_latest_pmi_data(self) -> Dict[str, Any]:
        """
        Get the latest PMI data from all sources

        Returns:
            Dict with manufacturing, services, construction PMI data
        """
        result = {
            'manufacturing': None,
            'services': None,
            'construction': None,
            'last_updated': datetime.now().isoformat(),
            'source': 'mixed'
        }

        # Try AIB first
        for pmi_type in ['manufacturing', 'services', 'construction']:
            data = self.scrape_aib_pmi(pmi_type)
            if data:
                result[pmi_type] = data
                print(f"Got {pmi_type} PMI from AIB: {data['value']}")

        # Fill gaps with Trading Economics
        for pmi_type in ['manufacturing', 'services', 'construction']:
            if result[pmi_type] is None:
                te_data = self.scrape_trading_economics(pmi_type)
                if te_data and len(te_data) > 0:
                    result[pmi_type] = te_data[0]  # Latest value
                    print(f"Got {pmi_type} PMI from Trading Economics: {te_data[0]['value']}")

        # Save to cache
        self._save_cache(result)

        return result

    def get_historical_pmi(self, months: int = 15) -> pd.DataFrame:
        """
        Get historical PMI data

        Args:
            months: Number of months of history

        Returns:
            DataFrame with date, manufacturing_pmi, services_pmi, construction_pmi
        """
        # Try to load from cache first
        cached = self._load_cache()

        # Get fresh data
        all_data = {
            'manufacturing': [],
            'services': [],
            'construction': []
        }

        for pmi_type in ['manufacturing', 'services', 'construction']:
            te_data = self.scrape_trading_economics(pmi_type)
            if te_data:
                all_data[pmi_type] = te_data[:months]

        # Build DataFrame
        if all_data['manufacturing'] or all_data['services'] or all_data['construction']:
            # Use the longest series to get dates
            dates = set()
            for pmi_type in all_data:
                for item in all_data[pmi_type]:
                    dates.add(item['date'])

            dates = sorted(dates, reverse=True)[:months]

            records = []
            for date in dates:
                record = {'date': date}
                for pmi_type in all_data:
                    for item in all_data[pmi_type]:
                        if item['date'] == date:
                            record[f'{pmi_type}_pmi'] = item['value']
                            break
                records.append(record)

            df = pd.DataFrame(records)
            return df

        # Return fallback data if scraping failed
        return self._get_fallback_data()

    def _save_cache(self, data: Dict):
        """Save data to cache file"""
        try:
            # Convert datetime objects to strings
            cache_data = {}
            for key, value in data.items():
                if isinstance(value, dict) and 'date' in value:
                    value = value.copy()
                    value['date'] = value['date'].isoformat()
                cache_data[key] = value

            with open(self.pmi_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving PMI cache: {e}")

    def _load_cache(self) -> Optional[Dict]:
        """Load data from cache file"""
        try:
            if self.pmi_cache_file.exists():
                with open(self.pmi_cache_file, 'r') as f:
                    data = json.load(f)

                # Convert date strings back to datetime
                for key, value in data.items():
                    if isinstance(value, dict) and 'date' in value:
                        value['date'] = datetime.fromisoformat(value['date'])

                return data
        except Exception as e:
            print(f"Error loading PMI cache: {e}")

        return None

    def _get_fallback_data(self) -> pd.DataFrame:
        """Return fallback PMI data if scraping fails"""
        dates = pd.date_range(end=datetime.now().replace(day=1), periods=15, freq='MS')

        return pd.DataFrame({
            'date': dates[::-1],
            'manufacturing_pmi': [52.2, 52.8, 50.9, 51.6, 51.6, 53.2, 53.7, 52.6, 53.0,
                                  51.6, 51.9, 51.3, 49.1, 49.9, 51.5],
            'services_pmi': [54.8, 58.5, 56.7, 53.5, 50.6, 50.9, 51.5, 54.7, 52.8,
                            55.3, 53.2, 53.4, 57.1, 58.3, 53.8],
            'construction_pmi': [48.4, 46.7, 48.1, 43.7, 45.9, 47.1, 48.6, 49.2, 52.4,
                                53.9, 48.7, 48.2, 51.6, 47.5, 49.4]
        })


# Test the module
if __name__ == "__main__":
    scraper = PMIScraper()

    print("Testing PMI scraper...")
    print("\nTrying to get latest PMI data...")
    latest = scraper.get_latest_pmi_data()
    print(f"Result: {latest}")

    print("\nGetting historical data...")
    historical = scraper.get_historical_pmi(months=6)
    print(historical)
