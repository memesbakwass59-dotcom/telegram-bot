import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = '8830625955:AAGyQEyDiOHP97Dv9DFYsdvoc5jJC1MQBR4'

# आपके दोनों चैनल और ग्रुप
CHANNELS = [
    ('@quantixcashflow', 'https://t.me/quantixcashflow'),
    ('@Quantix_CashFlow', 'https://t.me/Quantix_CashFlow'),
] 

# मीडिया को स्टोर करने के लिए डेटाबेस
media_database = {}
media_counter = 0

async def check_all_subscriptions(user_id: int, context) -> bool:
    """चेक करता है कि यूजर ने दोनों चैनल जॉइन किए हैं या नहीं"""
    for channel, _ in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Error checking subscription for {channel}: {e}")
            return False
    return True

async def delete_message_after_delay(context, chat_id, message_id, delay_seconds):
    """24 घंटे बाद वीडियो/मीडिया को ऑटोमैटिक डिलीट करने के लिए फंक्शन"""
    await asyncio.sleep(delay_seconds)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Could not auto-delete message: {e}")

async def handle_admin_upload(update, context):
    """जब आप बोट पर वीडियो भेजेंगे, यह तुरंत यूनिक लिंक जनरेट करके देगा"""
    global media_counter
    message = update.message
    
    media_counter += 1
    media_id = f"media_{media_counter}"
    
    media_type = None
    file_id = None
    
    if message.video:
        media_type = "video"
        file_id = message.video.file_id
    elif message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
    else:
        return

    # मीडिया डिटेल्स सेव करें
    media_database[media_id] = {
        "type": media_type,
        "file_id": file_id,
        "caption": message.caption or "🎉 **Access Granted!** Here is your video content 🔥"
    }

    bot_username = context.bot.username
    unique_link = f"https://t.me/{bot_username}?start={media_id}"
    
    await message.reply_text(
        f"✅ **Media Uploaded Successfully!**\n\n"
        f"🔗 **Your Shareable Link:**\n`{unique_link}`",
        parse_mode="Markdown"
    )

async def send_specific_media(chat_id, media_id, context):
    """यूजर को मीडिया भेजेगा और 24 घंटे बाद डिलीट होने का टास्क सेट करेगा"""
    media_data = media_database.get(media_id)
    
    if not media_data:
        await context.bot.send_message(chat_id=chat_id, text="❌ This media link is invalid or has expired.")
        return

    m_type = media_data["type"]
    f_id = media_data["file_id"]
    cap = media_data["caption"]

    sent_msg = None
    if m_type == "video":
        sent_msg = await context.bot.send_video(chat_id=chat_id, video=f_id, caption=cap, parse_mode="Markdown")
    elif m_type == "photo":
        sent_msg = await context.bot.send_photo(chat_id=chat_id, photo=f_id, caption=cap, parse_mode="Markdown")
    elif m_type == "document":
        sent_msg = await context.bot.send_document(chat_id=chat_id, document=f_id, caption=cap, parse_mode="Markdown")

    # 24 घंटे (86400 सेकंड्स) बाद मैसेज डिलीट करने के लिए बैकग्राउंड टास्क शुरू करें
    if sent_msg:
        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 86400))

async def start(update, context):
    user_id = update.effective_user.id
    args = context.args  
    
    if not args:
        await update.message.reply_text("👋 Welcome! Send any media file to this chat to generate a unique promotion link.")
        return

    media_id = args[0]
    if media_id not in media_database:
        await update.message.reply_text("❌ Invalid or expired media link.")
        return

    # चेक करें कि यूजर ने चैनल जॉइन किया है या नहीं
    is_joined = await check_all_subscriptions(user_id, context)
    
    if not is_joined:
        keyboard = []
        for i in range(0, len(CHANNELS), 2):
            row = []
            row.append(InlineKeyboardButton("Join Channel 1 ↗", url=CHANNELS[i][1]))
            if i + 1 < len(CHANNELS):
                row.append(InlineKeyboardButton("Join Channel 2 ↗", url=CHANNELS[i+1][1]))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔓 Claim / Verify", callback_data=f"claim_{media_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            "👋 **Hello Dear, Welcome To Our Bot!**\n\n"
            "🛑 **You must join all required channels below to access this media.**\n\n"
            "💣 **After joining both channels, click on 'Claim / Verify'.**"
        )
        
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    # अगर पहले से जॉइन है तो डायरेक्ट मीडिया भेजें
    await send_specific_media(user_id, media_id, context)

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data  
    
    if data.startswith("claim_"):
        media_id = data.split("_", 1)[1] 
        is_joined = await check_all_subscriptions(user_id, context)
        
        if is_joined:
            try:
                await query.message.delete() # जॉइन करने पर प्रॉपर बॉक्स गायब हो जाएगा
            except Exception:
                pass
            
            await send_specific_media(user_id, media_id, context)
        else:
            # अगर जॉइन नहीं किया है तो इंग्लिश में अलर्ट दिखेगा
            await query.answer("❌ You haven't joined all channels yet! Please join both channels and try again.", show_alert=True)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^claim_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.DOCUMENT, handle_admin_upload))

    print("Bot is running successfully with auto-delete & unique links...")
    app.run_polling()

if __name__ == '__main__':
    main()
