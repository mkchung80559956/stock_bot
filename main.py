import os
import sys
import asyncio
from datetime import datetime
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from sentinel_engine import get_pro_analysis 
from telegram import Bot # 💡 移至頂部

# ... (前段 1.環境變數 與 2.解析 ID 的程式碼保持不變) ...

# --- 修改後的 auto_scan 函數 ---
async def auto_scan():
    """GitHub Actions 專用：一次性掃描並推播"""
    if not TOKEN or not ALLOWED_IDS:
        print(f"❌ 關鍵變數缺失: TOKEN={bool(TOKEN)}, IDS={ALLOWED_IDS}")
        return
    
    # 💡 使用 async with bot 確保任務結束後連線正確關閉
    async with Bot(TOKEN) as bot:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for cid in ALLOWED_IDS:
            try:
                await bot.send_message(chat_id=cid, text=f"🔍 Sentinel 掃描啟動\n⏰ 時間：{now_str}\n清單：{WATCHLIST}")
            except Exception as e:
                print(f"❌ 無法通知 {cid}: {e}")

        for s in WATCHLIST:
            print(f"🔄 正在分析 {s}...")
            try:
                data = get_pro_analysis(s)
                if "error" not in data:
                    for cid in ALLOWED_IDS:
                        # 💡 關鍵：發送前重置圖片流的位置
                        data['plot'].seek(0)
                        await bot.send_photo(
                            chat_id=cid,
                            photo=data['plot'],
                            caption=f"📊 {s} 分析報告\n⭐️ 評分：{data.get('score', ['?'])[0]}\n🎯 建議：{data.get('action', 'N/A')}"
                        )
                    print(f"✅ 成功發送圖片: {s}")
            except Exception as e:
                print(f"❌ 分析失敗 {s}: {e}")

# ... (handle_message 函數保持不變) ...

# --- 修改後的執行入口 ---
if __name__ == '__main__':
    print(f"--- 啟動檢查 ---")
    print(f"TOKEN 狀態: {'已讀取' if TOKEN else '未設定 ❌'}")
    print(f"環境: {'GitHub Actions' if os.getenv('GITHUB_ACTIONS') == 'true' else 'General'}")
    print(f"----------------")

    if not TOKEN:
        print("❌ 錯誤：TELEGRAM_TOKEN 未設定。")
        sys.exit(1)

    # 💡 根據環境分流執行，避免衝突
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("🚀 偵測到 GitHub 環境：執行一次性掃描...")
        asyncio.run(auto_scan())
        print("🏁 任務完成，程式正常結束。")
    else:
        print("✅ 偵測到常駐環境：啟動 Polling 監聽...")
        # 💡 只有在此模式下才建立 app 物件
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.run_polling()
