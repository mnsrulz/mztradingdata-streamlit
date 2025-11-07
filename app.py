import streamlit as st
import polars as pl
import os
from datetime import date, timedelta

from utils.utils import render_footer

# Read from environment variable, with a fallback default
DATA_DIR = os.getenv("DATA_DIR", "/mnt/c/ws/consolidated-data-by-symbol")

st.set_page_config(
    page_title="Options Data Explorer",
    layout="wide"  # this enables full-width content
)

# -------------------
# Sidebar Filters
# -------------------

with st.sidebar:
    # Symbol filter
    
    symbols = sorted([
        d.split("=")[1]
        for d in os.listdir(DATA_DIR)
        if d.startswith("symbol=")
    ])
    selected_symbol = st.selectbox("Choose a Symbol:", symbols)
    # selected_symbol = st.text_input("Enter symbol", "AAPL").upper()

    df_lazy = pl.scan_parquet(f"{DATA_DIR}/symbol={selected_symbol}/*.parquet")

    filter_mode = st.radio("By:", ["Delta", "Strike"])


    if filter_mode == "Strike":
        unique_strikes = df_lazy.select(pl.col("strike")).unique().sort(by="strike").collect()
        strike = st.selectbox("Choose strike:", unique_strikes["strike"].to_list())
    else:
        # Numeric input for delta (10-90, default 25)
        delta_input = st.number_input("Choose delta", min_value=10, max_value=90, value=25, step=1)
        delta_input = delta_input / 100.0  # convert to decimal

    unique_expirations = df_lazy.select(pl.col("expiration")).unique().sort(by="expiration").collect()
    unique_options_symbols = df_lazy.select(pl.col("option_symbol")).unique().sort(by="option_symbol").collect()

    if len(unique_options_symbols) > 1:
        option_symbol = st.selectbox("Choose option symbol:", unique_options_symbols["option_symbol"].to_list())
        df_lazy = df_lazy.filter(pl.col("option_symbol") == option_symbol)

    show_weekly = st.checkbox("Show weekly options", value=False)    
    monthly_expiries = unique_expirations.with_columns([
        pl.col("expiration").dt.year().alias("year"),
        pl.col("expiration").dt.month().alias("month"),
        pl.col("expiration").dt.week().alias("week"),
        (
            (pl.col("expiration").dt.day() >= 15) &
            (pl.col("expiration").dt.day() <= 21)
        ).alias("is_third_week")
    ])
    monthly_expiries = (
        monthly_expiries.filter(pl.col("is_third_week")).group_by(["year", "month", "week"])
            .agg(pl.col("expiration").max().alias("expiration"))
            .select("expiration")
            .sort("expiration")
    )
    if not show_weekly:
        unique_expirations = monthly_expiries

        # Today's date
    today = date.today()

    # Find first expiration greater than today
    future_expirations = [d for d in unique_expirations["expiration"].to_list() if d > today]

    if future_expirations:
        default_value = future_expirations[0]
        default_index = unique_expirations["expiration"].to_list().index(default_value)
    else:
        default_index = 0  # fallback if no future dates
        default_value = unique_expirations["expiration"].to_list()[0]

    # display unique strikes and expirations  as dropdowns in sorted order
    # expiration = st.selectbox("Choose expiration:", unique_expirations["expiration"].to_list(), index=default_index)
    
    expiration = st.segmented_control(
        "Expiration", unique_expirations["expiration"].to_list(), selection_mode="single", default=default_value
    )

    show_table = st.checkbox("Show raw data", value=False)

    # choice = st.radio(
    #     "Choose mode:", 
    #     unique_expirations["expiration"].to_list(), 
    #     horizontal=True
    # )
    
# -------------------
# Main Area (Right side)
# -------------------
periodOptions = ["1mo", "3mo", "6mo", "1y", "ytd", "max"]
periodOptionsDays = [30, 90, 180, 365, date.today().timetuple().tm_yday, 99999]

timeframe = st.segmented_control("Timeframe", options=periodOptions, default="6mo", selection_mode="single")
days_worth = periodOptionsDays[periodOptions.index(timeframe)]

df_lazy = df_lazy.filter(pl.col("dt") >= (date.today() - timedelta(days=days_worth)))

df_lazy = df_lazy.filter(pl.col("expiration") == expiration).with_columns(
        (pl.col("iv") * 100).alias("iv_percent")
    ).with_columns(
        ((pl.col("bid") + pl.col("ask"))/2).alias("mid_price")  # mid price
    )

if filter_mode == "Delta":
    # 1. Add a column with the absolute difference to user input
    df_lazy = df_lazy.with_columns(
        (pl.col("delta").abs() - delta_input).abs().alias("delta_diff")
    )

    # 2. For each day, pick the row with the minimal delta_diff
    df_lazy = (
        df_lazy.group_by(["dt", "option_type"])  # group by day and option type
        .agg(
            pl.all().sort_by("delta_diff").first()  # pick the row with min delta_diff per day
        )
    )
else:
    df_lazy = df_lazy.filter(pl.col("strike") == strike)

dt_list = df_lazy.sort(
    by=["dt", "option_type"], 
    descending=[True, False]  # True = descending, False = ascending
).collect()

if show_table:
    st.subheader("Query Result Table")
    st.dataframe(dt_list, width="stretch", column_config={
            "dt": st.column_config.DatetimeColumn(
                "Date", 
                format="YYYY-MM-DD",  # only show the date
            ),
            "expiration": st.column_config.DatetimeColumn(
                "Expiration", 
                format="YYYY-MM-DD",  # only show the date
            )        
        })  # scrollable, interactive table

# Pivot so each date has Call and Put in one row
dt_wide = dt_list.pivot(
    values=['iv_percent', 'mid_price'],
    index='dt',
    on='option_type'    
)

# Polars pivot returns columns like ['dt', 'C', 'P']
# Convert to Pandas for Altair
dt_wide_pd = dt_wide.to_pandas()


st.subheader("Options Implied Volatility over time")
st.line_chart(dt_list, x='dt', y='iv_percent', color="option_type")

st.subheader("Options Mid Price over time")
st.line_chart(dt_list, x='dt', y='mid_price', color='option_type')

render_footer()