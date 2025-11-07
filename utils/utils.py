import os
import streamlit as st

def parse_option_ticker(ticker: str) -> dict:
    """
    Parse OCC-style option ticker into components.
    Example: COIN260116P00200000 -> 
    {
        'symbol': 'COIN',
        'expiry': '2026-01-16',
        'option_type': 'Put',
        'strike': 200.00
    }
    """
    # Underlying symbol: variable length (up to 6 chars, until a digit appears)
    import re
    m = re.match(r"([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})", ticker)
    if not m:
        raise ValueError(f"Invalid option ticker format: {ticker}")
    
    symbol, yy, mm, dd, opt_type, strike_str = m.groups()
    year = int(f"20{yy}")
    month = int(mm)
    day = int(dd)
    strike = int(strike_str) / 1000
    
    return {
        "symbol": symbol,
        "expiry": f"{year:04d}-{month:02d}-{day:02d}",
        "option_type": "Call" if opt_type == "C" else "Put",
        "strike": strike,
        "display": f"{symbol} {year:04d}-{month:02d}-{day:02d} {'Call' if opt_type == 'C' else 'Put'} {strike:.2f}"
    }

def render_footer():
    # Display build info at the bottom
    # Display build info at the bottom
    build_time = os.getenv("BUILD_TIME", "unknown")
    git_sha = os.getenv("GIT_SHA", "unknown")

    st.markdown("---")  # horizontal separator
    st.caption(f"Build time: {build_time} | Git SHA: {git_sha}")