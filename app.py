import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="测试", layout="wide")


def standardize_ohlcv(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    column_map = {
        "日期": "datetime", "时间": "datetime",
        "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low",
        "成交量": "volume"
    }
    df.rename(columns=column_map, inplace=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    existing_cols = [c for c in ["datetime", "open", "high", "low", "close", "volume"] if c in df.columns]
    return df[existing_cols].sort_values("datetime").reset_index(drop=True)

@st.cache_data(ttl=600)
def fetch_all_data(symbol, d_start, d_end, m60_start, m15_start):
    try:
        df_d = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=d_start, end_date=d_end, adjust="qfq")
        df_d = standardize_ohlcv(df_d)
        

        df_60 = ak.stock_zh_a_hist_min_em(symbol=symbol, period="60", adjust="qfq")
        df_60 = standardize_ohlcv(df_60)
        df_60 = df_60[df_60["datetime"] >= pd.to_datetime(m60_start)]
        
        df_15 = ak.stock_zh_a_hist_min_em(symbol=symbol, period="15", adjust="qfq")
        df_15 = standardize_ohlcv(df_15)
        df_15 = df_15[df_15["datetime"] >= pd.to_datetime(m15_start)]
        
        return df_d, df_60, df_15
    except Exception as e:
        st.error(f"数据抓取失败: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


st.sidebar.header("参数设置")
symbol = st.sidebar.text_input("股票代码", value="300628")

st.sidebar.subheader("日线范围")
d_start = st.sidebar.date_input("日线开始日期", value=datetime(2022, 1, 1)).strftime("%Y%m%d")
d_end = st.sidebar.date_input("日线结束日期", value=datetime(2026, 2, 1)).strftime("%Y%m%d")

st.sidebar.subheader("分钟线开始时间")
m60_start = st.sidebar.date_input("60min 开始日期", value=datetime(2024, 1, 1))
m15_start = st.sidebar.date_input("15min 开始日期", value=datetime(2025, 1, 1))

st.title(f"📊 股票数据监控: {symbol}")

if st.sidebar.button("开始获取数据"):
    with st.spinner('正在从 AkShare 加载数据...'):
        df_d, df_60, df_15 = fetch_all_data(symbol, d_start, d_end, m60_start, m15_start)
        

        tab1, tab2, tab3 = st.tabs(["日线数据", "60分钟数据", "15分钟数据"])
        
        with tab1:
            st.subheader("Daily Data")
            st.dataframe(df_d, use_container_width=True)
            if not df_d.empty:
                st.info(f"数据区间: {df_d['datetime'].min()} 至 {df_d['datetime'].max()}")
        
        with tab2:
            st.subheader("60-Min Data")
            st.dataframe(df_60, use_container_width=True)
            
        with tab3:
            st.subheader("15-Min Data")
            st.dataframe(df_15, use_container_width=True)
else:
    st.info("请在侧边栏配置参数并点击『开始获取数据』")
