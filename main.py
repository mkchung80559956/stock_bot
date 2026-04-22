import os
import aiocron
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from sentinel_engine import get_pro_analysis

# 從變數讀取 (絕對不要寫死在程式碼)
TOKEN = os.getenv("TELEGRAM_TOKEN")
RAW_IDS = os.getenv("TELEGRAM_CHAT_ID", "")
USER_MAP = {i.split(":")[0].strip(): i.split(":")[1].strip() for i in RAW_IDS.split(",") if ":" in i}
ALLOWED_IDS = list(USER_MAP.keys())
WATCHLIST = [s.strip() for s in os.getenv("WATCHLIST", "").split(",") if s.strip()]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    if cid not in ALLOWED_IDS: return
    
    text = update.message.text.strip().upper()
    symbol = f"{text}.TW" if text.isdigit() else text
    res = get_pro_analysis(symbol)
    
    if "error" in res:
        await update.message.reply_text(f"❌ {res['error']}")
    else:
        user_name = USER_MAP.get(cid, "老友")
        caption = (f"👋 {user_name}，決策建議如下：\n"
                   f"🎯 {res['symbol']} (${res['price']})\n勝率：{res['win_rate']} | 分數：{res['score']}\n"
                   f"⚖️ 建議比重：{res['weight']}\n🎬 行動：{res['action']}\n"
                   f"🛑 停損：{res['stop']} | 💎 停利：{res['tp']}")
        await context.bot.send_photo(chat_id=cid, photo=res['plot'], caption=caption)

@aiocron.crontab('40 06 * * 1-5')
async def daily_push():
    from telegram import Bot
    bot = Bot(TOKEN)
    for s in WATCHLIST:
        data = get_pro_analysis(s)
        if "error" not in data and int(data['score'][0]) >= 3:
            for cid in ALLOWED_IDS:
                await bot.send_photo(chat_id=cid, photo=data['plot'], caption=f"🔔 觸發高分共振：{s}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
