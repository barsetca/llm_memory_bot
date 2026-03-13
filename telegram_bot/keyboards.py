"""Клавиатуры бота."""

from telegram import ReplyKeyboardMarkup, KeyboardButton

# Подписи кнопок (должны совпадать с проверкой в обработчиках)
BTN_SHOW_CONTEXT = "Вывести контекст"
BTN_CLEAR_CONTEXT = "Очистить контекст"
BTN_MAIN_MENU = "Главное меню"
BTN_CANCEL = "Отмена"

MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(BTN_SHOW_CONTEXT), KeyboardButton(BTN_CLEAR_CONTEXT)],
        [KeyboardButton(BTN_MAIN_MENU)],
    ],
    resize_keyboard=True,
    is_persistent=True,
)
