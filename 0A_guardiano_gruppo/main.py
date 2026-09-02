import os
import json
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
pending_verifications = {}
AZIONE_TIMEOUT = "kick"
whitelist_raw = os.getenv("WHITELIST_IDS", "")
WHITELIST_IDS = [int(x.strip()) for x in whitelist_raw.split(",") if x.strip()]

SETTINGS_FILE = "settings.json"

def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def get_azione_timeout(chat_id: int) -> str:
    chat_key = str(chat_id)
    if chat_key in group_settings and "azione_timeout" in group_settings[chat_key]:
        return group_settings[chat_key]["azione_timeout"]
    return AZIONE_TIMEOUT

def get_whitelist_extra(chat_id: int) -> list:
    chat_key = str(chat_id)
    if chat_key in group_settings and "whitelist_extra" in group_settings[chat_key]:
        return group_settings[chat_key]["whitelist_extra"]
    return []

group_settings = load_settings()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(f"Ciao {user_first_name}! Sono il tuo guardiano del gruppo. Come posso aiutarti oggi?")

async def is_admin(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("creator", "administrator")
    except Exception as e:
        print(f"Errore durante il controllo admin di {user_id}: {e}")
        return False

async def is_exempt(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id in WHITELIST_IDS:
        return True

    if user_id in get_whitelist_extra(chat_id):
        return True

    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception as e:
        print(f"Errore durante il controllo dello status di {user_id}: {e}")

    return False

async def set_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("⛔ Solo gli admin s usare questo comando.")
        return

    if not context.args or context.args[0].lower() not in ("kick", "mute"):
        await update.message.reply_text("Uso corretto: /set_timeout kick  oppure  /set_timeout mute")
        return

    nuova_azione = context.args[0].lower()
    chat_key = str(chat_id)

    if chat_key not in group_settings:
        group_settings[chat_key] = {}

    group_settings[chat_key]["azione_timeout"] = nuova_azione
    save_settings(group_settings)

    await update.message.reply_text(f"✅ Impostazione aggiornata: alla scadenza del timer verrà eseguito \"{nuova_azione}\".")

async def whitelist_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("⛔ Solo gli admin possono usare questo comando.")
        return

    target_id = None
    target_name = None

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        target_name = target_user.first_name
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_name = str(target_id)
        except ValueError:
            await update.message.reply_text("ID non valido. Usa un numero, oppure rispondi al messaggio della persona.")
            return
    else:
        await update.message.reply_text("Rispondi al messaggio della persona da aggiungere, oppure scrivi: /whitelist_add <id>")
        return

    chat_key = str(chat_id)
    if chat_key not in group_settings:
        group_settings[chat_key] = {}
    if "whitelist_extra" not in group_settings[chat_key]:
        group_settings[chat_key]["whitelist_extra"] = []

    if target_id in group_settings[chat_key]["whitelist_extra"]:
        await update.message.reply_text(f"{target_name} è già in whitelist.")
        return

    group_settings[chat_key]["whitelist_extra"].append(target_id)
    save_settings(group_settings)

    await update.message.reply_text(f"✅ {target_name} (ID: {target_id}) aggiunto alla whitelist.")

async def whitelist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("⛔ Solo gli admin possono usare questo comando.")
        return

    target_id = None

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID non valido. Usa un numero, oppure rispondi al messaggio della persona.")
            return
    else:
        await update.message.reply_text("Rispondi al messaggio della persona da rimuovere, oppure scrivi: /whitelist_remove <id>")
        return

    chat_key = str(chat_id)

    if chat_key not in group_settings or target_id not in group_settings[chat_key].get("whitelist_extra", []):
        await update.message.reply_text("Questo utente non è in whitelist.")
        return

    group_settings[chat_key]["whitelist_extra"].remove(target_id)
    save_settings(group_settings)

    await update.message.reply_text(f"✅ Utente (ID: {target_id}) rimosso dalla whitelist.")

async def whitelist_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("⛔ Solo gli admin possono usare questo comando.")
        return

    extra = get_whitelist_extra(chat_id)

    if not extra:
        await update.message.reply_text("Nessun utente extra in whitelist per questo gruppo.")
        return

    lista_testo = "\n".join(str(uid) for uid in extra)
    await update.message.reply_text(f"Utenti in whitelist per questo gruppo:\n{lista_testo}")

async def process_new_member(user, chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await is_exempt(user.id, chat_id, context):
        print(f"Utente {user.first_name} (ID: {user.id}) esentato dalla verifica (admin/whitelist).")
        return

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

    sent_message = await context.bot.send_message(
        chat_id = chat_id,
        text = f"Benvenuto {user.first_name}! Per favore, dimostra che sei umano cliccando il pulsante qui sotto.",
        reply_markup = keyboard
    )

    pending_verifications[user.id] = {
        "chat_id": chat_id,
        "first_name": user.first_name,
        "message_id": sent_message.message_id
    }

    context.job_queue.run_once(
        check_verification,
        when=60,
        data={"user_id": user.id, "chat_id": chat_id}
    )

async def check_verification(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    if user_id not in pending_verifications:
        print(f"Utente {user_id} aveva già verificato in tempo, nessuna azione necessaria.")
        return

    info = pending_verifications[user_id]
    first_name = info["first_name"]
    message_id = info["message_id"]
    del pending_verifications[user_id]

    azione = get_azione_timeout(chat_id)
    print(f"Timer scaduto per {first_name} (ID: {user_id}) - non ha cliccato in tempo. Azione: {azione}")

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Errore durante la cancellazione del messaggio di verifica: {e}")

    if azione == "kick":
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            print(f"Utente {first_name} (ID: {user_id}) rimosso dal gruppo per mancata verifica.")

            if ADMIN_CHAT_ID:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⚠️ {first_name} (ID: {user_id}) è stato rimosso dal gruppo per mancata verifica entro 60 secondi."
                )
        except Exception as e:
            print(f"Errore durante la rimozione dell'utente {first_name} (ID: {user_id}): {e}")
    else:
        print(f"Utente {first_name} (ID: {user_id}) resta silenziato in attesa di sblocco manuale da un admin.")


async def verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    clicked_user_id = int(query.data.split("_")[1])

    if query.from_user.id != clicked_user_id:
        await query.answer("Questo pulsante non è per te!", show_alert=True)
        return

    chat_id = query.message.chat.id

    if clicked_user_id in pending_verifications:
        del pending_verifications[clicked_user_id]

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

    await context.bot.send_message(
        chat_id = chat_id,
        text = f"✅ Benvenuto {query.from_user.first_name}! Ora puoi scrivere"
    )


async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for member in update.message.new_chat_members:
        await process_new_member(member, update.effective_chat.id, context)

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
    app.add_handler(CommandHandler("set_timeout", set_timeout))
    app.add_handler(CommandHandler("whitelist_add", whitelist_add))
    app.add_handler(CommandHandler("whitelist_remove", whitelist_remove))
    app.add_handler(CommandHandler("whitelist_list", whitelist_list))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(CallbackQueryHandler(verify_button))
    print("Bot avviato. In attesa di comandi...")
    app.run_polling()

if __name__ == "__main__":
    main()