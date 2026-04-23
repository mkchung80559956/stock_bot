import os
import sys
import asyncio
from datetime import datetime
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from sentinel_engine import get_pro_analysis 

# 1. 全域變數定義
TOKEN = os.getenv("TELEGRAM_TOKEN")
RAW_IDS = os.getenv("TELEGRAM_CHAT_ID", "")
WATCHLIST = [s.strip() for s in os.getenv("WATCHLIST", "2330.TW").split(",") if s.strip()]

USER_MAP = {item.split(":")[0].strip(): item.split(":")[1].strip() for item in RAW_IDS.split(",") if ":" in item}
ALLOWED_IDS = list(USER_MAP.keys())

# --- 函數定義 ---

async def handle_message(update, context):
    # 這裡保留你原本處理單次查詢的邏輯
    pass

async def auto_scan():
    from telegram import Bot
    if not TOKEN: 
        print("❌ 找不到 TOKEN，停止掃描")
        return
    
    bot = Bot(TOKEN)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # --- 🛠️ 核心測試：啟動通知 (加在這裡) ---
    for cid in ALLOWED_IDS:
        try:
            # 使用 int(cid) 確保 ID 格式正確
            await bot.send_message(chat_id=int(cid), text=f"🔍 Sentinel 掃描任務已啟動...\n⏰ 台灣時間：{now_str}")
            print(f"✅ 已發送啟動通知給 {cid}")
        except Exception as e:
            print(f"❌ 無法發送通知給 {cid}，錯誤原因: {e}")

    # --- 股票掃描邏輯 ---
    for s in WATCHLIST:
        print(f"🔄 正在分析 {s}...")
        data = get_pro_analysis(s)
        
        # 💡 除錯建議：暫時把 >= 5 改成 >= 0，確保圖片一定會發送
        if "error" not in data and int(data['score'][0]) >= 0: 
            for cid in ALLOWED_IDS:
                try:
                    await bot.send_photo(
                        chat_id=int(cid), 
                        photo=data['plot'], 
                        caption=f"📊 {s} 分析報告\n🎯 動作建議：{data['action']}\n⭐️ 綜合評分：{data['score'][0]}"
                    )
                    print(f"✅ 圖表發送成功: {s}")
                except Exception as e:
                    print(f"❌ 圖表發送失敗 {s}: {e}")

# --- 執行入口 ---
if __name__ == '__main__':
    if not TOKEN:
        print("❌ 錯誤：環境變數 TELEGRAM_TOKEN 未設定")
        sys.exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    if os.getenv("GITHUB_ACTIONS") == "true":
        print("🚀 GitHub Actions 模式：執行一次性掃描...")
        asyncio.run(auto_scan()) 
        print("✅ 任務結束")
    else:
        print("✅ 常駐模式：啟動監聽中...")
        app.run_polling()
