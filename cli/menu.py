"""CLI menu and dialog flow."""

from database import ContextDB, DEFAULT_USER_ID
from openai_client import OpenAIClient


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
    print("---\n")


def _action_clear_context(db: ContextDB) -> None:
    db.clear(DEFAULT_USER_ID)
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
        context_text = db.get_context_text(DEFAULT_USER_ID)
        try:
            response = client.chat(line, context_text=context_text)
        except Exception as e:
            print(f"Ошибка запроса: {e}\n")
            continue
        db.add_turn(
            DEFAULT_USER_ID,
            response.user_theses,
            response.assistant_theses,
        )
        print("\nАссистент:", response.message, "\n")


def run_cli() -> None:
    """Main CLI loop."""
    from config import OPENAI_API_KEY, OPENAI_MODEL

    if not OPENAI_API_KEY:
        print("Ошибка: задайте OPENAI_API_KEY в файле .env")
        return

    client = OpenAIClient()
    db = ContextDB()

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
