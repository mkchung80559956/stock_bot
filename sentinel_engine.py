import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime, timedelta
import io

def get_pro_analysis(symbol):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 250: return {"error": "數據不足"}

        # --- A. 指標精算 (不依賴 pandas_ta) ---
        # 1. CCI 計算
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['sma_tp'] = df['TP'].rolling(14).mean()
        df['mad'] = df['TP'].rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
        df['CCI'] = (df['TP'] - df['sma_tp']) / (0.015 * df['mad'] + 1e-6)
        
        # 2. EMA 200 (手動計算)
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # 3. RSI (手動計算)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # 4. ATR (手動計算)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        # --- B. 剩餘邏輯 (回測、評分、繪圖) 與之前完全相同 ---
        # ... (此處接續之前的回測與繪圖程式碼)
