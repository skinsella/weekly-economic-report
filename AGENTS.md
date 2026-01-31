# Repository Guidelines

## Project Structure & Module Organization
`app.py` hosts the Streamlit UI and pulls shared constants from `config.py`. Source adapters in `data/` encapsulate external APIs or scrapers (CSO, ECB, Yahoo Finance, PMI) and cache results in `cache/` and `data_store/`. Charting and PDF assembly live in `reports/`, while automation sticks to `scripts/update_data.py` and helper utilities within `scripts/`.

## Build, Test, and Development Commands
Standard workflow:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py  # or ./run.sh for the same effect
```
Refresh datasets outside the UI with `python scripts/update_data.py`; add `FORCE_REFRESH=true` to backfill every indicator. When developing a single source, run it as a module (e.g., `python -m data.cso`) and inspect the cached parquet/JSON produced.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, snake_case functions, and uppercase constants (see `config.py`). Modules should expose clear entry points such as `fetch_*` or `build_*`, mirroring files like `data/markets.py` and `reports/charts.py`. Keep selectors, URLs, and column schemas close to the top of each file with brief comments describing assumptions. Favor vectorized pandas operations, return typed DataFrames (`-> pd.DataFrame`), and avoid duplicating literal strings—import them from shared helpers.

## Testing Guidelines
The repository currently relies on manual testing. Treat `python scripts/update_data.py` as the smoke test and verify the resulting timestamps in `cache/last_update.json`. Launch `streamlit run app.py` before submitting to confirm charts, tables, and PDF exports rebuild without warnings. When modifying scrapers, attach sample payloads or describe observed HTML changes in the PR so reviewers can reason about breakpoints.

## Commit & Pull Request Guidelines
Recent history shows concise, imperative subjects (`Add 10 dashboard improvements`, `Remove IGEES/DOT references from dashboard`). Continue that style, grouping related changes per commit and describing affected indicators. Pull requests should summarize the feature or fix, call out new environment variables, list the commands you ran, and include screenshots or paths to refreshed outputs when visuals change. Reference issue IDs or data tickets where possible.

## Security & Configuration Tips
Keep secrets in a local `.env` or Streamlit Cloud secrets; load them via `python-dotenv` and never commit the files. Cache directories should contain only reproducible artifacts, so scrub personally identifiable data before pushing. When introducing new dependencies, ensure they remain compatible with Streamlit Cloud (Python 3.9+) and add rationale if a version pin is required.
