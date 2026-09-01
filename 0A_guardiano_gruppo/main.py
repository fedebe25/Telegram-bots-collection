import os
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(f"Ciao {user_first_name}! Sono il tuo guardiano del gruppo. Come posso aiutarti oggi?")

async def process_new_member(user, chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    muted_permissions = ChatPermissions(can_send_messages=False)
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=muted_permissions
        )
        print(f"Utente {user.first_name} (ID: {user.id}) è stato silenziato nel gruppo {chat_id}.")
    except Exception as e:
        print(f"Errore durante il silenziamento dell'utente {user.first_name} (ID: {user.id}): {e}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Clicca qui per dimostrare che sei umano", callback_data=f"verify_{user.id}")]
    ])

    await context.bot.send_message(
        chat_id = chat_id,
        text = f"Benvenuto {user.first_name}! Per favore, dimostra che sei umano cliccando il pulsante qui sotto.",
        reply_markup = keyboard
    )

async def verify_button(update: Update, context:ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    clicked_user_id = int(query.data.split("_")[1])

    if query.from_user.id != clicked_user_id:
        await query.answer("Questo pulsante non è per te!", show_alert=True)
        return

    chat_id = query.message.chat.id

    try:
        await context.bot.restrict_chat_member(
            chat_id = chat_id,
            user_id = clicked_user_id,
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except Exception as e:
        print(f"Errore durante il ripristino permessi di {query.from_user.first_name} (ID: {query.from_user.id}): {e}")

    await query.message.delete()

    conferma = await context.bot.send_message(
        chat_id = chat_id,
        text = f"✅ Benvenuto {query.from_user.first_name}! Ora puoi scrivere"
    )

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for member in update.message.new_chat_members:
        await process_new_member(member, update.effective_chat.id, context)

async def simula_ingresso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fake_user = update.effective_user
    chat_id = update.effective_chat.id
    await process_new_member(fake_user, chat_id, context)
    await update.message.reply_text("✅ Simulazione ingresso eseguita (solo debug).")

def main() -> None:
    if not TOKEN:
        print("Errore: TELEGRAM_BOT_TOKEN non è impostato nelle variabili d'ambiente.")
        return
    
    app = (
    ApplicationBuilder()
    .token(TOKEN)
    .read_timeout(30)
    .write_timeout(30)
    .connect_timeout(30)
    .build()
)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(CommandHandler("simula_ingresso", simula_ingresso))
    app.add_handler(CallbackQueryHandler(verify_button))
    print("Bot avviato. In attesa di comandi...")
    app.run_polling()

if __name__ == "__main__":
    main()