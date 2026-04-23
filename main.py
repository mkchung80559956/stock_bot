import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from sentinel_engine import get_pro_analysis

# --- 讀取環境變數 ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
# 支援多 ID 格式： "123,456,789"
RAW_IDS = os.getenv("TELEGRAM_CHAT_ID", "")
ALLOWED_IDS = [id.strip() for id in RAW_IDS.split(",") if id.strip()]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 權限檢查：檢查發話者的 ID 是否在白名單中
    current_chat_id = str(update.effective_chat.id)
    
    if ALLOWED_IDS and (current_chat_id not in ALLOWED_IDS):
        await update.message.reply_text("⛔ 您不在授權名單中，無法使用此機器人。")
        return

    raw_text = update.message.text.strip().upper()
    # 支援代碼補齊
    symbol = f"{raw_text}.TW" if raw_text.isdigit() else raw_text
    
    await update.message.reply_text(f"🔍 正在為您進行 Sentinel 量價分析：`{symbol}`...")
    
    data = get_pro_analysis(symbol)
    if data:
        msg = (
            f"🛡️ *Sentinel Pro 分析報告* ({symbol})\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"💰 現價：`{data['price']}`\n"
            f"📊 評分：`{data['score']}/7` ({data['trend']})\n"
            f"🚀 訊號：{data['cci_sig']}\n"
            f"🚨 風險：{data['warning'] if data['warning'] else '✅ 正常'}\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"🛡️ 停損：`{data['stop_loss']}`\n"
            f"🎯 目標：`{data['target']}`"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')
        
        # 【進階】如果有其他管理員，可以在有人查詢時通知管理員 (選配功能)
        # for admin_id in ALLOWED_IDS:
        #     if admin_id != current_chat_id:
        #         await context.bot.send_message(chat_id=admin_id, text=f"🔔 授權用戶 {current_chat_id} 查詢了 {symbol}")
                
    else:
        await update.message.reply_text("❌ 數據抓取失敗。請確保輸入正確代碼 (如: 2330 或 2603.TW)")

if __name__ == '__main__':
    if not TOKEN:
        print("錯誤：找不到 TELEGRAM_TOKEN 環境變數！")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print(f"Sentinel Bot 已啟動。目前授權 ID 數量：{len(ALLOWED_IDS)}")
    app.run_polling()
