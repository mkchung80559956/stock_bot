import os
import requests
import pandas as pd
import io
from datetime import datetime, timedelta

def get_pro_analysis(symbol):
    # 這裡強迫在函數內 import，確保 GitHub 環境一定抓得到
    try:
        import numpy as np
        import mplfinance as mpf
        import matplotlib.pyplot as plt
    except ImportError as e:
        return {"error": f"缺少套件: {str(e)}"}

    token = os.getenv("FINMIND_TOKEN")
    stock_id = symbol.replace(".TW", "").replace(".tw", "")
    
    try:
        # 1. 抓取資料
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            "token": token,
        }
        
        res = requests.get(url, params=params, timeout=15)
        res_data = res.json()
        
        if res_data.get("msg") != "success" or not res_data.get("data"):
            return {"error": f"API 沒資料: {res_data.get('msg')}"}
            
        df = pd.DataFrame(res_data["data"])
        
        # 2. 格式轉換與檢查
        df = df.rename(columns={
            "date": "Date", "open": "Open", "max": "High",
            "min": "Low", "close": "Close", "trading_volume": "Volume"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        
        # 強制轉為數值，防止 FinMind 回傳字串導致計算崩潰
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()

        # 3. 技術指標 (簡化版確保不崩潰)
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['sma_tp'] = df['TP'].rolling(14).mean()
        df['mad'] = df['TP'].rolling(14).apply(lambda x: np.abs(x - x.mean()).mean(), raw=False)
        df['CCI'] = (df['TP'] - df['sma_tp']) / (0.015 * df['mad'] + 1e-6)

        # 4. 繪圖
        plot_df = df.tail(60)
        buf = io.BytesIO()
        
        # 設定 K 線顏色
        mc = mpf.make_marketcolors(up='r', down='g', inherit=True)
        s  = mpf.make_mpf_style(base_mpf_style='charles', marketcolors=mc)
        
        # 繪圖並存入緩衝區
        mpf.plot(plot_df, type='candle', style=s, volume=True, 
                 savefig=dict(fname=buf, dpi=100, bbox_inches='tight'))
        buf.seek(0)

        last = df.iloc[-1]
        return {
            "symbol": symbol,
            "price": round(last['Close'], 2),
            "score": "N/A",
            "action": "分析完成",
            "plot": buf
        }

    except Exception as e:
        # 如果出錯，至少要把錯誤訊息傳回去
        print(f"❌ 嚴重崩潰: {str(e)}")
        return {"error": f"代碼崩潰: {str(e)}"}
