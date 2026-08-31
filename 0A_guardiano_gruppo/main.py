import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(f"Ciao {user_first_name}! Sono il tuo guardiano del gruppo. Come posso aiutarti oggi?")

async def process_new_member(user, chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Nuovo membro rilevato: {user.first_name} (ID: {user.id}) nel gruppo {chat_id}")

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
    print("Bot avviato. In attesa di comandi...")
    app.run_polling()

if __name__ == "__main__":
    main()