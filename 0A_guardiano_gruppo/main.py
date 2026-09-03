import os
import random
import time
import logging
import re
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from dotenv import load_dotenv

import aiosqlite
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    Application
)
from telegram.error import BadRequest

try:
    from google import genai
except ImportError:
    genai = None

load_dotenv()

LOG_FILE = os.getenv("LOG_FILE", "bot.log")
DB_FILE = os.getenv("DB_FILE", "bot_database.db")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_MAX_CALLS_PER_MONTH = int(os.getenv("GEMINI_MAX_CALLS_PER_MONTH", "1000"))

whitelist_raw = os.getenv("WHITELIST_IDS", "")
ENV_WHITELIST_IDS = [int(x.strip()) for x in whitelist_raw.split(",") if x.strip()]

log_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] (%(name)s): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("GuardianBot")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

FLOOD_MAX_MESSAGES = 5
FLOOD_TIME_WINDOW = 3.0
FLOOD_MUTE_MINUTES = 5
message_timestamps: dict[str, list[float]] = {}

LINK_REGEX = re.compile(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")

ai_client = None
if GEMINI_API_KEY and genai:
    try:
        ai_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Integrazione Google Gemini configurata con successo.")
    except Exception as e:
        logger.error(f"Errore inizializzazione client Gemini: {e}")

async def init_db(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            filter_links INTEGER DEFAULT 0,
            filter_forwards INTEGER DEFAULT 0,
            filter_channels INTEGER DEFAULT 0,
            filter_ai INTEGER DEFAULT 0,
            azione_timeout TEXT DEFAULT 'kick'
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS blocked_words (
            chat_id INTEGER,
            word TEXT,
            PRIMARY KEY (chat_id, word)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            chat_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            warning_count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS pending_verifications (
            user_id INTEGER,
            chat_id INTEGER,
            correct_answer INTEGER,
            first_name TEXT,
            message_id INTEGER,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage (
            month TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)

    await db.commit()
    logger.info("Database SQLite verificato/inizializzato.")

async def get_settings(chat_id: int, db: aiosqlite.Connection) -> dict:
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return dict(row)
        await db.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
        await db.commit()
        return {
            "chat_id": chat_id,
            "filter_links": 0,
            "filter_forwards": 0,
            "filter_channels": 0,
            "filter_ai": 0,
            "azione_timeout": "kick"
        }

async def update_setting_field(chat_id: int, field: str, value, db: aiosqlite.Connection) -> None:
    valid_fields = ["filter_links", "filter_forwards", "filter_channels", "filter_ai", "azione_timeout"]
    if field not in valid_fields:
        return
    await db.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
    await db.execute(f"UPDATE group_settings SET {field} = ? WHERE chat_id = ?", (value, chat_id))
    await db.commit()

async def send_log(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    logger.info(f"[LOG NOTIFICATION] {text}")
    if not LOG_CHANNEL_ID:
        return
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=text)
    except BadRequest as e:
        logger.error(f"Errore permessi invio log: {e}")
    except Exception as e:
        logger.error(f"Errore generico invio log: {e}")

async def is_admin(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("creator", "administrator")
    except BadRequest as e:
        logger.warning(f"Impossibile verificare permessi admin: {e}")
        return False
    except Exception as e:
        logger.error(f"Errore controllo admin: {e}")
        return False

async def is_exempt(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE, db: aiosqlite.Connection) -> bool:
    if user_id in ENV_WHITELIST_IDS:
        return True
    async with db.execute("SELECT 1 FROM whitelist WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)) as cur:
        if await cur.fetchone():
            return True
    return await is_admin(user_id, chat_id, context)

async def analyze_with_gemini(message_text: str) -> bool:
    if not ai_client:
        return False
    try:
        prompt = (
            "Sei un moderatore automatico per un gruppo Telegram. Analizza questo messaggio. "
            "Rispondi ESCLUSIVAMENTE con la parola 'SPAM' se contiene scam, bot crypto, pubblicità non autorizzata, "
            "promozione di canali terzi ingannevole, o linguaggio gravemente diffamatorio. "
            "Altrimenti rispondi con 'SAFE'. Non aggiungere commenti.\n\n"
            f"Messaggio: {message_text}"
        )
        response = await ai_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        result = response.text.strip().upper() if response.text else "SAFE"
        return "SPAM" in result
    except Exception as e:
        logger.error(f"Errore chiamata Gemini API: {e}")
        return False

def build_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    f_links = "🟢 ON" if settings.get("filter_links") else "🔴 OFF"
    f_forwards = "🟢 ON" if settings.get("filter_forwards") else "🔴 OFF"
    f_channels = "🟢 ON" if settings.get("filter_channels") else "🔴 OFF"
    f_ai = "🟢 ON" if settings.get("filter_ai") else "🔴 OFF"
    az_to = settings.get("azione_timeout", "kick").upper()

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"Filtro Link: {f_links}", callback_data="toggle_links"),
            InlineKeyboardButton(f"Filtro Inoltri: {f_forwards}", callback_data="toggle_forwards")
        ],
        [
            InlineKeyboardButton(f"Blocca Canali: {f_channels}", callback_data="toggle_channels"),
            InlineKeyboardButton(f"Gemini AI: {f_ai}", callback_data="toggle_ai")
        ],
        [
            InlineKeyboardButton(f"Azione Timeout: [{az_to}]", callback_data="toggle_timeout")
        ],
        [
            InlineKeyboardButton("❌ Chiudi Pannello", callback_data="close_settings")
        ]
    ])

async def check_and_increment_ai_usage(db: aiosqlite.Connection) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    async with db.execute("SELECT count FROM ai_usage WHERE month = ?", (month_key,)) as cur:
        row = await cur.fetchone()
        current = row[0] if row else 0

    if current >= GEMINI_MAX_CALLS_PER_MONTH:
        return False

    await db.execute(
        "INSERT INTO ai_usage (month, count) VALUES (?, 1) ON CONFLICT(month) DO UPDATE SET count = count + 1",
        (month_key,)
    )
    await db.commit()
    return True

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    db = context.bot_data["db"]

    if chat.type == "private":
        await update.message.reply_text("Questo comando va usato all'interno del gruppo.")
        return

    if not await is_admin(user.id, chat.id, context):
        await update.message.reply_text("Comando riservato agli amministratori.")
        return

    settings = await get_settings(chat.id, db)
    await update.message.reply_text(
        "⚙️ **Pannello di Controllo Gruppo**\nTocca i pulsanti sottostanti per attivare/disattivare i filtri in tempo reale.",
        reply_markup=build_settings_keyboard(settings),
        parse_mode="Markdown"
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    db = context.bot_data["db"]

    if not await is_admin(user.id, chat.id, context):
        await query.answer("Accesso negato: non sei un amministratore.", show_alert=True)
        return

    data = query.data
    if data == "close_settings":
        await query.answer()
        await query.message.delete()
        return

    settings = await get_settings(chat.id, db)

    if data == "toggle_links":
        await update_setting_field(chat.id, "filter_links", 0 if settings["filter_links"] else 1, db)
    elif data == "toggle_forwards":
        await update_setting_field(chat.id, "filter_forwards", 0 if settings["filter_forwards"] else 1, db)
    elif data == "toggle_channels":
        await update_setting_field(chat.id, "filter_channels", 0 if settings["filter_channels"] else 1, db)
    elif data == "toggle_ai":
        if not ai_client:
            await query.answer("Gemini API Key non presente nel server!", show_alert=True)
            return
        await update_setting_field(chat.id, "filter_ai", 0 if settings["filter_ai"] else 1, db)
    elif data == "toggle_timeout":
        new_action = "mute" if settings.get("azione_timeout", "kick") == "kick" else "kick"
        await update_setting_field(chat.id, "azione_timeout", new_action, db)

    updated_settings = await get_settings(chat.id, db)
    await query.answer("Impostazione aggiornata!")
    await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(updated_settings))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Guardian Bot attivo e operativo.")

async def whitelist_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    db = context.bot_data["db"]

    if not await is_admin(user_id, chat_id, context):
        await update.message.reply_text("Solo gli admin possono usare questo comando.")
        return

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target = update.message.reply_to_message.from_user
        target_id, target_name = target.id, target.first_name
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_name = f"ID:{target_id}"
        except ValueError:
            await update.message.reply_text("ID non valido.")
            return
    else:
        await update.message.reply_text("Rispondi a un utente o scrivi /whitelist_add <user_id>")
        return

    await db.execute("INSERT OR IGNORE INTO whitelist (chat_id, user_id) VALUES (?, ?)", (chat_id, target_id))
    await db.commit()
    await update.message.reply_text(f"Utente {target_name} inserito in whitelist.")

async def whitelist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    db = context.bot_data["db"]

    if not await is_admin(user_id, chat_id, context):
        return

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID non valido.")
            return
    else:
        await update.message.reply_text("Rispondi a un utente o scrivi /whitelist_remove <user_id>")
        return

    await db.execute("DELETE FROM whitelist WHERE chat_id = ? AND user_id = ?", (chat_id, target_id))
    await db.commit()
    await update.message.reply_text(f"Utente {target_id} rimosso dalla whitelist.")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    db = context.bot_data["db"]

    if not await is_admin(admin_id, chat_id, context):
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
        await update.message.reply_text("Rispondi al messaggio dell'utente che intendi ammonire.")
        return

    target_user = update.message.reply_to_message.from_user
    if await is_exempt(target_user.id, chat_id, context, db):
        await update.message.reply_text("Impossibile sanzionare admin o membri in whitelist.")
        return

    MAX_WARNS = 3
    async with db.execute("SELECT warning_count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, target_user.id)) as cur:
        row = await cur.fetchone()
        current_warns = (row[0] if row else 0) + 1

    if current_warns >= MAX_WARNS:
        await db.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, target_user.id))
        await db.commit()
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=15)
            )
            await update.message.reply_text(f"🚨 {target_user.first_name} ha raggiunto 3 ammonizioni: mutato per 15 minuti.")
            await send_log(context, f"WARN MAX LIMIT: {target_user.first_name} (ID: {target_user.id}) mutato per 15 minuti.")
        except BadRequest as e:
            logger.warning(f"Fallita restrizione per warn: {e}")
    else:
        await db.execute(
            "INSERT INTO warnings (chat_id, user_id, warning_count) VALUES (?, ?, ?) ON CONFLICT(chat_id, user_id) DO UPDATE SET warning_count = ?",
            (chat_id, target_user.id, current_warns, current_warns)
        )
        await db.commit()
        await update.message.reply_text(f"⚠️ {target_user.first_name} ammonito. Avvisi correnti: {current_warns}/{MAX_WARNS}.")

async def filter_word_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    db = context.bot_data["db"]

    if not await is_admin(update.effective_user.id, chat_id, context) or not context.args:
        await update.message.reply_text("Uso: /filter_word_add <parola>")
        return

    word = context.args[0].lower().strip()
    await db.execute("INSERT OR IGNORE INTO blocked_words (chat_id, word) VALUES (?, ?)", (chat_id, word))
    await db.commit()
    await update.message.reply_text(f"Parola '{word}' inserita nella blacklist.")

async def filter_word_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    db = context.bot_data["db"]

    if not await is_admin(update.effective_user.id, chat_id, context) or not context.args:
        await update.message.reply_text("Uso: /filter_word_remove <parola>")
        return

    word = context.args[0].lower().strip()
    await db.execute("DELETE FROM blocked_words WHERE chat_id = ? AND word = ?", (chat_id, word))
    await db.commit()
    await update.message.reply_text(f"Parola '{word}' eliminata dalla blacklist.")

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    db = context.bot_data["db"]

    for user in update.message.new_chat_members:
        if user.is_bot or await is_exempt(user.id, chat_id, context, db):
            continue

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except BadRequest as e:
            logger.warning(f"Impossibile restringere utente: {e}")
            continue

        n1, n2 = random.randint(2, 9), random.randint(2, 9)
        correct = n1 + n2
        distractors = {random.randint(correct - 4, correct + 4) for _ in range(10)}
        distractors.discard(correct)
        distractors = {d for d in distractors if d > 0}
        
        options = list(distractors)[:3] + [correct]
        random.shuffle(options)

        keyboard = [[InlineKeyboardButton(str(opt), callback_data=f"captcha_{user.id}_{opt}") for opt in options]]
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=f"👋 Benvenuto {user.first_name}!\nRisolvi il CAPTCHA anti-bot entro 60 secondi per abilitare la scrittura:\n👉 **Quanto fa {n1} + {n2}?**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        await db.execute(
            "INSERT OR REPLACE INTO pending_verifications (user_id, chat_id, correct_answer, first_name, message_id) VALUES (?, ?, ?, ?, ?)",
            (user.id, chat_id, correct, user.first_name, sent.message_id)
        )
        await db.commit()

        context.job_queue.run_once(check_verification, when=60, data={"user_id": user.id, "chat_id": chat_id})

async def captcha_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split("_")
    target_user_id, selected_val = int(parts[1]), int(parts[2])
    chat_id = query.message.chat.id
    db = context.bot_data["db"]

    if query.from_user.id != target_user_id:
        await query.answer("Questo CAPTCHA non è destinato al tuo account.", show_alert=True)
        return

    async with db.execute("SELECT correct_answer, first_name FROM pending_verifications WHERE user_id = ? AND chat_id = ?", (target_user_id, chat_id)) as cur:
        row = await cur.fetchone()
        if not row:
            await query.answer("Verifica scaduta o già completata.", show_alert=True)
            return
        correct_val, first_name = row[0], row[1]

    if selected_val == correct_val:
        await db.execute("DELETE FROM pending_verifications WHERE user_id = ? AND chat_id = ?", (target_user_id, chat_id))
        await db.commit()
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_user_id,
                permissions=ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
            )
            await query.message.delete()
        except BadRequest as e:
            logger.warning(f"Errore sblocco post-captcha: {e}")

        await query.answer("Verifica superata con successo!")
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Verifica completata. Benvenuto/a nel gruppo, {first_name}!")
    else:
        await query.answer("Risposta errata! Riprova prima dello scadere del tempo.", show_alert=True)

async def check_verification(context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id, chat_id = context.job.data["user_id"], context.job.data["chat_id"]
    db = context.bot_data["db"]

    async with db.execute("SELECT message_id, first_name FROM pending_verifications WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)) as cur:
        row = await cur.fetchone()
        if not row:
            return
        message_id, first_name = row[0], row[1]
    
    await db.execute("DELETE FROM pending_verifications WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    await db.commit()

    settings = await get_settings(chat_id, db)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except BadRequest:
        pass

    if settings.get("azione_timeout", "kick") == "kick":
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            await send_log(context, f"KICK TIMEOUT: {first_name} (ID: {user_id}) rimosso per timeout verifica.")
            if ADMIN_CHAT_ID:
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=f"⚠️ {first_name} (ID: {user_id}) è stato rimosso dal gruppo {chat_id} per mancata verifica."
                    )
                except Exception as e:
                    logger.warning(f"Impossibile notificare admin privatamente: {e}")
        except BadRequest as e:
            logger.error(f"Impossibile kickare utente per timeout: {e}")
    else:
        try:
            await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=ChatPermissions(can_send_messages=False))
            await context.bot.send_message(chat_id=chat_id, text=f"🔇 Tempo scaduto per la verifica: {first_name} rimane mutato nel gruppo.")
        except BadRequest as e:
            logger.error(f"Impossibile mutare utente per timeout: {e}")

async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not user:
        return False

    key = f"{chat_id}_{user.id}"
    now = time.time()

    if key not in message_timestamps:
        message_timestamps[key] = []

    message_timestamps[key].append(now)
    message_timestamps[key] = [t for t in message_timestamps[key] if now - t <= FLOOD_TIME_WINDOW]

    if len(message_timestamps[key]) > FLOOD_MAX_MESSAGES:
        del message_timestamps[key]
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id, user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=FLOOD_MUTE_MINUTES)
            )
            await update.message.reply_text(f"🚫 {user.first_name} mutato per {FLOOD_MUTE_MINUTES} minuti per spam/flood.")
            return True
        except BadRequest as e:
            logger.warning(f"Impossibile mutare per flood: {e}")
    elif not message_timestamps[key]:
        del message_timestamps[key]
        
    return False

async def handle_incoming_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not chat or chat.type == "private":
        return

    db = context.bot_data["db"]
    settings = await get_settings(chat.id, db)

    if settings.get("filter_channels") and msg.sender_chat and msg.sender_chat.id != chat.id:
        try:
            await msg.delete()
            return
        except BadRequest:
            return

    if user and await is_exempt(user.id, chat.id, context, db):
        return

    if await check_flood(update, context):
        return

    if settings.get("filter_forwards") and (msg.forward_origin or msg.forward_from_chat or msg.forward_from):
        try:
            await msg.delete()
            return
        except BadRequest:
            return

    text = msg.text or msg.caption or ""
    text_lower = text.lower()

    if settings.get("filter_links"):
        has_links = False
        entities = (msg.entities or []) + (msg.caption_entities or [])
        if any(ent.type in ("url", "text_link") for ent in entities) or LINK_REGEX.search(text_lower):
            has_links = True

        if has_links:
            try:
                await msg.delete()
                return
            except BadRequest:
                return

    async with db.execute("SELECT word FROM blocked_words WHERE chat_id = ?", (chat.id,)) as cur:
        blocked = [row[0] for row in await cur.fetchall()]

    if blocked and any(b_word in text_lower for b_word in blocked):
        try:
            await msg.delete()
            return
        except BadRequest:
            return

    if settings.get("filter_ai") and ai_client and len(text) > 15:
        triggers = ["crypto", "guadagn", "invest", "bonus", "dm me", "t.me", "telegram", "promo"]
        if any(trig in text_lower for trig in triggers):
            if await check_and_increment_ai_usage(db):
                if await analyze_with_gemini(text):
                    try:
                        await msg.delete()
                    except BadRequest:
                        pass
            else:
                logger.warning("Limite mensile chiamate Gemini raggiunto, filtro AI saltato per questo messaggio.")

async def post_init(application: Application) -> None:
    db = await aiosqlite.connect(DB_FILE)
    application.bot_data["db"] = db
    await init_db(db)

async def post_shutdown(application: Application) -> None:
    db = application.bot_data.get("db")
    if db:
        await db.close()

def main() -> None:
    if not TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN non configurato nel file .env!")
        return

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("whitelist_add", whitelist_add))
    application.add_handler(CommandHandler("whitelist_remove", whitelist_remove))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("filter_word_add", filter_word_add))
    application.add_handler(CommandHandler("filter_word_remove", filter_word_remove))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|close_settings)"))
    application.add_handler(CallbackQueryHandler(captcha_button_handler, pattern="^captcha_"))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.ALL, handle_incoming_messages))

    logger.info("Avvio polling Guardian Bot...")
    application.run_polling()

if __name__ == "__main__":
    main()