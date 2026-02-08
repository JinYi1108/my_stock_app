import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="多周期选股数据", layout="wide")


def standardize_ohlcv(df):
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    mapping = {"日期": "datetime", "时间": "datetime", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "volume"}
    df.rename(columns=mapping, inplace=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    cols = [c for c in ["datetime", "open", "high", "low", "close", "volume"] if c in df.columns]
    return df[cols].sort_values("datetime").reset_index(drop=True)


def resample_data(df, period='W'):

    if df.empty: return pd.DataFrame()
    logic = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    resampled = df.set_index('datetime').resample(period).agg(logic).dropna().reset_index()
    return resampled

@st.cache_data(ttl=3600)
def fetch_and_process(symbol, d_start, d_end, m60_start, m15_start):

    df_d_raw = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=d_start, end_date=d_end, adjust="qfq")
    df_d = standardize_ohlcv(df_d_raw)
    
    df_w = resample_data(df_d, 'W-MON')
    df_m = resample_data(df_d, 'ME')
    
    df_60 = standardize_ohlcv(ak.stock_zh_a_hist_min_em(symbol=symbol, period="60", adjust="qfq"))
    df_60 = df_60[df_60["datetime"] >= pd.to_datetime(m60_start)]
    
    df_15 = standardize_ohlcv(ak.stock_zh_a_hist_min_em(symbol=symbol, period="15", adjust="qfq"))
    df_15 = df_15[df_15["datetime"] >= pd.to_datetime(m15_start)]
    
    return df_d, df_w, df_m, df_60, df_15


st.sidebar.title("📊 参数配置")
symbol = st.sidebar.text_input("股票代码", "300461")
d_start = st.sidebar.date_input("日线起始", datetime(2022, 1, 1)).strftime("%Y%m%d")
d_end = st.sidebar.date_input("日线结束", datetime(2026, 2, 1)).strftime("%Y%m%d")
m60_s = st.sidebar.date_input("60min起始", datetime(2026, 1, 1))
m15_s = st.sidebar.date_input("15min起始", datetime(2026, 1, 1))

if st.sidebar.button("刷新数据"):
    data_list = fetch_and_process(symbol, d_start, d_end, m60_s, m15_s)
    periods = ["日线", "周线", "月线", "60min", "15min"]
    tabs = st.tabs(periods)
    
    for tab, name, df in zip(tabs, periods, data_list):
        with tab:
            st.markdown(f"### {name} 数据详情")
            st.dataframe(df, use_container_width=True)
            st.write(f"数据条数: {len(df)}")
