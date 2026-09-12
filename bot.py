from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Use your token from BotFather
TOKEN = '8830625955:AAGyQEyDiOHP97Dv9DFYsdvoc5jJC1MQBR4'

# Your 2 actual channels
CHANNELS = [
    ('@quantixcashflow', 'https://t.me/quantixcashflow'),
    ('@Quantix_CashFlow', 'https://t.me/Quantix_CashFlow'),
] 

async def check_all_subscriptions(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Real-time check to see if the user is a member of all configured channels"""
    for channel, _ in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Error checking subscription for {channel}: {e}")
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if the user has joined all channels
    is_joined = await check_all_subscriptions(user_id, context)
    
    if not is_joined:
        keyboard = []
        
        # Generates side-by-side 'Join' buttons matching your requested style
        for i in range(0, len(CHANNELS), 2):
            row = []
            row.append(InlineKeyboardButton("Join ↗", url=CHANNELS[i][1]))
            if i + 1 < len(CHANNELS):
                row.append(InlineKeyboardButton("Join ↗", url=CHANNELS[i+1][1]))
            keyboard.append(row)
        
        # Add the Claim / Check button at the bottom
        keyboard.append([InlineKeyboardButton("🔓 Claim", callback_data="check_sub")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            "👋 **Hey There User Welcome To Bot !**\n\n"
            "🛑 **Must Join Total Channel To Use Our Bot**\n\n"
            "💣 **After Joining Click Claim**"
        )
        
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    # 🟢 ACCESS GRANTED: Put your bot's main content or features here
    await update.message.reply_text("🎉 Welcome back! You have successfully completed all steps and now have access to the bot.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    is_joined = await check_all_subscriptions(user_id, context)
    
    if is_joined:
        await query.message.edit_text("✅ Success! You have joined all channels. Type /start to begin using the bot.")
    else:
        await query.answer("❌ You haven't joined all channels yet! Please check again.", show_alert=True)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="check_sub"))

    print("Bot style template is running...")
    app.run_polling()
  
