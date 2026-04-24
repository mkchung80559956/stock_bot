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
    
    async with Bot(TOKEN) as bot:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 1. 先對所有授權用戶發送「啟動通知」
        for cid in ALLOWED_IDS:
            try:
                await bot.send_message(chat_id=cid, text=f"🔍 Sentinel 掃描啟動\n⏰ 時間：{now_str}\n清單：{WATCHLIST}")
            except Exception as e:
                print(f"❌ 無法通知用戶 {cid}: {e}")

        # 2. 開始分析股票並發送結果
        for s in WATCHLIST:
            print(f"🔄 正在分析 {s}...")
            try:
                data = get_pro_analysis(s) # 呼叫 sentinel_engine.py
                
                # 遍歷每個用戶發送分析結果
                for cid in ALLOWED_IDS:
                    if "error" in data:
                        # 如果失敗，回報具體錯誤（例如：數據源錯誤）
                        await bot.send_message(chat_id=cid, text=f"❌ {s} 分析失敗: {data['error']}")
                    else:
                        # 成功則發圖
                        data['plot'].seek(0)
                        await bot.send_photo(
                            chat_id=cid, 
                            photo=data['plot'], 
                            caption=f"📊 {s} 分析完成\n💰 現價：{data.get('price', 'N/A')}\n🎯 建議：{data.get('action', '無')}"
                        )
            except Exception as e:
                # 這是防止 sentinel_engine 內部的意外崩潰導致整個 main.py 停擺
                print(f"❌ 分析過程中發生非預期錯誤 {s}: {e}")
                for cid in ALLOWED_IDS:
                    await bot.send_message(chat_id=cid, text=f"💥 程式執行崩潰 ({s}): {str(e)}")

            except Exception as e:
                print(f"❌ 無法通知 {cid}: {e}")

        for s in WATCHLIST:
    data = get_pro_analysis(s)
    if "error" in data:
        # 如果失敗，也要發文字通知，不要默默消失！
        await bot.send_message(chat_id=cid, text=f"❌ {s} 分析失敗: {data['error']}")
    else:
        # 成功才發圖
        data['plot'].seek(0)
        await bot.send_photo(chat_id=cid, photo=data['plot'], caption=f"✅ {s} 完成")

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
