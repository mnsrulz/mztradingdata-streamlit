import json
import os
from pathlib import Path

DATA_FILE = Path(os.getenv("TICKERS_JSON_PATH", "/mnt/c/ws/stock-options-watchlist/tickers.json"))

def load_tickers():
    """Load saved tickers from JSON file"""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_tickers(tickers):
    """Save tickers to JSON file"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(tickers, f, indent=2)
