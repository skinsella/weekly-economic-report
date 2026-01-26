#!/bin/bash
# Run the Weekly Economic Indicators Dashboard

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Run Streamlit
echo "Starting Weekly Economic Indicators Dashboard..."
echo "Open http://localhost:8501 in your browser"
streamlit run app.py --server.port 8501
