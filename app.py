import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
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
st.sidebar.header("📊 BBIBOLL 参数")
param_n = st.sidebar.slider("N (计算周期)", min_value=3, max_value=20, value=7)
param_k = st.sidebar.slider("K (倍数)", min_value=1.0, max_value=5.0, value=3.0, step=0.1)
threshold = st.sidebar.slider("收敛阈值 (%)", min_value=1.0, max_value=10.0, value=3.0, step=0.1) / 100

st.sidebar.markdown("---")
st.sidebar.header("📊 成交量挤压参数")
vol_short = st.sidebar.number_input("短周期均量", value=7)
vol_long = st.sidebar.number_input("长周期均量", value=14)
vol_threshold = st.sidebar.slider("成交量挤压阈值", 0.1, 1.0, 0.5, step=0.05)


def compute_vol_compression(df, short=7, long=14, threshold_ratio=0.5):
    if df.empty or len(df) < long * 3:
        return pd.DataFrame()
    
    df = df.copy()

    df['VOL_SHORT'] = df['volume'].rolling(short).mean()
    df['VOL_LONG'] = df['volume'].rolling(long).mean()

    max_long = df['VOL_LONG'].rolling(long * 3).max()
    df['VOL_RATIO'] = df['VOL_SHORT'] / max_long


    df['VOL_COMPRESSED'] = df['VOL_RATIO'] <= threshold_ratio
    return df

# def plot_bbiboll_interactive(df, symbol_name):

#     if df.empty or "BBI_UPPER" not in df.columns:
#         return None


#     fig = go.Figure()

#     fig.add_trace(go.Candlestick(
#         x=df['datetime'],
#         open=df['open'],
#         high=df['high'],
#         low=df['low'],
#         close=df['close'],
#         name='K线'
#     ))


#     line_style = dict(width=1.5)
#     fig.add_trace(go.Scatter(x=df['datetime'], y=df['BBI_UPPER'], 
#                              name='上轨', line=dict(color='rgba(255, 0, 0, 0.4)', **line_style)))
#     fig.add_trace(go.Scatter(x=df['datetime'], y=df['BBI_MID'], 
#                              name='中轨', line=dict(color='rgba(0, 0, 255, 0.4)', **line_style)))
#     fig.add_trace(go.Scatter(x=df['datetime'], y=df['BBI_LOWER'], 
#                              name='下轨', line=dict(color='rgba(0, 255, 0, 0.4)', **line_style)))

#     conv_df = df[df["IS_CONVERGING"] == True]
#     if not conv_df.empty:
#         fig.add_trace(go.Scatter(
#             x=conv_df['datetime'],
#             y=conv_df['low'] * 0.99, 
#             mode='markers',
#             marker=dict(symbol='triangle-up', size=12, color='firebrick'),
#             name='收敛信号'
#         ))


#     fig.update_layout(
#         title=f"{symbol_name} 多周期分析",
#         yaxis_title="价格",
#         xaxis_rangeslider_visible=False,
#         height=600,
#         template="plotly_white",
#         hovermode="x unified"
#     )


#     fig.update_xaxes(
#         rangebreaks=[
#             dict(bounds=["sat", "mon"]), 
#         ]
#     )

#     return fig

def plot_combined_chart(df, symbol_name):
    if df.empty or "BBI_UPPER" not in df.columns or "VOL_RATIO" not in df.columns:
        return None

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])


    fig.add_trace(go.Candlestick(
        x=df['datetime'], open=df['open'], high=df['high'], 
        low=df['low'], close=df['close'], name='K线'
    ), row=1, col=1)

    line_style = dict(width=1)
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['BBI_UPPER'], name='上轨', line=dict(color='rgba(255,0,0,0.3)', **line_style)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['BBI_MID'], name='中轨', line=dict(color='rgba(0,0,255,0.2)', **line_style)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['BBI_LOWER'], name='下轨', line=dict(color='rgba(0,255,0,0.3)', **line_style)), row=1, col=1)


    conv_df = df[df["IS_CONVERGING"] == True]
    if not conv_df.empty:
        fig.add_trace(go.Scatter(
            x=conv_df['datetime'], y=conv_df['low']*0.98, mode='markers',
            marker=dict(symbol='triangle-up', size=10, color='firebrick'), name='价格收敛'
        ), row=1, col=1)


    colors = ['red' if row['close'] >= row['open'] else 'green' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df['datetime'], y=df['volume'], name='成交量', marker_color=colors, opacity=0.7), row=2, col=1)


    vol_comp_df = df[df["VOL_COMPRESSED"] == True]
    if not vol_comp_df.empty:
        fig.add_trace(go.Scatter(
            x=vol_comp_df['datetime'], y=[0] * len(vol_comp_df),
            mode='markers', marker=dict(symbol='circle', size=6, color='blue'), name='量能挤压'
        ), row=2, col=1)

    fig.update_layout(height=700, template="plotly_white", xaxis_rangeslider_visible=False, showlegend=True, hovermode="x unified")
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


if st.sidebar.button("刷新数据并计算"):
    data_list = fetch_and_process(symbol, d_start, d_end, m60_s, m15_s)
    periods = ["日线", "周线", "月线", "60min", "15min"]
    tabs = st.tabs(periods)
    results_summary = []

    for tab, name, df_raw in zip(tabs, periods, data_list):
        with tab:
            if df_raw.empty:
                st.warning(f"{name} 周期暂无数据")
                continue

            df_processed = compute_bbiboll(df_raw, n=param_n, k=param_k)
            if df_processed.empty:
                st.warning(f"{name} 数据不足计算 BBIBOLL")
                continue
            
      
            df_processed["IS_CONVERGING"] = df_processed["WIDTH_RATIO"] <= threshold
  
            df_processed = compute_vol_compression(df_processed, short=vol_short, long=vol_long, threshold_ratio=vol_threshold)
            
            if df_processed.empty:
                st.warning(f"{name} 数据不足计算成交量指标")
                continue

            curr = df_processed.iloc[-1]
            
   
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("收盘价", f"{curr['close']:.2f}")
            col_b.metric("带宽比", f"{curr['WIDTH_RATIO']*100:.2f}%", 
                         delta=f"{(curr['WIDTH_RATIO']-threshold)*100:.2f}%", delta_color="inverse")
            col_c.metric("量能比", f"{curr['VOL_RATIO']*100:.1f}%")
            col_d.write(f"状态: {'✅收敛' if curr['IS_CONVERGING'] else '❌波动'} | {'🔵地量' if curr['VOL_COMPRESSED'] else '⚪正常'}")

       
            results_summary.append({
                "周期": name,
                "价格收敛": "✅" if curr['IS_CONVERGING'] else "❌",
                "量能挤压": "🔵" if curr['VOL_COMPRESSED'] else "⚪",
                "带宽比": f"{curr['WIDTH_RATIO']*100:.2f}%",
                "最新时间": curr['datetime'].strftime("%Y-%m-%d %H:%M")
            })

     
            fig = plot_combined_chart(df_processed, f"{symbol} ({name})")
            if fig:
                st.plotly_chart(fig, use_container_width=True)

    
            with st.expander(f"查看 {name} 详细数据表"):
                st.dataframe(df_processed.tail(100), use_container_width=True)


    if results_summary:
        st.markdown("---")
        st.markdown("### 🎯 多周期状态共振汇总")
        st.table(pd.DataFrame(results_summary))
    
