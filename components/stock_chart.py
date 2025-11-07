import yfinance as yf
from streamlit_lightweight_charts import renderLightweightCharts
import streamlit as st

def render_yf_pricing_chart(
    ticker: str,
    timeframe: str = "6mo",
    interval: str = "1d",
    chart_type: str = "Candlestick",
    height: int = 500
):
    """
    Render a stock price chart using streamlit-lightweight-charts and yfinance.

    Args:
        ticker (str): Stock ticker symbol, e.g., "AAPL"
        timeframe (str): Period to fetch from yfinance (e.g., "1mo", "6mo", "1y")
        interval (str): Interval to fetch (e.g., "1d", "1h", "15m")
        chart_type (str): "Candlestick" or "Line"
        height (int): Height of the chart in pixels
    """
    data = yf.Ticker(ticker).history(period=timeframe, interval=interval)
    if data.empty:
        st.warning(f"No data found for {ticker}. Try another timeframe or interval.")
        return

    price_data = [
            {
                "time": row.name.strftime("%Y-%m-%dT%H:%M:%S"),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "value": row["Close"],
            }
            for _, row in data.iterrows()
        ]

    chartOptions = {
        "height": height,
        "layout": {
            "textColor": 'black',
            "background": {
                "type": 'solid',
                "color": 'white'
            }
        }
    }

    if chart_type == "Candlestick":
        seriesCandlestickChart = [{
            "type": 'Candlestick',
            "data": price_data,
            "options": {
                "upColor": '#26a69a',
                "downColor": '#ef5350',
                "borderVisible": False,
                "wickUpColor": '#26a69a',
                "wickDownColor": '#ef5350'
            }
        }]

        renderLightweightCharts( [
            {
                "chart": chartOptions,
                "series": seriesCandlestickChart,
            }
        ], f'candlestick-{ticker}')
    else:
        seriesLineChart = [{
            "type": 'Line',
            "data": price_data,
            "options": {}
        }]

        renderLightweightCharts( [
            {
                "chart": chartOptions,
                "series": seriesLineChart,
            }
        ], f'line-{ticker}')