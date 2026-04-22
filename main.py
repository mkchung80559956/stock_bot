import os
import sys
import asyncio
import aiocron
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from sentinel_engine import get_pro_analysis # 確保你有 import 你的分析引擎

# 1. 這裡必須放在最外層，確保所有函數都讀得到
TOKEN = os.getenv("TELEGRAM_TOKEN")
RAW_IDS = os.getenv("TELEGRAM_CHAT_ID", "")
WATCHLIST = [s.strip() for s in os.getenv("WATCHLIST", "2330.TW").split(",") if s.strip()]

# 解析用戶地圖
USER_MAP = {item.split(":")[0].strip(): item.split(":")[1].strip() for item in RAW_IDS.split(",") if ":" in item}
ALLOWED_IDS = list(USER_MAP.keys())

# --- 你的 handle_message 與 auto_scan 函數放在這裡 ---
async def handle_message(update, context):
    # ... 原有邏輯 ...
    pass

async def auto_scan():
    # 注意：這裡面會用到 TOKEN，所以 TOKEN 必須定義在全域
    from telegram import Bot
    if not TOKEN: return
    bot = Bot(TOKEN)
    for s in WATCHLIST:
        data = get_pro_analysis(s)
        if "error" not in data and int(data['score'][0]) >= 5:
            for cid in ALLOWED_IDS:
                await bot.send_photo(chat_id=cid, photo=data['plot'], caption=f"🔔 發現訊號：{s}")

# --- 執行入口 ---
if __name__ == '__main__':
    # 安全檢查：如果沒設 TOKEN 直接報錯退出
    if not TOKEN:
        print("❌ 錯誤：環境變數 TELEGRAM_TOKEN 未設定")
        sys.exit(1)

    # 建立 Application
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # 環境偵測
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("🚀 GitHub Actions 模式：執行一次性掃描...")
        # 這是關鍵：一次性執行 async 函數後退出
        asyncio.run(auto_scan()) 
        print("✅ 任務結束")
    else:
        print("✅ 常駐模式：啟動監聽中...")
        app.run_polling()
