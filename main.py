import os
import sys
import asyncio
from telegram.ext import ApplicationBuilder, MessageHandler, filters
TOKEN = os.getenv("TELEGRAM_TOKEN")
RAW_IDS = os.getenv("TELEGRAM_CHAT_ID", "")

# ... (保留你之前的 handle_message 和 auto_scan 函數) ...

if __name__ == '__main__':
    # 1. 建立應用程式
    if not TOKEN:
        print("❌ 錯誤：找不到 TELEGRAM_TOKEN 環境變數")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    
    # 2. 註冊訊息處理器 (回覆代號用)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # 3. 環境偵測與執行
    # 判斷是否為 GitHub Actions 環境
    is_github_action = os.getenv("GITHUB_ACTIONS") == "true"

    if is_github_action:
        print("🚀 偵測到 GitHub Actions 環境：執行一次性定時掃描任務...")
        # 建立一個新的事件迴圈來跑一次性推播
        loop = asyncio.get_event_loop()
        # 這裡執行你原本定義的 auto_scan 函數內容
        loop.run_until_complete(auto_scan()) 
        print("✅ 掃描任務已完成，程式正常退出。")
        # 這裡不跑 run_polling()，所以不會有 Conflict 報錯
    else:
        print("✅ 偵測到常駐環境：啟動 Polling 模式...")
        # 只有在非 Actions 環境下才啟動監聽，防止 Conflict
        app.run_polling()
