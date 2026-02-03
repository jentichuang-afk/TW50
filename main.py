import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- 1. 頁面設定 ---
st.set_page_config(page_title="股票大師：智能選股雷達 (150大)", layout="wide", page_icon="📡")
st.title("📡 股票大師：策略 2 (RSI + 200MA) 全市場掃描")

# --- 2. 核心數據處理 ---
def get_target_tickers():
    # 台灣前 150 大權值股 (0050 + 0051 成分股集合)
    # 包含半導體、AI供應鏈、金融、航運、傳產龍頭
    tickers = [
        # --- 台灣50 (權值龍頭) ---
        "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2303.TW", "2881.TW", "2882.TW", "2891.TW", "2886.TW", "2884.TW",
        "2382.TW", "2885.TW", "2892.TW", "2207.TW", "2357.TW", "2890.TW", "1216.TW", "2912.TW", "2002.TW", "2880.TW",
        "2883.TW", "2327.TW", "2345.TW", "2379.TW", "3034.TW", "5880.TW", "2395.TW", "3008.TW", "2887.TW", "1101.TW",
        "3045.TW", "2801.TW", "2412.TW", "6505.TW", "3711.TW", "2603.TW", "3037.TW", "5871.TW", "2354.TW", "4904.TW",
        "2324.TW", "5876.TW", "2408.TW", "9910.TW", "2105.TW", "1303.TW", "1301.TW", "1326.TW", "3017.TW", "2609.TW",
        # --- 中型100 (成長潛力) ---
        "2356.TW", "3231.TW", "2376.TW", "2383.TW", "2353.TW", "2409.TW", "3481.TW", "2615.TW", "1102.TW", "1402.TW",
        "2474.TW", "4938.TW", "9904.TW", "9945.TW", "2006.TW", "1605.TW", "2313.TW", "2368.TW", "3035.TW", "3443.TW",
        "3661.TW", "6669.TW", "2301.TW", "2337.TW", "2344.TW", "2347.TW", "2360.TW", "2377.TW", "2385.TW", "2449.TW",
        "2492.TW", "2498.TW", "2542.TW", "2606.TW", "2610.TW", "2618.TW", "2809.TW", "2812.TW", "2834.TW", "2845.TW",
        "2867.TW", "2888.TW", "2889.TW", "2903.TW", "2915.TW", "3036.TW", "3044.TW", "3189.TW", "3293.TW", "3532.TW",
        "3533.TW", "3653.TW", "3702.TW", "3706.TW", "4919.TW", "4958.TW", "4961.TW", "4966.TW", "5269.TW", "5347.TWO",
        "5483.TWO", "5522.TW", "5871.TW", "6005.TW", "6176.TW", "6213.TW", "6239.TW", "6269.TW", "6271.TW", "6278.TW",
        "6285.TW", "6409.TW", "6415.TW", "6443.TW", "6472.TW", "6515.TW", "6531.TW", "6533.TW", "6669.TW", "6770.TW",
        "6781.TW", "8046.TW", "8069.TW", "8150.TW", "8299.TW", "8436.TW", "8454.TW", "8464.TW", "9914.TW", "9917.TW",
        "9921.TW", "9933.TW", "9941.TW", "9958.TW", "1504.TW", "1513.TW", "1519.TW", "1560.TW", "1590.TW", "1722.TW"
    ]
    # 去除重複並排序
    tickers = sorted(list(set(tickers)))
    return tickers

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
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 下載數據 (長度足夠計算 MA200)
    start_date = datetime.now() - timedelta(days=400)
    end_date = datetime.now() + timedelta(days=1)
    
    status_text.text(f"正在連線 Yahoo Finance 下載 {len(tickers)} 檔股票數據...")
    
    try:
        # 這裡為了穩定性，我們將 150 檔分成 3 批次下載，避免一次請求過大被擋
        batch_size = 50
        all_data = pd.DataFrame()
        
        for i in range(0, len(tickers), batch_size):
            batch_tickers = tickers[i:i + batch_size]
            status_text.text(f"正在下載第 {i+1} ~ {min(i+batch_size, len(tickers))} 檔... (請稍候)")
            batch_data = yf.download(batch_tickers, start=start_date, end=end_date, group_by='ticker', progress=False)
            
            # 合併數據 (處理 MultiIndex)
            if all_data.empty:
                all_data = batch_data
            else:
                all_data = pd.concat([all_data, batch_data], axis=1)

        status_text.text("數據下載完成，正在進行策略運算...")
        
        total = len(tickers)
        for i, ticker in enumerate(tickers):
            progress_bar.progress((i + 1) / total)
            
            try:
                # 容錯處理：有些股票可能下載失敗
                if ticker not in all_data.columns.get_level_values(0):
                    continue
                    
                df = all_data[ticker].copy()
                
                if df.empty or len(df) < 200:
                    continue
                    
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df = df.dropna(subset=['Close'])
                
                # 計算指標
                df['MA200'] = df['Close'].rolling(200).mean()
                
                # RSI (Simple Moving Average approximation for speed)
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
                
                # --- 策略 2 邏輯 ---
                
                # 🟢 買入條件：股價 > 200MA (長多) 且 RSI < 30 (超賣)
                if price > ma200 and rsi < 30:
                    dist_ma200 = (price - ma200) / ma200 * 100
                    results_buy.append({
                        "代碼": ticker.replace(".TW", "").replace(".TWO", ""),
                        "日期": date_str,
                        "收盤價": f"{price:.2f}",
                        "RSI": f"{rsi:.1f} 🔥",
                        "200MA": f"{ma200:.2f}",
                        "乖離率": f"{dist_ma200:.1f}%",
                        "狀態": "長多回檔 (強烈買訊)"
                    })
                
                # 🟡 觀察名單：股價 > 200MA 且 RSI < 40
                elif price > ma200 and rsi < 40:
                     dist_ma200 = (price - ma200) / ma200 * 100
                     results_buy.append({
                        "代碼": ticker.replace(".TW", "").replace(".TWO", ""),
                        "日期": date_str,
                        "收盤價": f"{price:.2f}",
                        "RSI": f"{rsi:.1f}",
                        "200MA": f"{ma200:.2f}",
                        "乖離率": f"{dist_ma200:.1f}%",
                        "狀態": "觀察中 (RSI < 40)"
                    })

                # 🔴 賣出條件：RSI > 70
                if rsi > 70:
                    results_sell.append({
                        "代碼": ticker.replace(".TW", "").replace(".TWO", ""),
                        "日期": date_str,
                        "收盤價": f"{price:.2f}",
                        "RSI": f"{rsi:.1f} ⚠️",
                        "200MA": f"{ma200:.2f}",
                        "狀態": "過熱 (注意風險)"
                    })

            except Exception as e:
                continue

        status_text.text("全市場掃描完成！")
        return pd.DataFrame(results_buy), pd.DataFrame(results_sell)

    except Exception as e:
        st.error(f"下載失敗，可能是網路不穩，請重試。錯誤: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 4. 主介面 ---
st.markdown("""
### 策略 2：RSI + 200MA 長線保護短線
* **掃描範圍**：台灣 50 + 中型 100 (約 150 檔熱門股)
* **✅ 買進條件**：股價在 **200MA (年線)** 之上，且 **RSI < 30** (或 40)。
* **❌ 賣出條件**：**RSI > 70** (短線過熱)。
""")

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🚀 開始掃描全市場 (150檔)", type="primary"):
        tickers = get_target_tickers()
        df_buy, df_sell = scan_market(tickers)
        
        st.session_state['df_buy'] = df_buy
        st.session_state['df_sell'] = df_sell

# 顯示結果
if 'df_buy' in st.session_state:
    tab1, tab2 = st.tabs(["🟢 潛力買點 (回後買上漲)", "🔴 潛力賣點 (短線過熱)"])
    
    with tab1:
        if not st.session_state['df_buy'].empty:
            st.success(f"共找到 {len(st.session_state['df_buy'])} 檔符合條件！")
            st.dataframe(st.session_state['df_buy'], use_container_width=True)
            st.markdown("💡 **解讀**：這些股票長線趨勢向上 (MA200 支撐)，但短線跌深了。請點擊股票代碼，回到「技術分析」分頁確認 K 線型態。")
        else:
            st.info("目前沒有股票符合「長多回檔 (RSI<40)」的條件。")

    with tab2:
        if not st.session_state['df_sell'].empty:
            st.warning(f"共找到 {len(st.session_state['df_sell'])} 檔過熱股！")
            st.dataframe(st.session_state['df_sell'], use_container_width=True)
            st.markdown("💡 **解讀**：這些股票短線 RSI 過高，隨時可能回檔整理。")
        else:
            st.info("目前沒有股票 RSI > 70。")
