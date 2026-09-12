import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = '8830625955:AAGyQEyDiOHP97Dv9DFYsdvoc5jJC1MQBR4'

# आपके दोनों अनिवार्य चैनल और ग्रुप
CHANNELS = [
    ('@quantixcashflow', 'https://t.me/quantixcashflow'),
    ('@Quantix_CashFlow', 'https://t.me/Quantix_CashFlow'),
] 

# डेटाबेस और स्टोरेज
media_database = {}
media_counter = 0
pinned_media = None  # डायरेक्ट /start करने वाले यूजर के लिए डिफ़ॉल्ट पिन मीडिया

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
    """24 घंटे (86400 सेकंड) बाद यूजर के पास भेजा गया मीडिया ऑटोमैटिक डिलीट कर देगा"""
    await asyncio.sleep(delay_seconds)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Could not auto-delete message: {e}")

async def handle_admin_upload(update, context):
    """जब आप (एडमिन) बोट पर मीडिया भेजेंगे, यह यूनिक लिंक देगा और इसे पिन मीडिया बना देगा"""
    global media_counter, pinned_media
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

    media_data = {
        "type": media_type,
        "file_id": file_id,
        "caption": message.caption or "🎉 **Access Granted!** Here is your media content 🔥"
    }

    # डेटाबेस में सेव करें
    media_database[media_id] = media_data
    
    # यह मीडिया डिफ़ॉल्ट रूप से पिन हो जाएगा (डायरेक्ट /start वालों के लिए)
    pinned_media = media_data

    bot_username = context.bot.username
    unique_link = f"https://t.me/{bot_username}?start={media_id}"
    
    await message.reply_text(
        f"✅ **Media Uploaded & Pinned Successfully!**\n\n"
        f"🔗 **Your Unique Shareable Link:**\n`{unique_link}`\n\n"
        f"📌 *(This media is now set as the default Pinned Media for direct /start users)*",
        parse_mode="Markdown"
    )

async def send_media_to_user(chat_id, media_data, context):
    """यूजर को मीडिया भेजेगा और 24 घंटे बाद डिलीट होने का टाइमर सेट करेगा"""
    if not media_data:
        await context.bot.send_message(chat_id=chat_id, text="❌ No media available or expired.")
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

    # 24 घंटे (86400 सेकंड) बाद मैसेज डिलीट करने के लिए बैकग्राउंड टास्क
    if sent_msg:
        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 86400))

async def start(update, context):
    user_id = update.effective_user.id
    args = context.args  
    
    # 1. केस 1: अगर यूजर ने डायरेक्ट /start किया है (बिना किसी लिंक के)
    if not args:
        is_joined = await check_all_subscriptions(user_id, context)
        if not is_joined:
            keyboard = []
            for i in range(0, len(CHANNELS), 2):
                row = []
                row.append(InlineKeyboardButton("Join Channel 1 ↗", url=CHANNELS[i][1]))
                if i + 1 < len(CHANNELS):
                    row.append(InlineKeyboardButton("Join Channel 2 ↗", url=CHANNELS[i+1][1]))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔓 Claim / Verify", callback_data="claim_pinned")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = (
                "👋 **Hello Dear, Welcome To Our Bot!**\n\n"
                "🛑 **You must join all required channels below to access the pinned media.**\n\n"
                "💣 **After joining both channels, click on 'Claim / Verify'.**"
            )
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await send_media_to_user(user_id, pinned_media, context)
        return

    # 2. केस 2: अगर यूजर किसी यूनिक लिंक से आया है (जैसे ?start=media_1)
    media_id = args[0]
    if media_id not in media_database:
        await update.message.reply_text("❌ Invalid or expired media link.")
        return

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

    await send_media_to_user(user_id, media_database[media_id], context)

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data  
    
    # अगर यूजर डायरेक्ट स्टार्ट वाले प्रॉम्प्ट से क्लेम कर रहा है (पिन मीडिया के लिए)
    if data == "claim_pinned":
        is_joined = await check_all_subscriptions(user_id, context)
        if is_joined:
            try:
                await query.message.delete() # बॉक्स गायब हो जाएगा
            except Exception:
                pass
            await send_media_to_user(user_id, pinned_media, context)
        else:
            await query.answer("❌ You haven't joined all channels yet! Please join both channels and try again.", show_alert=True)
            
    # अगर यूजर किसी यूनिक लिंक वाले प्रॉम्प्ट से क्लेम कर रहा है
    elif data.startswith("claim_"):
        media_id = data.split("_", 1)[1] 
        is_joined = await check_all_subscriptions(user_id, context)
        
        if is_joined:
            try:
                await query.message.delete() # बॉक्स गायब हो जाएगा
            except Exception:
                pass
            
            media_data = media_database.get(media_id)
            await send_media_to_user(user_id, media_data, context)
        else:
            await query.answer("❌ You haven't joined all channels yet! Please join both channels and try again.", show_alert=True)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_admin_upload))

    print("Bot is running perfectly with all features...")
    app.run_polling()

if __name__ == '__main__':
    main()
                                                
