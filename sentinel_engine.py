import os
import requests
import pandas as pd
import io
import matplotlib.pyplot as plt

def get_pro_analysis(symbol):
    print(f"🔍 DEBUG: 開始處理 {symbol}")
    token = os.getenv("FINMIND_TOKEN")
    
    # 1. 處理代號：FinMind 台股只需要數字 (2330.TW -> 2330)
    stock_id = symbol.replace(".TW", "").replace(".tw", "")
    
    try:
        # 2. 呼叫 FinMind API
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": "2024-01-01",
            "token": token,
        }
        
        print(f"📡 DEBUG: 正在請求 FinMind API...")
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        
        if data.get("msg") != "success":
            print(f"❌ DEBUG: API 回傳失敗: {data.get('msg')}")
            return {"error": f"API 錯誤: {data.get('msg')}"}
            
        # 3. 轉換為 DataFrame
        df = pd.DataFrame(data["data"])
        if df.empty:
            print(f"⚠️ DEBUG: {symbol} 沒抓到資料")
            return {"error": "找不到股票數據"}

        # 4. 欄位轉換（必須符合你原本指標計算的名稱）
        df = df.rename(columns={
            "date": "Date",
            "open": "Open",
            "max": "High",
            "min": "Low",
            "close": "Close",
            "trading_volume": "Volume"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        
        print(f"✅ DEBUG: 數據轉換成功，共 {len(df)} 筆資料")
       

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
