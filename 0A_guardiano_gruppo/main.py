import os
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
pending_verifications = {}
AZIONE_TIMEOUT = "kick"
FLOOD_MAX_MESSAGES = 5
FLOOD_TIME_WINDOW = 3
FLOOD_MUTE_MINUTES = 5
message_timestamps = {}
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
    await update.message.reply_text(f"Ciao {user_first_name}! Sono il guardiano del gruppo.")

async def is_admin(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("creator", "administrator")
    except Exception as e:
        print(f"Errore controllo admin: {e}")
        return False

async def send_log(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if not LOG_CHANNEL_ID:
        return
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=text)
    except Exception as e:
        print(f"Errore invio log: {e}")

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
        print(f"Errore controllo status: {e}")
    return False

async def set_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    if not context.args or context.args[0].lower() not in ("kick", "mute"):
        await update.message.reply_text("Uso corretto: /set_timeout kick oppure /set_timeout mute")
        return

    nuova_azione = context.args[0].lower()
    chat_key = str(chat_id)

    if chat_key not in group_settings:
        group_settings[chat_key] = {}

    group_settings[chat_key]["azione_timeout"] = nuova_azione
    save_settings(group_settings)

    await update.message.reply_text(f"Impostazione aggiornata: alla scadenza verrà eseguito '{nuova_azione}'.")

async def whitelist_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
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
            await update.message.reply_text("ID non valido.")
            return
    else:
        await update.message.reply_text("Rispondi al messaggio o scrivi: /whitelist_add <id>")
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

    await update.message.reply_text(f"{target_name} aggiunto alla whitelist.")

async def whitelist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    target_id = None

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID non valido.")
            return
    else:
        await update.message.reply_text("Rispondi al messaggio o scrivi: /whitelist_remove <id>")
        return

    chat_key = str(chat_id)
    if chat_key not in group_settings or target_id not in group_settings[chat_key].get("whitelist_extra", []):
        await update.message.reply_text("Utente non trovato in whitelist.")
        return

    group_settings[chat_key]["whitelist_extra"].remove(target_id)
    save_settings(group_settings)

    await update.message.reply_text(f"Utente (ID: {target_id}) rimosso dalla whitelist.")

async def whitelist_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    extra = get_whitelist_extra(chat_id)
    if not extra:
        await update.message.reply_text("Nessun utente extra in whitelist.")
        return

    lista_testo = "\n".join(str(uid) for uid in extra)
    await update.message.reply_text(f"Utenti in whitelist:\n{lista_testo}")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Rispondi al messaggio dell'utente da ammonire con /warn.")
        return

    target_user = update.message.reply_to_message.from_user
    target_id = target_user.id
    target_name = target_user.first_name

    if await is_exempt(target_id, chat_id, context):
        await update.message.reply_text("Non puoi ammonire un admin o un utente in whitelist.")
        return

    chat_key = str(chat_id)
    if chat_key not in group_settings:
        group_settings[chat_key] = {}
    if "warnings" not in group_settings[chat_key]:
        group_settings[chat_key]["warnings"] = {}

    user_warnings_key = str(target_id)
    current_warnings = group_settings[chat_key]["warnings"].get(user_warnings_key, 0) + 1
    group_settings[chat_key]["warnings"][user_warnings_key] = current_warnings
    save_settings(group_settings)

    MAX_WARNINGS = 3

    if current_warnings >= MAX_WARNINGS:
        group_settings[chat_key]["warnings"][user_warnings_key] = 0
        save_settings(group_settings)

        try:
            until = datetime.now() + timedelta(minutes=15)
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await update.message.reply_text(f"{target_name} ha raggiunto {MAX_WARNINGS} ammonizioni ed è stato mutato per 15 minuti.")
            await send_log(context, f"WARN LIMIT: {target_name} (ID: {target_id}) mutato per 15 min nel gruppo {chat_id}.")
        except Exception as e:
            print(f"Errore mute warning: {e}")
    else:
        await update.message.reply_text(f"{target_name} ammonito. Warn: {current_warnings}/{MAX_WARNINGS}")
        await send_log(context, f"WARN: {target_name} (ID: {target_id}) ammonito ({current_warnings}/{MAX_WARNINGS}) nel gruppo {chat_id}.")

async def filter_word_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    if not context.args:
        await update.message.reply_text("Uso corretto: /filter_word_add <parola>")
        return

    word = context.args[0].lower()
    chat_key = str(chat_id)

    if chat_key not in group_settings:
        group_settings[chat_key] = {}
    if "blocked_words" not in group_settings[chat_key]:
        group_settings[chat_key]["blocked_words"] = []

    if word in group_settings[chat_key]["blocked_words"]:
        await update.message.reply_text(f"La parola '{word}' è già filtrata.")
        return

    group_settings[chat_key]["blocked_words"].append(word)
    save_settings(group_settings)
    await update.message.reply_text(f"Parola '{word}' aggiunta al filtro.")

async def filter_word_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    if not context.args:
        await update.message.reply_text("Uso corretto: /filter_word_remove <parola>")
        return

    word = context.args[0].lower()
    chat_key = str(chat_id)

    if chat_key not in group_settings or "blocked_words" not in group_settings[chat_key] or word not in group_settings[chat_key]["blocked_words"]:
        await update.message.reply_text(f"La parola '{word}' non è nel filtro.")
        return

    group_settings[chat_key]["blocked_words"].remove(word)
    save_settings(group_settings)
    await update.message.reply_text(f"Parola '{word}' rimossa dal filtro.")

async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text("Uso corretto: /filter_links on oppure /filter_links off")
        return

    state = context.args[0].lower() == "on"
    chat_key = str(chat_id)

    if chat_key not in group_settings:
        group_settings[chat_key] = {}

    group_settings[chat_key]["filter_links"] = state
    save_settings(group_settings)
    await update.message.reply_text(f"Filtro link: {'attivo' if state else 'disattivato'}.")

async def check_chat_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id

    if await is_exempt(user.id, chat_id, context):
        return

    text = update.message.text.lower()
    chat_key = str(chat_id)
    settings = group_settings.get(chat_key, {})

    has_links = False
    if settings.get("filter_links", False):
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type in ("url", "text_link"):
                    has_links = True
                    break
        if "http://" in text or "https://" in text or "t.me/" in text or "www." in text:
            has_links = True

    if has_links:
        try:
            await update.message.delete()
            await send_log(context, f"FILTER LINK: Messaggio con link di {user.first_name} (ID: {user.id}) eliminato.")
            return
        except Exception as e:
            print(f"Errore eliminazione link: {e}")
            return

    blocked_words = settings.get("blocked_words", [])
    if blocked_words:
        words_in_message = text.split()
        for word in blocked_words:
            if word in words_in_message or word in text:
                try:
                    await update.message.delete()
                    await update.message.reply_text(f"{user.first_name}, il tuo messaggio conteneva termini non consentiti.")
                    await send_log(context, f"FILTER WORD: Messaggio di {user.first_name} (ID: {user.id}) rimosso per '{word}'.")
                    return
                except Exception as e:
                    print(f"Errore eliminazione parola vietata: {e}")
                break

async def process_new_member(user, chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await is_exempt(user.id, chat_id, context):
        return

    muted_permissions = ChatPermissions(can_send_messages=False)
    try:
        await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user.id, permissions=muted_permissions)
    except Exception as e:
        print(f"Errore mute nuovo utente: {e}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Clicca qui per dimostrare che sei umano", callback_data=f"verify_{user.id}")]
    ])

    sent_message = await context.bot.send_message(
        chat_id=chat_id,
        text=f"Benvenuto {user.first_name}! Clicca il pulsante per verificare di essere umano.",
        reply_markup=keyboard
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

async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id

    if await is_exempt(user.id, chat_id, context):
        return

    key = f"{chat_id}_{user.id}"
    now = time.time()

    if key not in message_timestamps:
        message_timestamps[key] = []

    message_timestamps[key].append(now)
    message_timestamps[key] = [t for t in message_timestamps[key] if now - t <= FLOOD_TIME_WINDOW]

    if len(message_timestamps[key]) > FLOOD_MAX_MESSAGES:
        message_timestamps[key] = []
        try:
            until = datetime.now() + timedelta(minutes=FLOOD_MUTE_MINUTES)
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await update.message.reply_text(f"{user.first_name} è stato mutato per {FLOOD_MUTE_MINUTES} minuti (flood).")
            await send_log(context, f"FLOOD: {user.first_name} (ID: {user.id}) mutato per {FLOOD_MUTE_MINUTES} min.")
        except Exception as e:
            print(f"Errore flood mute: {e}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await check_chat_content(update, context)
    if update.message and update.message.text:
        await check_flood(update, context)

async def check_verification(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    if user_id not in pending_verifications:
        return

    info = pending_verifications[user_id]
    first_name = info["first_name"]
    message_id = info["message_id"]
    del pending_verifications[user_id]

    azione = get_azione_timeout(chat_id)

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Errore cancellazione messaggio verifica: {e}")

    if azione == "kick":
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            if ADMIN_CHAT_ID:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"{first_name} (ID: {user_id}) rimosso per mancata verifica."
                )
            await send_log(context, f"KICK: {first_name} (ID: {user_id}) rimosso per mancata verifica.")
        except Exception as e:
            print(f"Errore kick verifica: {e}")

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
            chat_id=chat_id,
            user_id=clicked_user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except Exception as e:
        print(f"Errore ripristino permessi: {e}")

    await query.message.delete()
    await context.bot.send_message(chat_id=chat_id, text=f"Benvenuto {query.from_user.first_name}! Ora puoi scrivere.")

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for member in update.message.new_chat_members:
        await process_new_member(member, update.effective_chat.id, context)

def main() -> None:
    if not TOKEN:
        print("Errore: TELEGRAM_BOT_TOKEN non impostato.")
        return

    app = ApplicationBuilder().token(TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_timeout", set_timeout))
    app.add_handler(CommandHandler("whitelist_add", whitelist_add))
    app.add_handler(CommandHandler("whitelist_remove", whitelist_remove))
    app.add_handler(CommandHandler("whitelist_list", whitelist_list))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("filter_word_add", filter_word_add))
    app.add_handler(CommandHandler("filter_word_remove", filter_word_remove))
    app.add_handler(CommandHandler("filter_links", filter_links))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(CallbackQueryHandler(verify_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()