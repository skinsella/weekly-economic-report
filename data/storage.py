"""
Data caching and storage utilities
"""
import json
import pickle
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Callable
import hashlib


class DataCache:
    """Simple file-based cache for data"""

    def __init__(self, cache_dir: Path = None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, key: str, extension: str = 'pkl') -> Path:
        """Generate cache file path from key"""
        safe_key = hashlib.md5(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{safe_key}.{extension}"

    def get(self, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
        """
        Get cached data if it exists and is not expired

        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds before cache is considered stale

        Returns:
            Cached data or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        # Check age
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = (datetime.now() - mtime).total_seconds()

        if age > max_age_seconds:
            return None

        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error reading cache {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> bool:
        """
        Store data in cache

        Args:
            key: Cache key
            data: Data to cache (must be picklable)

        Returns:
            True if successful
        """
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"Error writing cache {key}: {e}")
            return False

    def get_or_fetch(self, key: str, fetch_fn: Callable, max_age_seconds: int = 3600) -> Any:
        """
        Get from cache or fetch and cache

        Args:
            key: Cache key
            fetch_fn: Function to call if cache miss
            max_age_seconds: Maximum cache age

        Returns:
            Data from cache or fetched
        """
        cached = self.get(key, max_age_seconds)
        if cached is not None:
            return cached

        data = fetch_fn()
        if data is not None:
            self.set(key, data)
        return data

    def clear(self, key: str = None):
        """
        Clear cache

        Args:
            key: Specific key to clear, or None to clear all
        """
        if key:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
        else:
            for f in self.cache_dir.glob('*.pkl'):
                f.unlink()

    def get_cache_info(self) -> dict:
        """Get information about cached items"""
        info = {
            'items': [],
            'total_size': 0
        }

        for f in self.cache_dir.glob('*.pkl'):
            size = f.stat().st_size
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            age = (datetime.now() - mtime).total_seconds()

            info['items'].append({
                'file': f.name,
                'size': size,
                'age_seconds': age,
                'modified': mtime.isoformat()
            })
            info['total_size'] += size

        return info


class DataStore:
    """
    Persistent storage for historical economic data
    Uses a simple JSON-based storage with pandas DataFrames
    """

    def __init__(self, store_dir: Path = None):
        if store_dir is None:
            store_dir = Path(__file__).parent.parent / "data_store"
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(exist_ok=True)

    def save_dataframe(self, name: str, df: pd.DataFrame) -> bool:
        """Save a DataFrame to storage"""
        try:
            path = self.store_dir / f"{name}.parquet"
            df.to_parquet(path, index=False)
            return True
        except Exception as e:
            print(f"Error saving DataFrame {name}: {e}")
            # Fallback to CSV
            try:
                path = self.store_dir / f"{name}.csv"
                df.to_csv(path, index=False)
                return True
            except:
                return False

    def load_dataframe(self, name: str) -> Optional[pd.DataFrame]:
        """Load a DataFrame from storage"""
        parquet_path = self.store_dir / f"{name}.parquet"
        csv_path = self.store_dir / f"{name}.csv"

        try:
            if parquet_path.exists():
                return pd.read_parquet(parquet_path)
            elif csv_path.exists():
                return pd.read_csv(csv_path)
        except Exception as e:
            print(f"Error loading DataFrame {name}: {e}")

        return None

    def append_dataframe(self, name: str, new_data: pd.DataFrame,
                         date_column: str = 'date') -> bool:
        """Append new data to existing DataFrame, avoiding duplicates"""
        existing = self.load_dataframe(name)

        if existing is None:
            return self.save_dataframe(name, new_data)

        try:
            # Ensure date columns are datetime
            if date_column in existing.columns:
                existing[date_column] = pd.to_datetime(existing[date_column])
            if date_column in new_data.columns:
                new_data[date_column] = pd.to_datetime(new_data[date_column])

            # Combine and remove duplicates
            combined = pd.concat([existing, new_data], ignore_index=True)
            if date_column in combined.columns:
                combined = combined.drop_duplicates(subset=[date_column], keep='last')
                combined = combined.sort_values(date_column, ascending=False)

            return self.save_dataframe(name, combined)

        except Exception as e:
            print(f"Error appending to DataFrame {name}: {e}")
            return False

    def list_datasets(self) -> list:
        """List all stored datasets"""
        datasets = []
        for f in self.store_dir.glob('*.*'):
            if f.suffix in ['.parquet', '.csv']:
                datasets.append(f.stem)
        return list(set(datasets))


# Test
if __name__ == "__main__":
    # Test cache
    cache = DataCache()

    print("Testing cache...")
    cache.set('test_key', {'value': 42, 'timestamp': datetime.now().isoformat()})
    result = cache.get('test_key')
    print(f"Cached result: {result}")

    print("\nCache info:")
    print(cache.get_cache_info())

    # Test store
    store = DataStore()

    print("\nTesting store...")
    test_df = pd.DataFrame({
        'date': pd.date_range('2025-01-01', periods=5),
        'value': [1, 2, 3, 4, 5]
    })
    store.save_dataframe('test_data', test_df)

    loaded = store.load_dataframe('test_data')
    print(f"Loaded DataFrame:\n{loaded}")

    print(f"\nDatasets: {store.list_datasets()}")
