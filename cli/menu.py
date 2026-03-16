"""CLI menu and dialog flow."""

import logging

from database import ContextDB, DEFAULT_USER_ID
from openai_client import OpenAIClient

logger = logging.getLogger(__name__)


def _print_header(model: str) -> None:
    print()
    print("=" * 60)
    print("  CLI — диалог с OpenAI")
    print("  Модель:", model)
    print("=" * 60)
    print()


def _print_menu() -> None:
    print("Меню:")
    print("  1. Начать диалог")
    print("  2. Вывести контекст")
    print("  3. Очистить контекст")
    print("  4. Выйти из программы")
    print()


def _action_show_context(db: ContextDB) -> None:
    print("\n--- Контекст (хронология) ---")
    try:
        any_ = False
        for entry in db.get_all_entries(DEFAULT_USER_ID):
            any_ = True
            print(f"  [{entry['created_at']}]")
            for t in entry["user_theses"]:
                print("    •", t)
            for t in entry["assistant_theses"]:
                print("    •", t)
            print()
        if not any_:
            print("  (пусто)")
    except RuntimeError as e:
        logger.exception("Не удалось вывести контекст в CLI")
        print(f"Ошибка чтения контекста: {e}")
    print("---\n")


def _action_clear_context(db: ContextDB) -> None:
    try:
        db.clear(DEFAULT_USER_ID)
    except RuntimeError as e:
        logger.exception("Не удалось очистить контекст в CLI")
        print(f"Ошибка очистки контекста: {e}\n")
        return
    print("\nКонтекст очищен.\n")


def _run_dialog(client: OpenAIClient, db: ContextDB) -> None:
    print("\nРежим диалога. Введите сообщение (пустая строка — вернуться в меню).\n")
    while True:
        try:
            line = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            return
        try:
            context_text = db.get_context_text(DEFAULT_USER_ID)
        except RuntimeError as e:
            logger.exception("Ошибка чтения контекста в режиме диалога CLI")
            print(f"Ошибка чтения контекста: {e}\n")
            continue
        try:
            response = client.chat(line, system_context=context_text)
        except RuntimeError as e:
            logger.exception("Ошибка запроса к модели из CLI")
            print(f"{e}\n")
            continue
        except Exception as e:  # noqa: BLE001
            logger.exception("Неожиданная ошибка запроса к модели из CLI")
            print(f"Произошла непредвиденная ошибка при обращении к модели: {e}\n")
            continue
        try:
            db.add_turn(
                DEFAULT_USER_ID,
                response.user_theses,
                response.assistant_theses,
            )
        except RuntimeError as e:
            logger.exception("Ошибка сохранения контекста в режиме диалога CLI")
            print(f"Ответ получен, но не удалось сохранить контекст: {e}\n")
        print("\nАссистент:", response.message, "\n")


def run_cli() -> None:
    """Main CLI loop."""
    from config import OPENAI_API_KEY, OPENAI_MODEL, get_log_level

    if not OPENAI_API_KEY:
        print("Ошибка: задайте OPENAI_API_KEY в файле .env")
        return

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=get_log_level(),
    )

    client = OpenAIClient()
    db = ContextDB()

    logger.info("CLI запущен с моделью %s", client.model)

    _print_header(client.model)

    while True:
        _print_menu()
        try:
            choice = input("Выберите пункт (1–4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "1":
            _run_dialog(client, db)
        elif choice == "2":
            _action_show_context(db)
        elif choice == "3":
            _action_clear_context(db)
        elif choice == "4":
            print("Выход.")
            break
        else:
            print("Неверный пункт. Введите 1–4.\n")

    db.close()
    logger.info("CLI завершён")
