import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # 👈 關鍵：防止雲端環境報錯
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime, timedelta
import io

def get_pro_analysis(symbol):
    try:
        # 1. 抓取數據 (使用 auto_adjust 確保價格連貫)
        df = yf.download(symbol, period="2y", interval="1d", progress=False, auto_adjust=True)

        # 2. 【核心修復】強行扁平化多重索引 (針對 yf 0.2.50+)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 3. 欄位名稱標準化 (防止出現 lowercase 的情況)
        df.columns = [c.title() for c in df.columns]

        if df.empty or len(df) < 50:
            return {"error": f"代號 `{symbol}` 數據抓取失敗。"}

        # 4. 數據轉型與清理
        df = df.astype(float).dropna()
        
        # --- 下方接你原本的指標計算 (TP, CCI, EMA200...) ---



        # 1. CCI 計算 (對標台股軟體公式)
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['sma_tp'] = df['TP'].rolling(14).mean()
        df['mad'] = df['TP'].rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
        df['CCI'] = (df['TP'] - df['sma_tp']) / (0.015 * df['mad'] + 1e-6)
        
        # 2. EMA 200 (趨勢過濾)
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # 3. RSI 14 (動能偵測)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

        # 4. ATR 14 (風險控管)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        # --- B. 滾動回測與決策邏輯 ---
        test_df = df.copy().tail(250)
        test_df['sig'] = (test_df['CCI'] > 100) & (test_df['CCI'].shift(1) <= 100)
        records = []
        for i in range(len(test_df) - 6):
            if test_df['sig'].iloc[i]:
                # 簡單模擬：隔日進場，5日後離場
                records.append(1 if test_df['Close'].iloc[i+6] > test_df['Close'].iloc[i+1] else 0)
        
        win_rate = np.mean(records) if records else 0.5
        
        last = df.iloc[-1]
        score = 0
        if last['CCI'] > 100: score += 2
        if last['Close'] > last['EMA200']: score += 2
        if last['RSI'] > 50: score += 1
        
        # 資金分配比重建議
        weight, action = "0%", "持續觀望"
        if score >= 4:
            if win_rate >= 0.6: weight, action = "30%-50%", "✅ 積極切入"
            elif win_rate >= 0.5: weight, action = "15%-20%", "⚠️ 小量試單"
            else: weight, action = "5%", "🐢 謹慎操作"

        # --- C. 專業 K 線圖繪製 ---
        plot_df = df.tail(60).copy()
        # 定義 CCI 色塊
        cci_colors = ['#26a69a' if x > 100 else '#ef5350' if x < -100 else '#b2b5be' for x in plot_df['CCI']]
        
        apds = [
            mpf.make_addplot(plot_df['EMA200'], color='#2962ff', width=1.5), # EMA200 藍線
            mpf.make_addplot(plot_df['CCI'], type='bar', panel=1, color=cci_colors, ylabel='CCI')
        ]
        
        buf = io.BytesIO()
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='inherit')
        style = mpf.make_mpf_style(base_mpf_style='charles', marketcolors=mc, gridstyle='--')
        
        mpf.plot(plot_df, type='candle', style=style, addplot=apds, volume=True, 
                 panel_ratios=(4,2,1), savefig=dict(fname=buf, dpi=100, bbox_inches='tight'))
        buf.seek(0)

        return {
            "symbol": symbol,
            "price": round(last['Close'], 2),
            "win_rate": f"{round(win_rate*100, 1)}%",
            "score": f"{score}/7",
            "weight": weight,
            "action": action,
            "plot": buf,
            "stop_loss": round(last['Close'] - (last['ATR'] * 1.5), 2),
            "take_profit": round(last['Close'] + (last['ATR'] * 3), 2),
            "entry_window": (datetime.now() + timedelta(days=1)).strftime("%m/%d 09:00-09:30")
        }
    except Exception as e:
        return {"error": str(e)}
