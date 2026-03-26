import streamlit as st
import pandas as pd
import os
import plotly.express as px
from pyathena import connect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App Configuration
st.set_page_config(page_title="CryptoPulse Analytics", layout="wide")

# Fetch configuration
AWS_REGION = os.getenv("AWS_REGION")
S3_STAGING = os.getenv("ATHENA_S3_STAGING_DIR")
ATHENA_DB = os.getenv("ATHENA_DATABASE")

@st.cache_data(ttl=3600)
def run_athena_query(query):
    """
    Connects to AWS Athena and executes the given SQL query.
    """
    conn = connect(
        s3_staging_dir=S3_STAGING,
        region_name=AWS_REGION
    )
    return pd.read_sql(query, conn)

# Main UI Header
st.title("🌐 CryptoPulse: Data Lakehouse Analytics")
st.markdown(f"**Environment:** Production | **Source:** {ATHENA_DB} (Gold Zone)")
st.divider()

# --- Section 1: Market Leaders Overview ---
st.header("🏆 Market Leaders Overview")
try:
    # Fetch top coins ordered by market capitalization
    query_leaders = f"""
        SELECT symbol, price_usd, market_cap_usd, report_date 
        FROM {ATHENA_DB}.market_leaders 
        ORDER BY market_cap_usd DESC 
        LIMIT 10
    """
    df_leaders = run_athena_query(query_leaders)
    
    # Display top 5 in metric cards
    cols = st.columns(5)
    for index, row in df_leaders.head(5).iterrows():
        cols[index].metric(
            label=row['symbol'].upper(), 
            value=f"${row['price_usd']:,.2f}",
            delta=f"Cap: ${row['market_cap_usd']:,.0f}",
            delta_color="off" # Market cap is an absolute value, not a trend direction
        )
    
    st.subheader("Top Assets Detail")
    st.dataframe(df_leaders, use_container_width=True)
except Exception as e:
    st.error(f"Error loading Market Leaders: {e}")

# --- Section 2: Coin Trends Analysis ---
st.divider()
st.header("📈 Price Trends Analysis")
try:
    # Fetch historical price movement
    query_trends = f"""
        SELECT report_date, current_price, symbol, price_change_pct 
        FROM {ATHENA_DB}.coin_trends 
        ORDER BY report_date ASC
    """
    df_trends = run_athena_query(query_trends)
    
    # Ensure report_date is datetime for proper plotting
    df_trends['report_date'] = pd.to_datetime(df_trends['report_date'])
    
    fig_trends = px.line(
        df_trends, 
        x='report_date', 
        y='current_price', 
        color='symbol',
        title="Historical Price Movement"
    )
    st.plotly_chart(fig_trends, use_container_width=True)
except Exception as e:
    st.error(f"Error loading Coin Trends: {e}")

# --- Section 3: Liquidity Analysis ---
st.divider()
st.header("💧 Liquidity Ratio Distribution")
try:
    # Fetch liquidity ratios
    query_liquidity = f"""
        SELECT symbol, liquidity_ratio, report_date 
        FROM {ATHENA_DB}.liquidity_analysis
        ORDER BY liquidity_ratio DESC
    """
    df_liquidity = run_athena_query(query_liquidity)
    
    # Bar chart to compare liquidity ratios across symbols
    fig_liq = px.bar(
        df_liquidity, 
        x="symbol", 
        y="liquidity_ratio", 
        color="symbol",
        title="Liquidity Ratio by Cryptocurrency"
    )
    st.plotly_chart(fig_liq, use_container_width=True)
except Exception as e:
    st.error(f"Error loading Liquidity Analysis: {e}")

# Footer Metadata
st.divider()
st.caption("Data Architecture: CoinGecko API → AWS S3 (Bronze) → PySpark (Silver/Gold) → AWS Athena → Streamlit")
st.caption("Status: Orchestrated via Apache Airflow | CI/CD enabled via GitHub Actions")