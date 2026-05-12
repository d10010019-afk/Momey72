import streamlit as st
from FinMind.data import DataLoader
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 1. 頁面設定
st.set_page_config(page_title="五星共振系統-書本範例版", layout="wide")
st.title("🌟 五星共振量化選股系統 (FinMind 標準版)")

# 2. 您的 API Token
FINMIND_TOKEN = "EyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiTWlrZSAiLCJlbWFpbCI6ImQxMDAxMDAxOUBnbWFpbC5jb20iLCJ0b2tlbl92ZXJzaW9uIjowfQ.ll0lBmiltd6LZWSR36rp-llozQ0EXvacpA57F0vmBqc"

# 3. 輸入框
symbol = st.text_input("🔍 請輸入台股代碼 (例如: 3481, 2330, 0050)", "3481")

@st.cache_data(ttl=3600)
def get_data_from_book_syntax(ticker):
    try:
        # 參考書中第 170 頁語法
        dl = DataLoader()
        dl.login(token=FINMIND_TOKEN)
        
        # 設定抓取時間區間 (抓取近半年的資料確保指標運算準確)
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        # 執行書中提到的資料抓取函式
        df = dl.taiwan_stock_daily(
            stock_id=ticker,
            start_date=start_date
        )
        
        if df is None or df.empty:
            return None

        # 書中回傳的欄位通常是 date, open, high, low, close, trading_volume
        # 我們將其標準化以利繪圖與運算
        df = df.rename(columns={
            'date': 'Date', 'open': 'Open', 'high': 'High', 
            'low': 'Low', 'close': 'Close', 'trading_volume': 'Volume'
        })
        
        # 確保數值型態為浮點數
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.set_index('Date', inplace=True)
        
        # --- 五星指標運算 ---
        # 1. 5日均線
        df['MA5'] = df['Close'].rolling(window=5).mean()
        
        # 2. RSI 指標 (14日)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        
        # 3. MACD 指標
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = exp1 - exp2
        df['MACD_Line'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['MACD_Line']
        
        return df
    except Exception as e:
        st.error(f"資料抓取失敗：{e}")
        return None

# --- 介面呈現 ---
df = get_data_from_book_syntax(symbol)

if df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 五星評分邏輯
    score = 0
    res = []
    if last['Close'] > last['MA5']: score += 1; res.append("✅ 5日線上")
    if last['MACD_Hist'] > 0 and last['MACD_Hist'] > prev['MACD_Hist']: score += 1; res.append("✅ MACD轉強")
    if 40 < last['RSI'] < 75: score += 1; res.append(f"✅ RSI {last['RSI']:.1f}")
    if last['Close'] > last['Open']: score += 1; res.append("✅ 收紅K")
    if last['Volume'] > df['Volume'].tail(5).mean(): score += 1; res.append("✅ 量能爆發")

    st.subheader(f"📊 診斷評分：{score} / 5")
    c = st.columns(5)
    for i, item in enumerate(res):
        with c[i]: st.info(item)

    # 繪製專業 K 線圖 (Plotly)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='orange'), name='5日線'), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD動能'), row=2, col=1)
    fig.update_layout(height=600, template='plotly_dark', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ 查無資料。請確認代碼是否正確（例如群創請打 3481）。")
