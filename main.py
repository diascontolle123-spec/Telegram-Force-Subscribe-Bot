from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo

from flask import Flask
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import Conflict, NetworkError, TelegramError, BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


LOGGER = logging.getLogger(__name__)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@yazz8ballpool")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/yazz8ballpool")
CHECK_STATUS_CALLBACK = "check_subscription"
GET_KEY_CALLBACK = "get_key"
MENU_GET_KEY = "🔑 Get Key"
MENU_LIST_HARGA = "📊 List Harga"
MENU_ORDER_VIP = "🛒 Order VIP"
MENU_APK_NINJA = "📥 Link APK Ninja"
MENU_APK_SAMURAI = "⚔️ Link APK Samurai"
MENU_TUTORIAL = "📖 Tutorial"
APK_NINJA_URL = "https://sub4unlock.com/S/05mxk"
APK_SAMURAI_URL = "https://sub4unlock.com/S/Z5olj"
# Status Kunci Samurai (Default: Terkunci)
SAMURAI_ACCESS_OPEN = False
TUTORIAL_URL = "https://youtu.be/94COnGxw15A?si=gVm0Qjos7Cfk_3Ao"
ADMIN_USERNAME = "@ADAMYOURBAE"
USERS_DB_PATH = os.getenv("USERS_DB_PATH", "data/users.db")
DISPLAY_TIMEZONE = os.getenv("BOT_TIMEZONE", "Asia/Jakarta")
MANUAL_EXPIRY_TEXT = "19 September 02:55"
KEEP_ALIVE_PORT = int(os.getenv("KEEP_ALIVE_PORT", os.getenv("PORT", "5000")))
RECONNECT_DELAY_SECONDS = int(os.getenv("RECONNECT_DELAY_SECONDS", "5"))
KEY_VALIDITY = timedelta(hours=24)
MONTH_NAMES_ID = (
    "JANUARI",
    "FEBRUARI",
    "MARET",
    "APRIL",
    "MEI",
    "JUNI",
    "JULI",
    "AGUSTUS",
    "SEPTEMBER",
    "OKTOBER",
    "NOVEMBER",
    "DESEMBER",
)
DEFAULT_VIP_PRICES = (
    "Daftar harga VIP belum diatur.\n"
    "Silakan hubungi admin untuk mendapatkan harga terbaru."
)
LIST_HARGA_MESSAGE = """📊 DAFTAR HARGA MOD & VIP ENGINE

NINJA ENGGINE :
• 7 Day: 40K - $2.60
• 15 Day: 70K - $4.50
• 30 Day: 110K - $7.10
• Permanent: Contacts Admin

SAMURAI ENGGINE :
• 7 Day: 45K - $2.90
• 15 Day: 80K - $5.20
• 30 Day: 115K - $7.40
• Permanent: Contacts Admin

💳 Pembayaran: BINANCE / PAYPAL / DANA / QRIS / MANDIRI
💬 Pembelian & Pertanyaan: @ADAMYOURBAE
"""
async def toggle_samurai_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global SAMURAI_ACCESS_OPEN
    user = update.effective_user
    
    # Memeriksa apakah pengirim adalah admin (@ADAMYOURBAE)
    if user.username and user.username.lower() == ADMIN_USERNAME.replace("@", "").lower():
        SAMURAI_ACCESS_OPEN = not SAMURAI_ACCESS_OPEN
        status_text = "🔓 TERBUKA (Pengguna bisa mengambil link)" if SAMURAI_ACCESS_OPEN else "🔒 TERKUNCI (Akses dibatasi)"
        await update.message.reply_text(f"Status Akses APK Samurai: {status_text}")
    else:
        await update.message.reply_text("⛔ Anda tidak memiliki akses untuk perintah ini.")

@dataclass(frozen=True)
class Settings:
    bot_token: str
    key_value: str
    vip_price_list: str
    admin_telegram_id: int

    @classmethod
    def from_environment(cls) -> "Settings":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        key_value = os.getenv("GETKEY_VALUE", "").strip()
        vip_price_list = os.getenv("VIP_PRICE_LIST", DEFAULT_VIP_PRICES).strip()
        admin_telegram_id_value = os.getenv("ADMIN_TELEGRAM_ID", "").strip()

        missing = []
        if not bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not key_value:
            missing.append("GETKEY_VALUE")
        if not admin_telegram_id_value:
            missing.append("ADMIN_TELEGRAM_ID")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variable(s): {names}")

        try:
            admin_telegram_id = int(admin_telegram_id_value)
        except ValueError as error:
            raise RuntimeError("ADMIN_TELEGRAM_ID must be a numeric Telegram user ID") from error
        if admin_telegram_id <= 0:
            raise RuntimeError("ADMIN_TELEGRAM_ID must be a positive Telegram user ID")

        return cls(
            bot_token=bot_token,
            key_value=key_value,
            vip_price_list=vip_price_list or DEFAULT_VIP_PRICES,
            admin_telegram_id=admin_telegram_id,
        )


class UserStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id INTEGER PRIMARY KEY,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS key_access (
                    telegram_user_id INTEGER PRIMARY KEY,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def record_start(self, telegram_user_id: int) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (telegram_user_id, first_seen_at, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at
                """,
                (telegram_user_id, timestamp, timestamp),
            )

    def count_users(self) -> int:
        with self._connect() as connection:
            result = connection.execute("SELECT COUNT(*) FROM users").fetchone()
        return int(result[0]) if result is not None else 0

    def issue_key_window(
        self,
        telegram_user_id: int,
        now: datetime | None = None,
    ) -> datetime:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        current_time = current_time.astimezone(timezone.utc)

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT expires_at
                FROM key_access
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            ).fetchone()

            if row is not None:
                existing_expiry = datetime.fromisoformat(row[0]).astimezone(
                    timezone.utc
                )
                if existing_expiry > current_time:
                    return existing_expiry

            new_expiry = current_time + KEY_VALIDITY
            connection.execute(
                """
                INSERT INTO key_access (telegram_user_id, issued_at, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    issued_at = excluded.issued_at,
                    expires_at = excluded.expires_at
                """,
                (
                    telegram_user_id,
                    current_time.isoformat(),
                    new_expiry.isoformat(),
                ),
            )
            return new_expiry


def subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Join Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("Cek Status", callback_data=CHECK_STATUS_CALLBACK)],
        ]
    )
def get_key_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Ambil Key", callback_data=GET_KEY_CALLBACK)]]
    )


def menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(MENU_GET_KEY)],
        [KeyboardButton(MENU_LIST_HARGA), KeyboardButton(MENU_ORDER_VIP)],
        [KeyboardButton(MENU_APK_NINJA), KeyboardButton(MENU_APK_SAMURAI)],
        [KeyboardButton(MENU_TUTORIAL)]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Pilih menu",
    )



def subscription_message() -> str:
    return (
        "AKSES TERKUNCI\n\n"
        f"Silakan join {CHANNEL_USERNAME}, lalu tekan tombol *Cek Status*."
    )


def format_expiry(expiry: datetime) -> str:
    local_expiry = expiry.astimezone(ZoneInfo(DISPLAY_TIMEZONE))
    month = MONTH_NAMES_ID[local_expiry.month - 1]
    return f"{local_expiry.day} {month} {local_expiry:%H.%M}"


def key_message(key_value: str, expiry: datetime) -> str:
    return (
        "🔗 LINK KEY ANDA BERHASIL DIDAPATKAN!\n\n"
        f"• Link Key: {key_value}\n"
        "• Status: Aktif\n"
        f"• Expired: {MANUAL_EXPIRY_TEXT}\n\n"
        "Silakan klik link di atas untuk mengambil key Anda."
    )


def create_keep_alive_app() -> Flask:
    keep_alive_app = Flask(__name__)

    @keep_alive_app.get("/")
    def health_check() -> str:
        return "Bot is Running!"

    return keep_alive_app


def start_keep_alive_server() -> None:
    keep_alive_app = create_keep_alive_app()

    def serve() -> None:
        keep_alive_app.run(
            host="0.0.0.0",
            port=KEEP_ALIVE_PORT,
            debug=False,
            use_reloader=False,
        )

    thread = Thread(
        target=serve,
        name="telegram-bot-keep-alive",
        daemon=True,
    )
    thread.start()
    LOGGER.info("Keep-alive Flask server started on port %s", KEEP_ALIVE_PORT)


async def is_subscribed(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    user = update.effective_user
    if user is None:
        return False

    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user.id,
        )
    except TelegramError:
        LOGGER.exception(
            "Could not verify channel membership for Telegram user %s",
            user.id,
        )
        return False

    # Telegram uses "creator" for the channel owner. A restricted member is
    # still a valid subscriber when Telegram marks is_member as true.
    return member.status in {"member", "administrator", "creator"} or (
        member.status == "restricted" and bool(member.is_member)
    )


async def send_subscription_prompt(update: Update) -> None:
    message = update.effective_message
    if message is not None:
        # Remove a previously displayed menu if a user leaves the channel
        # after gaining access.
        await message.reply_text(
            "Menu dinonaktifkan sampai kamu join channel.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.reply_text(
            subscription_message(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=subscription_keyboard(),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is not None:
        user_store: UserStore = context.application.bot_data["user_store"]
        user_store.record_start(user.id)

    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Akses berhasil dibuka. Pilih menu di bawah.",
            reply_markup=menu_keyboard(),
        )


async def send_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    message = update.effective_message
    if user is not None and message is not None:
        user_store: UserStore = context.application.bot_data["user_store"]
        expiry = user_store.issue_key_window(user.id)
        await message.reply_text(
            key_message(settings.key_value, expiry),
            reply_markup=menu_keyboard(),
        )


async def get_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    await send_key(update, context)


async def order_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    settings: Settings = context.application.bot_data["settings"]
    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Daftar Harga VIP\n\n"
            f"{settings.vip_price_list}\n\n"
            f"Admin: {ADMIN_USERNAME}",
            reply_markup=menu_keyboard(),
        )


async def list_harga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            LIST_HARGA_MESSAGE,
            reply_markup=menu_keyboard(),
        )


async def apk_ninja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            f"Link Download APK MOD:\n{APK_MOD_URL}",
            reply_markup=menu_keyboard(),
        )


async def tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Tutorial penggunaan:\n\n"
            "1. Pastikan sudah join channel.\n"
            "2. Gunakan menu di bawah sesuai kebutuhan.\n"
            "3. Tekan Get Key untuk mengambil key.\n\n"
            f"Video tutorial: {TUTORIAL_URL}",
            reply_markup=menu_keyboard(),
        )


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Perintah yang tersedia:\n"
            "/getkey — mengambil key\n"
            "/listharga — melihat daftar harga MOD & VIP Engine\n"
            "/ordervip — melihat harga VIP dan kontak admin\n"
            "/apkninja — mendapatkan link APK MOD\n"
            "/tutorial — melihat petunjuk penggunaan",
            reply_markup=menu_keyboard(),
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    user = update.effective_user
    settings: Settings = context.application.bot_data["settings"]
    message = update.effective_message
    if user is None or message is None:
        return

    if user.id != settings.admin_telegram_id:
        await message.reply_text(
            "Akses ditolak. Perintah ini hanya untuk admin.",
            reply_markup=menu_keyboard(),
        )
        return

    user_store: UserStore = context.application.bot_data["user_store"]
    total_users = user_store.count_users()
    await message.reply_text(
        f"📊 STATISTIK BOT:\n• Total Pengguna: {total_users} user",
        reply_markup=menu_keyboard(),
    )


async def check_status_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    if await is_subscribed(update, context):
        await query.edit_message_text(
            "Status terverifikasi. Kamu sudah join channel.\n\n"
            "Menu akses sudah diaktifkan.",
        )
        if query.message is not None:
            await query.message.reply_text(
                "Pilih menu di bawah.",
                reply_markup=menu_keyboard(),
            )
    else:
        await query.edit_message_text(
            subscription_message(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=subscription_keyboard(),
        )
        if query.message is not None:
            await query.message.reply_text(
                "Menu dinonaktifkan sampai kamu join channel.",
                reply_markup=ReplyKeyboardRemove(),
            )


async def get_key_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    if not await is_subscribed(update, context):
        await query.edit_message_text(
            subscription_message(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=subscription_keyboard(),
        )
        if query.message is not None:
            await query.message.reply_text(
                "Menu dinonaktifkan sampai kamu join channel.",
                reply_markup=ReplyKeyboardRemove(),
            )
        return

    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    if user is None:
        return

    user_store: UserStore = context.application.bot_data["user_store"]
    expiry = user_store.issue_key_window(user.id)
    await query.edit_message_text(key_message(settings.key_value, expiry))
    if query.message is not None:
        await query.message.reply_text(
            "Pilih menu di bawah.",
            reply_markup=menu_keyboard(),
        )


async def locked_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    # This handler catches commands that are not explicitly implemented.
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text("Perintah tidak dikenal. Gunakan /getkey.")

async def apk_ninja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        f"<b>📥 Link APK MOD Ninja:</b>\n{APK_NINJA_URL}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def apk_samurai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not SAMURAI_ACCESS_OPEN:
        await update.effective_message.reply_text(
            "🔒 <b>Akses APK MOD Samurai Sedang Terkunci!</b>\n\n"
            "Menu ini sedang ditutup oleh Admin. Silakan tunggu informasi resmi di channel atau hubungi Admin.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.effective_message.reply_text(
            f"<b>⚔️ Link APK MOD Samurai:</b>\n{APK_SAMURAI_URL}",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

async def plain_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        action = message.text or ""
        handlers = {
            MENU_GET_KEY: send_key,
            MENU_LIST_HARGA: list_harga,
            MENU_ORDER_VIP: order_vip,
            MENU_APK_NINJA: apk_ninja,
            MENU_APK_SAMURAI: apk_samurai,
            MENU_TUTORIAL: tutorial,
        }
        handler = handlers.get(action)
        if handler is not None:
            await handler(update, context)
            return

        await message.reply_text(
            "Pilih salah satu tombol menu di bawah.",
            reply_markup=menu_keyboard(),
        )



async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            ("start", "Mulai dan cek akses"),
            ("getkey", "Ambil key setelah join channel"),
            ("listharga", "Lihat daftar harga MOD dan VIP"),
            ("ordervip", "Lihat harga VIP dan kontak admin"),
            ("apkninja", "Dapatkan link APK MOD Ninja"),
            ("apksamurai", "Dapatkan link APK MOD Samurai"),
            ("togglesamurai", "Buka/Tutup akses APK Samurai (Admin)"),
            ("tutorial", "Lihat tutorial penggunaan"),
            ("stats", "Statistik bot untuk admin"),
        ]
    )

    LOGGER.info("Telegram bot started; protected channel: %s", CHANNEL_USERNAME)


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    LOGGER.error("Unhandled Telegram update error", exc_info=context.error)

def build_application(settings: Settings) -> Application:
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .build()
    )

    application.bot_data["settings"] = settings
    application.bot_data["user_store"] = UserStore(USERS_DB_PATH)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getkey", get_key))
    application.add_handler(CommandHandler("listharga", list_harga))
    application.add_handler(CommandHandler("ordervip", order_vip))
    application.add_handler(CommandHandler(["apkninja", "linkapkmod"], apk_ninja))
    application.add_handler(CommandHandler("apksamurai", apk_samurai))
    application.add_handler(CommandHandler("togglesamurai", toggle_samurai_access))
    application.add_handler(CommandHandler("tutorial", tutorial))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats))

    application.add_handler(
        CallbackQueryHandler(
            check_status_callback,
            pattern=f"^{CHECK_STATUS_CALLBACK}$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            get_key_callback,
            pattern=f"^{GET_KEY_CALLBACK}$",
        )
    )

    application.add_handler(MessageHandler(filters.COMMAND, locked_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text))
    application.add_error_handler(error_handler)

    return application



def run_polling_forever(settings: Settings) -> None:
    while True:
        application = build_application(settings)
        try:
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                close_loop=False,
            )
            LOGGER.warning("Telegram polling stopped; reconnecting")
        except (Conflict, NetworkError) as error:
            LOGGER.warning(
                "Telegram polling connection issue (%s); reconnecting in %s seconds",
                error.__class__.__name__,
                RECONNECT_DELAY_SECONDS,
            )
        except TelegramError:
            LOGGER.exception(
                "Telegram polling failed; reconnecting in %s seconds",
                RECONNECT_DELAY_SECONDS,
            )
        except Exception:
            LOGGER.exception(
                "Unexpected polling error; reconnecting in %s seconds",
                RECONNECT_DELAY_SECONDS,
            )
        time.sleep(RECONNECT_DELAY_SECONDS)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    settings = Settings.from_environment()
    start_keep_alive_server()
    run_polling_forever(settings)


if __name__ == "__main__":
    main()
import os
from threading import Thread
from flask import Flask

# 1. Buat web server mini
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Render memberikan PORT secara otomatis lewat environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. Panggil keep_alive() sebelum bot.polling()
if __name__ == "__main__":
    keep_alive()
    print("Bot sedang berjalan...")
    # Masukkan kode bot polling Anda di bawah ini
    # bot.infinity_polling()
