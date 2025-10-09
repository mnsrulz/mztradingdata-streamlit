import streamlit as st
import polars as pl
import os
import altair as alt

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

    unique_strikes = df_lazy.select(pl.col("strike")).unique().sort(by="strike").collect()
    unique_expirations = df_lazy.select(pl.col("expiration")).unique().sort(by="expiration").collect()

    # display unique strikes and expirations  as dropdowns in sorted order
    strike = st.selectbox("Choose strike:", unique_strikes["strike"].to_list())
    expiration = st.selectbox("Choose expiration:", unique_expirations["expiration"].to_list())

# -------------------
# Main Area (Right side)
# -------------------
dt_list = (
    df_lazy
    # .filter(pl.col("dt") == "2025-10-01")
    # .filter(pl.col("symbol") == selected_symbol)
    .filter(pl.col("strike") == strike)
    .filter(pl.col("expiration") == expiration)
    .with_columns(
        (pl.col("iv") * 100).alias("iv_percent")
    )
    .collect()  # triggers computation
)

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
chart = alt.Chart(dt_list).mark_line().encode(
    x="dt:T",
    y="iv_percent:Q",
    color="option_type:N",   # separate line for C and P
    tooltip=[
        alt.Tooltip("dt:T", title="Date"), "option_type",
        alt.Tooltip("iv_percent:Q", title="IV (%)", format=".2f")  # 2 decimal places
    ]
).interactive()

st.altair_chart(chart, use_container_width=True)