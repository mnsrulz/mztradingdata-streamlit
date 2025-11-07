import yfinance as yf
import streamlit as st
from components.stock_chart import render_yf_pricing_chart
from utils.datastore import load_tickers, save_tickers
from utils.utils import parse_option_ticker, render_footer

st.set_page_config(
    page_title="Options Data Explorer",
    layout="wide"  # this enables full-width content
)

st.title("📈 Options Data Explorer")

tickers = load_tickers()

# ticker = st.text_input("Enter Ticker Symbol", "COIN260116C00300000").upper()

# --- Modal for adding a symbol ---
@st.dialog("Add a Symbol", width="medium", dismissible=True)
def add_symbol_dialog():
    symbol_type = st.radio("Symbol Type", ["Stock", "Option"])
    
    if symbol_type == "Stock":
        stock_input = st.text_input("Enter Stock Ticker (e.g., AAPL)").upper()
        if st.button("✅ Add Stock"):
            if not stock_input:
                st.warning("Please enter a ticker.")
            elif stock_input in tickers:
                st.warning(f"{stock_input} already exists.")
            else:
                tickers.append(stock_input)
                save_tickers(tickers)
                st.success(f"{stock_input} added to watchlist!")
                st.rerun()
                
    else:  # Option
        underlying = st.text_input("Enter Underlying Stock Symbol (e.g., AAPL)").upper()
        if underlying:
            try:
                stock = yf.Ticker(underlying)
                expirations = stock.options
            except Exception:
                expirations = []
            
            if not expirations:
                st.warning("No option data available for this symbol.")
                return
            
            selected_exp = st.selectbox("Select Expiration", expirations)
            
            if selected_exp:
                opt_chain = stock.option_chain(selected_exp)
                strikes = sorted(list(set(opt_chain.calls.strike.tolist() + opt_chain.puts.strike.tolist())))
                selected_strike = st.selectbox("Select Strike", strikes)
                opt_type = st.radio("Option Type", ["Call", "Put"])
                
                option_symbol = f"{underlying}_{selected_exp}_{selected_strike}_{opt_type[0]}"

                opt_chain_df = opt_chain.calls if opt_type == "Call" else opt_chain.puts
                # st.dataframe(opt_chain_df)
                opt_chain_df['strike'] = opt_chain_df['strike'].astype(float)
                opt_row = opt_chain_df[opt_chain_df['strike'] == selected_strike]
                if not opt_row.empty:
                    option_symbol = opt_row['contractSymbol'].values[0]
                    st.text(f"Actual Option Symbol: {option_symbol}")
                    render_yf_pricing_chart(
                        option_symbol,
                        timeframe=timeframe,
                        interval=interval,
                        chart_type=chart_type,
                        height=300
                    )
                    if option_symbol in tickers:
                        st.warning(f"{option_symbol} already exists.")
                    else:      
                        add_another = st.checkbox("Add another after this", value=False)      
                        if st.button("✅ Add Option"):
                            if not selected_strike or not opt_type:
                                st.warning("Please select strike and option type.")
                            else:                                
                                tickers.append(option_symbol)
                                save_tickers(tickers)
                                st.success(f"{option_symbol} added to watchlist!")
                                if not add_another:                                    
                                    st.rerun()

@st.dialog("Confirm Delete")
def confirm_delete_ticker_dialog(ticker):
    st.write(f"Are you sure you want to delete **{ticker}**?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes"):
            tickers.remove(ticker)
            save_tickers(tickers)
            st.rerun()    

periodOptions = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]
intervalOptions = ["1d", "1wk"]

col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 3, 1])
with col1:    
    chart_type = st.segmented_control(
        "Chart Type", options=["Line", "Candlestick"], default="Line"
    )
with col2:
    grid_option = st.segmented_control("Charts per row", ["1", "2", "3", "4"], default="3")
    # grid_option = selected = st.selectbox("#Columns", ["1", "2", "3", "4"], label_visibility="collapsed", index=1)

with col3:
    interval = st.segmented_control("Interval", options=intervalOptions, default="1d", selection_mode="single")
with col4:
    timeframe = st.segmented_control("Timeframe", options=periodOptions, default="6mo", selection_mode="single")
with col5:    
    if st.button("➕ Add Ticker"):
        add_symbol_dialog()

search_text = st.text_input("Search Tickers", "").upper()

if search_text:
    filtered_tickers = [t for t in tickers if search_text in t]
else:
    filtered_tickers = tickers

n_cols = int(grid_option)

# --- Display charts ---
cols = st.columns(n_cols, gap="small")

for i, ticker in enumerate(filtered_tickers):
    col = cols[i % n_cols]
    with col:
        name_col, del_col = st.columns([4, 1])
        with name_col:
            st.markdown(f"##### {parse_option_ticker(ticker)['display']}")
        with del_col:
            if st.button("🗑️", key=f"del_{ticker}"):
                confirm_delete_ticker_dialog(ticker)
        render_yf_pricing_chart(
            ticker,
            timeframe=timeframe,
            interval=interval,
            chart_type=chart_type,
            height=600/n_cols
        )


render_footer()