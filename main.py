from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
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


@dataclass(frozen=True)
class Settings:
    bot_token: str
    key_value: str

    @classmethod
    def from_environment(cls) -> "Settings":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        key_value = os.getenv("GETKEY_VALUE", "").strip()

        missing = []
        if not bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not key_value:
            missing.append("GETKEY_VALUE")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variable(s): {names}")

        return cls(bot_token=bot_token, key_value=key_value)


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


def subscription_message() -> str:
    return (
        "Akses bot masih terkunci.\n\n"
        f"Silakan join {CHANNEL_USERNAME}, lalu tekan tombol *Cek Status*."
    )


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
        await message.reply_text(
            subscription_message(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=subscription_keyboard(),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Akses berhasil dibuka.\n\nGunakan /getkey untuk mengambil key.",
            reply_markup=get_key_keyboard(),
        )


async def get_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    settings: Settings = context.application.bot_data["settings"]
    message = update.effective_message
    if message is not None:
        await message.reply_text(f"Key kamu:\n\n`{settings.key_value}`")


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text(
            "Perintah yang tersedia:\n/getkey — mengambil key"
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
            "Tekan tombol di bawah atau gunakan /getkey.",
            reply_markup=get_key_keyboard(),
        )
    else:
        await query.edit_message_text(
            subscription_message(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=subscription_keyboard(),
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
        return

    settings: Settings = context.application.bot_data["settings"]
    await query.edit_message_text(f"Key kamu:\n\n`{settings.key_value}`")


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


async def plain_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await is_subscribed(update, context):
        await send_subscription_prompt(update)
        return

    message = update.effective_message
    if message is not None:
        await message.reply_text("Gunakan /getkey untuk mengambil key.")


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            ("start", "Mulai dan cek akses"),
            ("getkey", "Ambil key setelah join channel"),
            ("help", "Lihat bantuan"),
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

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getkey", get_key))
    application.add_handler(CommandHandler("help", help_command))
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


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    settings = Settings.from_environment()
    application = build_application(settings)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
