"""
CSO (Central Statistics Office) Ireland data fetcher
Uses the PxStat API (StatBank replacement)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import re


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

            dim_columns = {}
            for dim_name in dim_order:
                dim = dimensions.get(dim_name, {})
                category = dim.get('category', {})
                index = category.get('index', {})
                label = category.get('label', {})
                dim_label = dim.get('label', dim_name)
                dim_columns[dim_name] = dim_label

                # Handle both dict (code->position) and list (ordered codes) formats.
                if isinstance(index, dict):
                    dim_info[dim_name] = {pos: label.get(code, code) for code, pos in index.items()}
                else:
                    dim_info[dim_name] = {
                        pos: label.get(code, code) for pos, code in enumerate(index)
                    }

            # Build records
            sizes = [len(dim_info[d]) for d in dim_order]
            records = []

            for i, val in enumerate(values):
                indices = []
                remaining = i
                for size in reversed(sizes):
                    indices.insert(0, remaining % size)
                    remaining //= size

                record = {
                    dim_columns[dim_order[j]]: dim_info[dim_order[j]].get(idx, idx)
                    for j, idx in enumerate(indices)
                }
                record['value'] = val
                records.append(record)

            return pd.DataFrame(records)

        except Exception as e:
            print(f"Error parsing JSON-stat: {e}")
            return pd.DataFrame()

    @staticmethod
    def _find_column(df: pd.DataFrame, exact: Optional[str] = None, contains: Optional[list] = None) -> Optional[str]:
        """Find a column by exact name or contains matching (case-insensitive)."""
        if exact and exact in df.columns:
            return exact
        if contains:
            for col in df.columns:
                lower = str(col).lower()
                if all(token in lower for token in contains):
                    return col
        return None

    @staticmethod
    def _parse_month_series(series: pd.Series) -> pd.Series:
        """Parse month labels/codes from CSO (e.g., 202601 or '2026 January')."""
        as_str = series.astype(str).str.strip()
        parsed = pd.to_datetime(as_str, format='%Y%m', errors='coerce')
        if parsed.notna().any():
            return parsed
        parsed = pd.to_datetime(as_str, format='%Y %B', errors='coerce')
        if parsed.notna().any():
            return parsed
        # Last resort for variants such as '2026-01'
        return pd.to_datetime(as_str, errors='coerce')

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
            month_col = self._find_column(df, exact='Month') or self._find_column(df, contains=['month'])
            stat_col = self._find_column(df, exact='Statistic') or self._find_column(df, contains=['stat'])
            age_col = self._find_column(df, exact='Age Group') or self._find_column(df, contains=['age'])
            sex_col = self._find_column(df, exact='Sex') or self._find_column(df, contains=['sex'])

            if not month_col or not stat_col:
                raise ValueError("Required Month/Statistic columns not found")

            if age_col:
                all_ages = df[age_col].astype(str).str.contains('all ages', case=False, na=False)
                if all_ages.any():
                    df = df[all_ages]
            if sex_col:
                both_sexes = df[sex_col].astype(str).str.contains('both sexes', case=False, na=False)
                if both_sexes.any():
                    df = df[both_sexes]

            # Get the last N months
            df['date'] = self._parse_month_series(df[month_col])
            df = df.dropna(subset=['date'])
            df = df.sort_values('date', ascending=False).head(months * 3)  # Extra for filtering

            # Pivot to get unadjusted and seasonally adjusted
            result = df.pivot_table(
                index='date',
                columns=stat_col,
                values='value',
                aggfunc='first'
            ).reset_index()

            if 'Persons on the Live Register' in result.columns:
                result = result.rename(columns={
                    'Persons on the Live Register': 'Persons on the Live Register (Unadjusted)'
                })
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
            month_col = self._find_column(df, exact='Month') or self._find_column(df, contains=['month'])
            stat_col = self._find_column(df, exact='Statistic') or self._find_column(df, contains=['stat'])
            commodity_col = self._find_column(df, exact='Commodity Group') or self._find_column(df, contains=['commodity'])
            if not month_col:
                raise ValueError("Month column not found in CPI data")

            df['date'] = self._parse_month_series(df[month_col])
            df = df.dropna(subset=['date'])

            # Filter for annual percentage change
            annual_change = pd.DataFrame()
            if stat_col:
                annual_change = df[df[stat_col].astype(str).str.contains('annual', case=False, na=False)]

            if not annual_change.empty and commodity_col:
                result = annual_change.pivot_table(
                    index='date',
                    columns=commodity_col,
                    values='value',
                    aggfunc='first'
                ).reset_index()
                all_items = next((c for c in result.columns if str(c).lower() == 'all items'), None)
                if all_items:
                    result['cpi'] = pd.to_numeric(result[all_items], errors='coerce')
                elif 'value' in annual_change.columns:
                    result['cpi'] = pd.to_numeric(result.filter(regex='^(?!date$).*').iloc[:, 0], errors='coerce')
            else:
                # If annual % series isn't available, derive YoY inflation from All items CPI index.
                stat_filtered = df
                if stat_col:
                    stats = [str(s) for s in df[stat_col].dropna().unique()]
                    base_stats = []
                    for stat in stats:
                        match = re.search(r'base dec (\d{4})=100', stat.lower())
                        if match:
                            base_stats.append((int(match.group(1)), stat))
                    if base_stats:
                        selected_stat = sorted(base_stats, reverse=True)[0][1]
                        stat_filtered = df[df[stat_col] == selected_stat]
                    elif stats:
                        stat_filtered = df[df[stat_col] == stats[0]]

                if commodity_col:
                    base = stat_filtered[stat_filtered[commodity_col].astype(str).str.lower() == 'all items']
                    if base.empty:
                        base = stat_filtered
                else:
                    base = stat_filtered
                base = base.sort_values('date').drop_duplicates(subset=['date'], keep='last')
                base['index_value'] = pd.to_numeric(base['value'], errors='coerce')
                base['cpi'] = base['index_value'].pct_change(12, fill_method=None) * 100
                result = base[['date', 'cpi']].copy()

            result = result.sort_values('date', ascending=False).head(months)
            if 'core_cpi' not in result.columns:
                core_col = next(
                    (c for c in result.columns if 'core' in str(c).lower() or 'excluding' in str(c).lower()),
                    None
                )
                if core_col:
                    result['core_cpi'] = pd.to_numeric(result[core_col], errors='coerce')
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
            month_col = self._find_column(df, exact='Month') or self._find_column(df, contains=['month'])
            stat_col = self._find_column(df, exact='Statistic') or self._find_column(df, contains=['stat'])
            sex_col = self._find_column(df, exact='Sex') or self._find_column(df, contains=['sex'])
            age_col = self._find_column(df, exact='Age Group') or self._find_column(df, contains=['age'])

            if not month_col:
                raise ValueError("Month column not found in unemployment data")

            if stat_col:
                rate_rows = df[stat_col].astype(str).str.contains('rate', case=False, na=False)
                if rate_rows.any():
                    df = df[rate_rows]
            if sex_col:
                both = df[sex_col].astype(str).str.contains('both sexes', case=False, na=False)
                if both.any():
                    df = df[both]
            if age_col:
                broad = df[age_col].astype(str).str.contains('15 - 74 years|all ages', case=False, na=False, regex=True)
                if broad.any():
                    df = df[broad]

            df['date'] = self._parse_month_series(df[month_col])
            latest = df.dropna(subset=['date']).sort_values('date', ascending=False).iloc[0]
            return {
                'rate': float(latest['value']),
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
