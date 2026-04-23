import os
import sys
import asyncio
from datetime import datetime
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from sentinel_engine import get_pro_analysis 

# 1. 環境變數讀取與預設值
TOKEN = os.getenv("TELEGRAM_TOKEN")
RAW_IDS = os.getenv("TELEGRAM_CHAT_ID", "")
WATCHLIST_RAW = os.getenv("WATCHLIST", "2330.TW")
WATCHLIST = [s.strip() for s in WATCHLIST_RAW.split(",") if s.strip()]

# 2. 解析用戶 ID (確保轉為整數型態以利 Telegram 發送)
ALLOWED_IDS = []
if RAW_IDS:
    for item in RAW_IDS.split(","):
        if ":" in item:
            try:
                # 格式: "123456:暱稱" -> 取得 123456
                user_id = int(item.split(":")[0].strip())
                ALLOWED_IDS.append(user_id)
            except:
                continue

# --- 功能函數 ---

async def auto_scan():
    """GitHub Actions 專用：一次性掃描並推播"""
    from telegram import Bot
    if not TOKEN or not ALLOWED_IDS:
        print(f"❌ 關鍵變數缺失: TOKEN={bool(TOKEN)}, IDS={ALLOWED_IDS}")
        return
    
    bot = Bot(TOKEN)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 【心跳測試】不論有無訊號先發一段文字，確認連線正常
    for cid in ALLOWED_IDS:
        try:
            await bot.send_message(chat_id=cid, text=f"🔍 Sentinel 掃描啟動\n⏰ 時間：{now_str}\n清單：{WATCHLIST}")
            print(f"✅ 已發送啟動通知至 {cid}")
        except Exception as e:
            print(f"❌ 無法發送通知至 {cid}: {e}")

    # 【核心掃描】
    for s in WATCHLIST:
        print(f"🔄 正在分析 {s}...")
        try:
            data = get_pro_analysis(s)
            # 測試階段：只要沒報錯就發圖（門檻設為 -1）
            if "error" not in data:
                for cid in ALLOWED_IDS:
                    await bot.send_photo(
                        chat_id=cid,
                        photo=data['plot'],
                        caption=f"📊 {s} 分析報告\n⭐️ 評分：{data.get('score', ['?'])[0]}\n🎯 建議：{data.get('action', 'N/A')}"
                    )
                    print(f"✅ 成功發送圖片: {s}")
        except Exception as e:
            print(f"❌ 分析或發送失敗 {s}: {e}")

async def handle_message(update, context):
    """Railway 專用：處理手動查詢"""
    if not update.message or not update.message.text: return
    text = update.message.text.upper().strip()
    
    # 簡易權限檢查
    if update.effective_user.id not in ALLOWED_IDS:
        await update.message.reply_text("🚫 您不在授權名單中。")
        return

    await update.message.reply_text(f"⏳ 正在分析 {text}，請稍候...")
    data = get_pro_analysis(text)
    if "error" in data:
        await update.message.reply_text(f"❌ 查無資料或格式錯誤: {text}")
    else:
        await update.message.reply_photo(photo=data['plot'], caption=f"🎯 {text} 即時分析結果")

# --- 執行入口 ---

if __name__ == '__main__':
    # 啟動前的最後檢查
    print(f"--- 啟動檢查 ---")
    print(f"TOKEN 狀態: {'已讀取' if TOKEN else '未設定 ❌'}")
    print(f"授權 ID 數量: {len(ALLOWED_IDS)}")
    print(f"----------------")

    if not TOKEN:
        print("❌ 錯誤：TELEGRAM_TOKEN 未設定，程式終止。")
        sys.exit(1)

    # 建立 Application
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # 辨識環境
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("🚀 偵測到 GitHub 環境：執行一次性掃描任務...")
        asyncio.run(auto_scan())
        print("✅ 任務結束，程式退出。")
    else:
        print("✅ 偵測到常駐環境：啟動 Polling 監聽...")
        app.run_polling()
