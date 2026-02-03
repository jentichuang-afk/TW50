import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- 1. 頁面設定 ---
st.set_page_config(page_title="股票大師：智能選股雷達", layout="wide", page_icon="📡")
st.title("📡 股票大師：策略 2 (RSI + 200MA) 每日掃描")

# --- 2. 核心數據處理 ---
# 為了示範，這裡列出台灣50成分股 (您可以自行擴充至150檔)
def get_target_tickers():
    # 台灣50成份股 (範例)
    tw50 = [
        "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2303.TW", "2881.TW", "2882.TW", "2891.TW", "2886.TW", "2884.TW",
        "2382.TW", "2885.TW", "2892.TW", "2207.TW", "2357.TW", "2890.TW", "1216.TW", "2912.TW", "2002.TW", "2880.TW",
        "2883.TW", "2327.TW", "2345.TW", "2379.TW", "3034.TW", "5880.TW", "2395.TW", "3008.TW", "2887.TW", "1101.TW",
        "3045.TW", "2801.TW", "2412.TW", "6505.TW", "3711.TW", "2603.TW", "3037.TW", "5871.TW", "2354.TW", "4904.TW",
        "2324.TW", "5876.TW", "2408.TW", "9910.TW", "2105.TW", "1303.TW", "1301.TW", "1326.TW", "3017.TW", "2609.TW"
    ]
    return tw50

# RSI 計算函數
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- 3. 掃描引擎 ---
def scan_market(tickers):
    results_buy = []
    results_sell = []
    
    # 進度條
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 為了節省時間，使用 yfinance 的批次下載 (Batch Download)
    # 但為了計算準確的 MA200，我們需要下載過去一年的資料
    start_date = datetime.now() - timedelta(days=400)
    end_date = datetime.now() + timedelta(days=1)
    
    status_text.text("正在連線 Yahoo Finance 下載數據 (這可能需要 30 秒)...")
    
    try:
        # 批次下載
        data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', progress=False)
        
        total = len(tickers)
        for i, ticker in enumerate(tickers):
            # 更新進度
            progress = (i + 1) / total
            progress_bar.progress(progress)
            
            try:
                # 取出單一個股資料
                df = data[ticker].copy()
                
                # 清理資料
                if df.empty or len(df) < 200:
                    continue
                    
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df = df.dropna(subset=['Close'])
                
                # 計算指標
                # 1. MA200 (季線/年線分界，這裡用200日作為長線保護)
                df['MA200'] = df['Close'].rolling(200).mean()
                
                # 2. RSI (14)
                # 使用 Wilder's RSI 或簡單 RSI，這裡用簡單移動平均模擬
                delta = df['Close'].diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                ema_up = up.ewm(com=13, adjust=False).mean()
                ema_down = down.ewm(com=13, adjust=False).mean()
                rs = ema_up / ema_down
                df['RSI'] = 100 - (100 / (1 + rs))
                
                # 取得最新一天的數據
                last_row = df.iloc[-1]
                price = last_row['Close']
                ma200 = last_row['MA200']
                rsi = last_row['RSI']
                date_str = df.index[-1].strftime('%Y-%m-%d')
                
                # --- 策略 2 邏輯判定 ---
                
                # 🟢 買入條件：股價 > 200MA (長多) 且 RSI < 30 (超賣)
                if price > ma200 and rsi < 30:
                    dist_ma200 = (price - ma200) / ma200 * 100
                    results_buy.append({
                        "代碼": ticker.replace(".TW", ""),
                        "日期": date_str,
                        "收盤價": f"{price:.2f}",
                        "RSI": f"{rsi:.1f} 🔥",
                        "200MA": f"{ma200:.2f}",
                        "乖離率": f"{dist_ma200:.1f}%",
                        "狀態": "長多回檔 (強烈買訊)"
                    })
                
                # 🟡 觀察名單：股價 > 200MA 且 RSI < 40 (快到了)
                elif price > ma200 and rsi < 40:
                     dist_ma200 = (price - ma200) / ma200 * 100
                     results_buy.append({
                        "代碼": ticker.replace(".TW", ""),
                        "日期": date_str,
                        "收盤價": f"{price:.2f}",
                        "RSI": f"{rsi:.1f}",
                        "200MA": f"{ma200:.2f}",
                        "乖離率": f"{dist_ma200:.1f}%",
                        "狀態": "觀察中 (RSI < 40)"
                    })

                # 🔴 賣出條件：RSI > 70 (過熱)
                if rsi > 70:
                    results_sell.append({
                        "代碼": ticker.replace(".TW", ""),
                        "日期": date_str,
                        "收盤價": f"{price:.2f}",
                        "RSI": f"{rsi:.1f} ⚠️",
                        "200MA": f"{ma200:.2f}",
                        "狀態": "過熱 (注意風險)"
                    })

            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue

        status_text.text("掃描完成！")
        return pd.DataFrame(results_buy), pd.DataFrame(results_sell)

    except Exception as e:
        st.error(f"下載失敗: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 4. 主介面 ---
st.markdown("""
### 策略 2：RSI + 200MA 長線保護短線
* **核心邏輯**：只做「長線多頭」的股票，並等待它「短線被錯殺」時撿便宜。
* **✅ 買進條件**：股價在 **200MA (年線)** 之上，且 **RSI < 30** (或 40)。
* **❌ 賣出條件**：**RSI > 70** (短線過熱)。
""")

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🚀 開始掃描全市場", type="primary"):
        tickers = get_target_tickers()
        df_buy, df_sell = scan_market(tickers)
        
        st.session_state['df_buy'] = df_buy
        st.session_state['df_sell'] = df_sell

# 顯示結果
if 'df_buy' in st.session_state:
    tab1, tab2 = st.tabs(["🟢 潛力買點 (RSI低+長多)", "🔴 潛力賣點 (RSI高)"])
    
    with tab1:
        if not st.session_state['df_buy'].empty:
            st.success(f"共找到 {len(st.session_state['df_buy'])} 檔符合條件！")
            st.dataframe(st.session_state['df_buy'], use_container_width=True)
            st.markdown("💡 **解讀**：這些股票長線趨勢向上，但最近幾天跌深了。這通常是勝率最高的「回後買上漲」機會。")
        else:
            st.info("目前沒有股票符合「股價 > 200MA 且 RSI < 40」的條件。市場可能處於強勢上漲或全面空頭。")

    with tab2:
        if not st.session_state['df_sell'].empty:
            st.warning(f"共找到 {len(st.session_state['df_sell'])} 檔過熱股！")
            st.dataframe(st.session_state['df_sell'], use_container_width=True)
            st.markdown("💡 **解讀**：這些股票短線漲太多了，隨時可能回檔，建議分批獲利了結，不要追高。")
        else:
            st.info("目前沒有股票 RSI > 70。")

st.divider()
st.markdown("### 📚 如何擴充到 150 大公司？")
st.markdown("目前的代碼列表在 `get_target_tickers()` 函數中。如果您想掃描更多，只需去 Google 搜尋「台灣中型100成分股 代碼」，將代碼複製進去即可（記得加上 `.TW`）。")
