# Weekly Economic Indicators Dashboard

An automated dashboard replicating the IGEES DOT Economic Policy Unit weekly economic indicators report for Ireland. Features live data sourcing, interactive charts, and scheduled updates.

## Features

- **Live Data**: Automatically fetches data from CSO Ireland, ECB, Yahoo Finance
- **PMI Scraping**: Scrapes AIB/Trading Economics for PMI data
- **Interactive Charts**: Plotly-based interactive visualizations
- **Heatmap Table**: Colour-coded monthly indicator table
- **Scheduled Updates**: GitHub Actions workflow for weekly data refresh
- **Cloud Deployment**: Ready for Streamlit Cloud deployment

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/weekly-economic-report.git
cd weekly-economic-report

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`

### Using the Run Script

```bash
./run.sh
```

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit"

# Create repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/weekly-economic-report.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `YOUR_USERNAME/weekly-economic-report`
5. Set the main file path: `app.py`
6. Click "Deploy"

Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

### Step 3: Enable Scheduled Updates

The GitHub Actions workflow will automatically run every Saturday at 8:00 AM UTC. To enable it:

1. Go to your GitHub repository
2. Click "Actions" tab
3. Enable workflows if prompted
4. The "Update Economic Data" workflow will run automatically

To trigger a manual update:
1. Go to Actions → "Update Economic Data"
2. Click "Run workflow"
3. Optionally check "Force refresh all data"

## Project Structure

```
weekly_economic_report/
├── app.py                      # Main Streamlit dashboard
├── config.py                   # Configuration and constants
├── requirements.txt            # Python dependencies
├── run.sh                      # Launch script
│
├── data/
│   ├── __init__.py
│   ├── cso.py                  # CSO Ireland StatBank API
│   ├── ecb.py                  # ECB exchange rates API
│   ├── markets.py              # Yahoo Finance, bonds, commodities
│   ├── pmi_scraper.py          # PMI web scraping
│   └── storage.py              # Data caching and persistence
│
├── reports/
│   ├── __init__.py
│   ├── charts.py               # Plotly chart generation
│   └── pdf_generator.py        # PDF report generation
│
├── scripts/
│   └── update_data.py          # Scheduled data update script
│
├── .github/
│   └── workflows/
│       └── update-data.yml     # GitHub Actions workflow
│
├── .streamlit/
│   └── config.toml             # Streamlit configuration
│
├── cache/                      # Cached API responses
└── data_store/                 # Persistent data storage
```

## Data Sources

| Indicator | Source | Update Method |
|-----------|--------|---------------|
| Live Register | CSO Ireland (StatBank API) | Live API |
| CPI / Inflation | CSO Ireland (StatBank API) | Live API |
| EUR/GBP, EUR/USD | ECB Statistical Warehouse | Live API |
| Brent Crude Oil | Yahoo Finance | Live API |
| Natural Gas | Yahoo Finance | Live API |
| Manufacturing PMI | AIB / Trading Economics | Web scraping |
| Services PMI | AIB / Trading Economics | Web scraping |
| Construction PMI | AIB / Trading Economics | Web scraping |
| Consumer Sentiment | KBC (cached) | Manual / Scraping |
| Bond Yields | World Government Bonds | Web scraping |
| Container Costs | Freightos (cached) | Manual update |

## Configuration

### Environment Variables

Create a `.env` file (optional):

```bash
# Optional: Anthropic API for AI-generated commentary
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Freightos API for container shipping data
FREIGHTOS_API_KEY=your_api_key_here
```

### Streamlit Secrets (for Cloud deployment)

In Streamlit Cloud, add secrets via the dashboard:
1. Go to your app settings
2. Click "Secrets"
3. Add any required API keys

## Manual Data Updates

To manually update PMI or other data that requires scraping:

```bash
source venv/bin/activate
python scripts/update_data.py
```

Or with force refresh:

```bash
FORCE_REFRESH=true python scripts/update_data.py
```

## Scheduled Updates

The GitHub Actions workflow (`update-data.yml`) runs:
- **Schedule**: Every Saturday at 8:00 AM UTC
- **Manual**: Can be triggered via GitHub Actions UI

The workflow:
1. Fetches fresh data from all sources
2. Updates cache and data store
3. Commits changes back to the repository
4. Streamlit Cloud auto-redeploys on new commits

## Troubleshooting

### Data not loading
- Check the "Refresh Data" button in the sidebar
- Verify API endpoints are accessible
- Check the `cache/last_update.json` for error details

### PMI scraping failing
- Website structure may have changed
- Check `data/pmi_scraper.py` for current selectors
- Fallback data will be used automatically

### Deployment issues
- Ensure `requirements.txt` is up to date
- Check Streamlit Cloud logs for errors
- Verify Python version compatibility (3.9+)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Data sources: CSO Ireland, ECB, AIB, Yahoo Finance
- Original report format: IGEES DOT Economic Policy Unit
