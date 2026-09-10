import os
import logging
from venv import logger
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

async def start(update:Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Domande frequenti", "Contatta un umano"]
        ["Orari e Info"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard= True)
    logger.info(f"Utente {update.effective_user.first_name} ha avviato il bot.")


    await update.message.reply_text(
        "Ciao! Sono il tuo assistente virtuale. Come posso aiutarti oggi?",
        reply_markup=reply_markup
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    logger.info("Bot in esecuzione... Premi CTRL+C per spegnerlo.")
    app.run_polling()

if __name__ == "__main__":
    main()