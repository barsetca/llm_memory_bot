"""Telegram-бот с логикой CLI: меню кнопками, контекст на пользователя."""

import asyncio
import logging

from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import OPENAI_API_KEY, OPENAI_MODEL, TELEGRAM_BOT_TOKEN
from database import ContextDB
from openai_client import OpenAIClient
from telegram_bot.keyboards import (
    BTN_CANCEL,
    BTN_CLEAR_CONTEXT,
    BTN_MAIN_MENU,
    BTN_SHOW_CONTEXT,
    MAIN_MENU_KEYBOARD,
)

# Общие зависимости (инициализируются при запуске)
_db: ContextDB | None = None
_client: OpenAIClient | None = None


def _tg_user_id(update: Update) -> str:
    """Идентификатор пользователя для таблицы контекста."""
    return f"tg_{update.effective_user.id}"


async def _get_bot_name(app: Application) -> str:
    me = await app.bot.get_me()
    return me.first_name or me.username or "Бот"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start: приветствие, имя бота, модель, меню кнопок."""
    if not update.message:
        return
    app = context.application
    bot_name = await _get_bot_name(app)
    text = (
        f"Привет! Я **{bot_name}**.\n\n"
        f"Модель: `{OPENAI_MODEL}`\n\n"
        "Я могу вести с вами диалог, запоминая важные тезисы в контексте.\n"
        "Кнопками ниже вы можете посмотреть или очистить накопленный контекст.\n\n"
        "Для начала диалога просто отправьте сообщение."
    )
    await update.message.reply_text(
        text,
        reply_markup=MAIN_MENU_KEYBOARD,
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текста: кнопки меню или обычное сообщение (запрос к модели)."""
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()

    # Обработка кнопок меню
    if text == BTN_SHOW_CONTEXT:
        uid = _tg_user_id(update)
        entries = list(_db.get_all_entries(uid)) if _db else []
        if not entries:
            await update.message.reply_text("Контекст пуст.", reply_markup=MAIN_MENU_KEYBOARD)
            return
        lines = []
        for entry in entries:
            lines.append(f"_{entry['created_at']}_")
            for t in entry["user_theses"]:
                lines.append(f"• {t}")
            for t in entry["assistant_theses"]:
                lines.append(f"• {t}")
            lines.append("")
        msg = "\n".join(lines).strip()
        if len(msg) > 4000:
            msg = msg[:3970] + "\n\n… (обрезано)"
        await update.message.reply_text(msg or "—", reply_markup=MAIN_MENU_KEYBOARD, parse_mode="Markdown")
        return
    if text == BTN_CLEAR_CONTEXT:
        uid = _tg_user_id(update)
        if _db:
            _db.clear(uid)
        await update.message.reply_text("Контекст очищен.", reply_markup=MAIN_MENU_KEYBOARD)
        return
    if text == BTN_MAIN_MENU or text == BTN_CANCEL:
        await update.message.reply_text("Главное меню. Выберите действие:", reply_markup=MAIN_MENU_KEYBOARD)
        return

    # Любой другой текст — это запрос к модели
    uid = _tg_user_id(update)
    context_text = _db.get_context_text(uid) if _db else ""
    try:
        response = (
            await asyncio.to_thread(_client.chat, text, context_text=context_text)
            if _client
            else None
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка запроса: {e}", reply_markup=MAIN_MENU_KEYBOARD)
        return
    if response and _db:
        _db.add_turn(uid, response.user_theses, response.assistant_theses)
        await update.message.reply_text(response.message, reply_markup=MAIN_MENU_KEYBOARD)
    else:
        await update.message.reply_text("Ошибка: нет ответа.", reply_markup=MAIN_MENU_KEYBOARD)


def run_bot() -> None:
    """Запуск бота (блокирующий)."""
    global _db, _client
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: задайте TELEGRAM_BOT_TOKEN в .env")
        return
    if not OPENAI_API_KEY:
        print("Ошибка: задайте OPENAI_API_KEY в .env")
        return
    _db = ContextDB()
    _client = OpenAIClient()

    async def _print_bot_info() -> None:
        bot = Bot(TELEGRAM_BOT_TOKEN)
        me = await bot.get_me()
        name = me.first_name or me.username or "Бот"
        username = f" (@{me.username})" if me.username else ""
        print(f"Запуск Telegram-бота: {name}{username}")
        print(f"Модель: {OPENAI_MODEL}")

    try:
        asyncio.run(_print_bot_info())
    except RuntimeError:
        # Если цикл уже запущен (маловероятно при run_bot как entrypoint), просто пропускаем
        pass

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.WARNING,
    )
    # Урезаем подробные логи библиотек, чтобы не светить токен
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    app.run_polling(allowed_updates=Update.ALL_TYPES)
