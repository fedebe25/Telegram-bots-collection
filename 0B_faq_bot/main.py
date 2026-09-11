import os
import logging
from venv import logger
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)
logging.logger("httpx").setLevel(logging.WARNING)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

async def start(update:Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Domande frequenti", "Contatta un umano"],
        ["Orari e Info"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard= True)
    logger.info(f"Utente {update.effective_user.first_name} ha avviato il bot.")


    await update.message.reply_text(
        "Ciao! Sono il tuo assistente virtuale. Come posso aiutarti oggi?",
        reply_markup=reply_markup
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    testo_utente = update.message.text

    logger.info(f"Ricevuto messaggio: '{testo_utente}' da {update.message.from_user.first_name}")
    
    if testo_utente == "Domande Frequenti ❓":
        await update.message.reply_text("Hai scelto le FAQ! Presto collegheremo questa sezione al database.")
        
    elif testo_utente == "Contatta un Umano 🙋‍♂️":
        await update.message.reply_text("Richiesta di assistenza registrata. Inoltro al proprietario in corso...")
        
    elif testo_utente == "Orari e Info 🕒":
        await update.message.reply_text("Siamo operativi tutti i giorni, pronti a risponderti.")
        
    else:
        await update.message.reply_text("Scusami, non ho capito. Per favore, usa i bottoni del menu qui sotto.")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot in esecuzione... Premi CTRL+C per spegnerlo.")
    app.run_polling()

if __name__ == "__main__":
    main()