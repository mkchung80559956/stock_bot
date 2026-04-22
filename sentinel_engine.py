import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import mplfinance as mpf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime, timedelta
import io

def get_pro_analysis(symbol):
    try:
        # 1. 數據獲取
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 250:
            return {"error": "數據樣本不足，無法進行專業分析。"}

        # 2. 指標精算 (對標三竹)
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['sma_tp'] = df['TP'].rolling(14).mean()
        df['mad'] = df['TP'].rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
        df['CCI'] = (df['TP'] - df['sma_tp']) / (0.015 * df['mad'] + 1e-6)
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['RSI'] = ta.rsi(df['Close'], length=14)

        # 3. 滾動回測 (預估勝率)
        test_df = df.copy()
        test_df['sig'] = (test_df['CCI'] > 100) & (test_df['CCI'].shift(1) <= 100)
        records = [1 if test_df['Close'].iloc[i+6] > test_df['Close'].iloc[i+1] else 0 
                   for i in range(len(test_df)-6) if test_df['sig'].iloc[i]]
        win_rate = np.mean(records) if records else 0.5
        
        # 4. 評分與比重邏輯
        last = df.iloc[-1]
        score = sum([last['CCI'] > 100, last['Close'] > last['EMA200'], 
                     last['RSI'] > 50, last['CCI'] > 150]) # 權重可微調
        
        weight, action = ("30-50%", "✅ 積極切入") if score >= 3 and win_rate >= 0.6 else \
                         ("15-20%", "⚠️ 小量試單") if score >= 2 and win_rate >= 0.5 else \
                         ("0%", "持續觀望")

        # 5. 繪製 K 線圖表
        buf = io.BytesIO()
        plot_df = df.tail(60).copy()
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='inherit')
        style = mpf.make_mpf_style(base_mpf_style='charles', marketcolors=mc, gridstyle='--')
        apds = [
            mpf.make_addplot(plot_df['EMA200'], color='blue', width=1),
            mpf.make_addplot(plot_df['CCI'], type='bar', panel=1, color=['red' if x < -100 else 'green' if x > 100 else 'gray' for x in plot_df['CCI']])
        ]
        mpf.plot(plot_df, type='candle', style=style, addplot=apds, volume=True, 
                 savefig=dict(fname=buf, dpi=100, bbox_inches='tight'))
        buf.seek(0)

        return {
            "symbol": symbol, "price": round(last['Close'], 2), "win_rate": f"{round(win_rate*100, 1)}%",
            "score": f"{score}/4", "weight": weight, "action": action, "plot": buf,
            "stop": round(last['Close'] - (last['ATR']*1.5), 2), "tp": round(last['Close'] + (last['ATR']*3), 2)
        }
    except Exception as e:
        return {"error": str(e)}
