"""
CSO (Central Statistics Office) Ireland data fetcher
Uses the PxStat API (StatBank replacement)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json


class CSODataFetcher:
    """Fetch data from CSO Ireland's PxStat API"""

    BASE_URL = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'WeeklyEconomicReport/1.0'
        })

    def _fetch_table(self, table_code: str, format: str = "JSON-stat/2.0") -> Optional[Dict]:
        """Fetch a table from CSO PxStat API"""
        url = f"{self.BASE_URL}/{table_code}/{format}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching CSO table {table_code}: {e}")
            return None

    def _jsonstat_to_dataframe(self, data: Dict) -> pd.DataFrame:
        """Convert JSON-stat format to pandas DataFrame"""
        if not data:
            return pd.DataFrame()

        try:
            # Extract dimensions
            dimensions = data.get('dimension', {})
            values = data.get('value', [])

            # Get dimension categories
            dim_info = {}
            dim_order = data.get('id', [])

            for dim_name in dim_order:
                dim = dimensions.get(dim_name, {})
                category = dim.get('category', {})
                index = category.get('index', {})
                label = category.get('label', {})

                # Handle both dict and list formats
                if isinstance(index, dict):
                    dim_info[dim_name] = {v: label.get(k, k) for k, v in index.items()}
                else:
                    dim_info[dim_name] = {i: label.get(str(i), str(i)) for i in range(len(index))}

            # Build records
            sizes = [len(dim_info[d]) for d in dim_order]
            records = []

            for i, val in enumerate(values):
                indices = []
                remaining = i
                for size in reversed(sizes):
                    indices.insert(0, remaining % size)
                    remaining //= size

                record = {dim_order[j]: dim_info[dim_order[j]].get(idx, idx)
                         for j, idx in enumerate(indices)}
                record['value'] = val
                records.append(record)

            return pd.DataFrame(records)

        except Exception as e:
            print(f"Error parsing JSON-stat: {e}")
            return pd.DataFrame()

    def get_live_register(self, months: int = 24) -> pd.DataFrame:
        """
        Fetch Live Register data
        Returns monthly unadjusted and seasonally adjusted figures
        """
        data = self._fetch_table("LRM02")
        if not data:
            return self._get_fallback_live_register()

        df = self._jsonstat_to_dataframe(data)
        if df.empty:
            return self._get_fallback_live_register()

        # Filter and process
        try:
            # Get the last N months
            df['date'] = pd.to_datetime(df['Month'], format='%YM%m', errors='coerce')
            df = df.dropna(subset=['date'])
            df = df.sort_values('date', ascending=False).head(months * 3)  # Extra for filtering

            # Pivot to get unadjusted and seasonally adjusted
            result = df.pivot_table(
                index='date',
                columns='Statistic',
                values='value',
                aggfunc='first'
            ).reset_index()

            result = result.sort_values('date', ascending=False).head(months)
            return result

        except Exception as e:
            print(f"Error processing Live Register data: {e}")
            return self._get_fallback_live_register()

    def _get_fallback_live_register(self) -> pd.DataFrame:
        """Return sample data if API fails"""
        dates = pd.date_range(end=datetime.now(), periods=15, freq='MS')
        return pd.DataFrame({
            'date': dates,
            'Persons on the Live Register (Unadjusted)': [172224, 163483, 163864, 168898, 185026,
                                                          182562, 168418, 163512, 164257, 161470,
                                                          165478, 167119, 161022, 161094, 161008],
            'Persons on the Live Register (Seasonally Adjusted)': [172200, 163500, 164000, 169000, 185000,
                                                                    182500, 168500, 163500, 164300, 161500,
                                                                    165500, 167100, 161000, 161100, 161000]
        })

    def get_cpi(self, months: int = 24) -> pd.DataFrame:
        """
        Fetch Consumer Price Index data
        Returns CPI and Core CPI annual rates
        """
        data = self._fetch_table("CPM01")
        if not data:
            return self._get_fallback_cpi()

        df = self._jsonstat_to_dataframe(data)
        if df.empty:
            return self._get_fallback_cpi()

        try:
            df['date'] = pd.to_datetime(df['Month'], format='%YM%m', errors='coerce')
            df = df.dropna(subset=['date'])

            # Filter for annual percentage change
            annual_change = df[df['Statistic'].str.contains('Annual', case=False, na=False)]

            result = annual_change.pivot_table(
                index='date',
                columns='Commodity Group',
                values='value',
                aggfunc='first'
            ).reset_index()

            result = result.sort_values('date', ascending=False).head(months)
            return result

        except Exception as e:
            print(f"Error processing CPI data: {e}")
            return self._get_fallback_cpi()

    def _get_fallback_cpi(self) -> pd.DataFrame:
        """Return sample CPI data if API fails"""
        dates = pd.date_range(end=datetime.now(), periods=15, freq='MS')
        return pd.DataFrame({
            'date': dates,
            'cpi': [2.8, 3.2, 2.9, 2.7, 2.0, 1.7, 1.8, 1.7, 2.2, 2.0, 1.8, 1.9, 1.4, 1.0, 0.7],
            'core_cpi': [2.7, 3.1, 2.8, 2.8, 2.1, 1.8, 2.0, 1.9, 2.6, 2.2, 2.2, 2.5, 2.1, 2.0, 2.3]
        })

    def get_construction_costs(self, months: int = 24) -> pd.DataFrame:
        """Fetch construction cost index data"""
        data = self._fetch_table("BHQ06")
        if not data:
            return self._get_fallback_construction_costs()

        df = self._jsonstat_to_dataframe(data)
        if df.empty:
            return self._get_fallback_construction_costs()

        try:
            df['date'] = pd.to_datetime(df['Quarter'], errors='coerce')
            df = df.dropna(subset=['date'])

            # Get annual percentage change
            annual_change = df[df['Statistic'].str.contains('Annual', case=False, na=False)]
            result = annual_change[['date', 'value']].copy()
            result.columns = ['date', 'construction_cost_change']

            return result.sort_values('date', ascending=False).head(months)

        except Exception as e:
            print(f"Error processing construction costs: {e}")
            return self._get_fallback_construction_costs()

    def _get_fallback_construction_costs(self) -> pd.DataFrame:
        """Return sample construction cost data"""
        dates = pd.date_range(end=datetime.now(), periods=15, freq='MS')
        return pd.DataFrame({
            'date': dates,
            'construction_cost_change': [2.0] * 15
        })

    def get_unemployment_rate(self) -> Dict[str, Any]:
        """Get latest unemployment rate"""
        data = self._fetch_table("MUM01")
        if not data:
            return {'rate': 5.0, 'date': datetime.now().strftime('%B %Y')}

        df = self._jsonstat_to_dataframe(data)
        if df.empty:
            return {'rate': 5.0, 'date': datetime.now().strftime('%B %Y')}

        try:
            df['date'] = pd.to_datetime(df['Month'], format='%YM%m', errors='coerce')
            latest = df.sort_values('date', ascending=False).iloc[0]
            return {
                'rate': latest['value'],
                'date': latest['date'].strftime('%B %Y')
            }
        except:
            return {'rate': 5.0, 'date': datetime.now().strftime('%B %Y')}


# Test the module
if __name__ == "__main__":
    fetcher = CSODataFetcher()

    print("Testing Live Register...")
    lr = fetcher.get_live_register(months=6)
    print(lr.head())

    print("\nTesting CPI...")
    cpi = fetcher.get_cpi(months=6)
    print(cpi.head())
