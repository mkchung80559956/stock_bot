import os
import requests
import pandas as pd
import numpy as np  # 👈 必加，否則 CCI/ATR 會崩潰
import io
import matplotlib.pyplot as plt
import mplfinance as mpf  # 👈 必加，否則繪圖會崩潰
from datetime import datetime, timedelta # 👈 必加，計算 entry_window 用

def get_pro_analysis(symbol):
    print(f"🔍 DEBUG: 開始處理 {symbol}")
    token = os.getenv("FINMIND_TOKEN")
    
    # FinMind 台股只需要數字
    stock_id = symbol.replace(".TW", "").replace(".tw", "")
    
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": "2024-01-01",
            "token": token,
        }
        
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        
        if data.get("msg") != "success":
            return {"error": f"API 錯誤: {data.get('msg')}"}
            
        df = pd.DataFrame(data["data"])
        if df.empty:
            return {"error": "找不到股票數據"}

        df = df.rename(columns={
            "date": "Date", "open": "Open", "max": "High",
            "min": "Low", "close": "Close", "trading_volume": "Volume"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        
        # --- A. 技術指標計算 ---
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['sma_tp'] = df['TP'].rolling(14).mean()
        # 修正 MAD 計算
        df['mad'] = df['TP'].rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
        df['CCI'] = (df['TP'] - df['sma_tp']) / (0.015 * df['mad'] + 1e-6)
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

        tr = pd.concat([df['High']-df['Low'], 
                        np.abs(df['High']-df['Close'].shift()), 
                        np.abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        # --- B. 決策邏輯 ---
        test_df = df.copy().tail(250)
        test_df['sig'] = (test_df['CCI'] > 100) & (test_df['CCI'].shift(1) <= 100)
        records = []
        for i in range(len(test_df) - 6):
            if test_df['sig'].iloc[i]:
                records.append(1 if test_df['Close'].iloc[i+5] > test_df['Close'].iloc[i] else 0)
        
        win_rate = np.mean(records) if records else 0.5
        last = df.iloc[-1]
        score = 0
        if last['CCI'] > 100: score += 2
        if last['Close'] > last['EMA200']: score += 2
        if last['RSI'] > 50: score += 1
        
        weight, action = "0%", "持續觀望"
        if score >= 3: # 稍微放寬門檻以利測試
            if win_rate >= 0.55: weight, action = "30%-50%", "✅ 積極切入"
            else: weight, action = "15%-20%", "⚠️ 小量試單"

        # --- C. 繪圖 ---
        plot_df = df.tail(60).copy()
        cci_colors = ['#26a69a' if x > 100 else '#ef5350' if x < -100 else '#b2b5be' for x in plot_df['CCI']]
        
        apds = [
            mpf.make_addplot(plot_df['EMA200'], color='#2962ff', width=1.0),
            mpf.make_addplot(plot_df['CCI'], type='bar', panel=1, color=cci_colors, ylabel='CCI')
        ]
        
        buf = io.BytesIO()
        mc = mpf.make_marketcolors(up='red', down='green', inherit=True)
        style = mpf.make_mpf_style(base_mpf_style='charles', marketcolors=mc)
        
        mpf.plot(plot_df, type='candle', style=style, addplot=apds, volume=True, 
                 panel_ratios=(4,2), savefig=dict(fname=buf, dpi=120), tight_layout=True)
        buf.seek(0)

        print(f"✅ {symbol} 分析完成")
        return {
            "symbol": symbol,
            "price": round(last['Close'], 1),
            "score": f"{score}/5",
            "weight": weight,
            "action": action,
            "plot": buf,
            "entry_window": (datetime.now() + timedelta(days=1)).strftime("%m/%d 09:00")
        }
    except Exception as e:
        print(f"❌ 崩潰詳細原因: {str(e)}") # 💡 讓 GitHub Actions 日誌顯示真正錯誤
        return {"error": str(e)}
