import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime
import numpy as np

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



def compute_bbiboll(df, n=7, k=3):

    if df.empty or len(df) < 24:
        return pd.DataFrame()
    
    df = df.copy()
    
 
    ma3 = df["close"].rolling(3).mean()
    ma6 = df["close"].rolling(6).mean()
    ma12 = df["close"].rolling(12).mean()
    ma24 = df["close"].rolling(24).mean()
    df["BBI"] = (ma3 + ma6 + ma12 + ma24) / 4

    df["BBI_MID"] = df["BBI"].rolling(n).mean()
    std_n = df["BBI"].rolling(n).std()
    df["BBI_UPPER"] = df["BBI_MID"] + k * std_n
    df["BBI_LOWER"] = df["BBI_MID"] - k * std_n
    

    df["WIDTH_RATIO"] = (df["BBI_UPPER"] - df["BBI_LOWER"]) / df["BBI_LOWER"]
    
    return df


st.sidebar.markdown("---")
st.sidebar.header("BBIBOLL 参数")
param_n = st.sidebar.slider("N (计算周期)", min_value=3, max_value=20, value=7)
param_k = st.sidebar.slider("K (倍数)", min_value=1.0, max_value=5.0, value=3.0, step=0.1)
threshold = st.sidebar.slider("收敛阈值 (%)", min_value=1.0, max_value=10.0, value=3.0, step=0.1) / 100

if st.sidebar.button("刷新数据并计算"):
    data_list = fetch_and_process(symbol, d_start, d_end, m60_s, m15_s)
    periods = ["日线", "周线", "月线", "60min", "15min"]
    tabs = st.tabs(periods)
    results_summary = []

    for tab, name, df_raw in zip(tabs, periods, data_list):
        with tab:
            if df_raw.empty:
                st.warning(f"{name} 无数据")
                continue

            df_bb = compute_bbiboll(df_raw, n=param_n, k=param_k)
            
            if df_bb.empty:
                st.warning(f"{name} 数据量不足以计算指标")
                continue


            df_bb["IS_CONVERGING"] = df_bb["WIDTH_RATIO"] <= threshold


            current_row = df_bb.iloc[-1]
            is_conv = current_row["IS_CONVERGING"]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("最新收盘价", f"{current_row['close']:.2f}")
            c2.metric("当前带宽比", f"{current_row['WIDTH_RATIO']*100:.2f}%")
            diff = current_row['WIDTH_RATIO'] - threshold
            c3.metric("状态", "✅ 已收敛" if is_conv else "❌ 波动中", 
                      delta=f"{diff*100:.2f}%", delta_color="inverse")
            c4.metric("数据总量", f"{len(df_bb)} 行")

     
            st.markdown("#### 🚀 计算结果明细 (最近 50 条)")
            
            st.dataframe(df_bb.tail(50).style.applymap(
                lambda x: 'background-color: rgba(0, 255, 0, 0.2)' if x == True else '', 
                subset=['IS_CONVERGING']
            ), use_container_width=True)

            with st.expander("查看原始数据及完整指标"):
                st.write(df_bb)

        
            results_summary.append({
                "周期": name,
                "收敛": "✅" if is_conv else "❌",
                "带宽比": f"{current_row['WIDTH_RATIO']*100:.2f}%",
                "最新时间": current_row['datetime'].strftime("%Y-%m-%d %H:%M")
            })


    st.markdown("### 🎯 多周期收敛汇总")
    summary_df = pd.DataFrame(results_summary)
    st.table(summary_df)
    
