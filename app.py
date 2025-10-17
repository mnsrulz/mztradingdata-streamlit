import streamlit as st
import polars as pl
import os
import altair as alt
from datetime import date

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
    selected_symbol = st.text_input("Enter symbol", "AAPL").upper()

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
    if not show_weekly:
        unique_expirations = unique_expirations.with_columns([
            pl.col("expiration").dt.year().alias("year"),
            pl.col("expiration").dt.month().alias("month"),
            pl.col("expiration").dt.week().alias("week"),
            (
                (pl.col("expiration").dt.day() >= 15) &
                (pl.col("expiration").dt.day() <= 21)
            ).alias("is_third_week")
        ])
        unique_expirations = (
            unique_expirations.filter(pl.col("is_third_week")).group_by(["year", "month", "week"])
                .agg(pl.col("expiration").max().alias("expiration"))
                .select("expiration")
                .sort("expiration")
        )

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
    st.dataframe(dt_list, use_container_width=True, column_config={
            "dt": st.column_config.DatetimeColumn(
                "Date", 
                format="YYYY-MM-DD",  # only show the date
            ),
            "expiration": st.column_config.DatetimeColumn(
                "Expiration", 
                format="YYYY-MM-DD",  # only show the date
            )        
        })  # scrollable, interactive table

# df_pivot = dt_list.pivot(index="dt", columns="option_type", values="iv")

# st.line_chart(df_pivot)

# Multi-line chart by option_type
iv_chart = alt.Chart(dt_list).mark_line().encode(
    x="dt:T",
    y="iv_percent:Q",
    color=alt.Color("option_type:N", legend=alt.Legend(
        orient="top", title="Option Type", titleAnchor="start"
    ), 
    scale=alt.Scale(domain=["C", "P"], range=["#006E09", "#e2403a"]),   
    ),   
    tooltip=[
        alt.Tooltip("dt:T", title="Date"), "option_type",
        alt.Tooltip("iv_percent:Q", title="IV (%)", format=".2f")  # 2 decimal places
    ]
).interactive()

st.subheader("Implied Volatility over time")
st.altair_chart(iv_chart, use_container_width=True)

# Multi-line for pricing
mid_price_chart = alt.Chart(dt_list).mark_line().encode(
    x="dt:T",
    y="mid_price:Q",
    color=alt.Color("option_type:N", legend=alt.Legend(
        orient="top", title="Option Type", titleAnchor="start"
    ),
    scale=alt.Scale(domain=["C", "P"], range=["#006E09", "#e2403a"])),   
    tooltip=[
        alt.Tooltip("dt:T", title="Date"), "option_type",
        alt.Tooltip("mid_price:Q", title="Mid Price", format=".2f")  # 2 decimal places
    ]
).interactive()

st.subheader("Pricing over time")
st.altair_chart(mid_price_chart, use_container_width=True)

# Display build info at the bottom
build_time = os.getenv("BUILD_TIME", "unknown")
git_sha = os.getenv("GIT_SHA", "unknown")

st.markdown("---")  # horizontal separator
st.caption(f"Build time: {build_time} | Git SHA: {git_sha}")