# CLI/Telegram-бот — диалог с OpenAI

Приложение для общения с OpenAI с сохранением контекста в SQLite, с возможностью вывода или очистки этого контекста.


## Быстрый старт

```bash
pip install -r requirements.txt
cp .env.example .env
# В .env укажите как минимум OPENAI_API_KEY.
```

## Запуск

**CLI:**
```bash
python3 main.py
```

**Telegram-бот:**
```bash
# В .env добавьте TELEGRAM_BOT_TOKEN (токен от @BotFather)
python3 -m telegram_bot
```

## Поведение CLI

1. **Начать диалог** — ввод сообщений модели; ответы структурированы (тезисы + полный ответ), тезисы пишутся в БД и используются как контекст.
2. **Вывести контекст** — показать сохранённые тезисы в хронологическом порядке.
3. **Очистить контекст** — полная очистка хранилища контекста.
4. **Выйти из программы** — корректное завершение.

### Жизненный цикл одного запроса (CLI)

1. Пользователь вводит текст.
2. Приложение читает накопленный контекст из SQLite для текущего пользователя.
3. В `OpenAIClient` формируется промпт: контекст + новое сообщение.
4. Модель возвращает **структурированный ответ** (Structured Outputs):  
   - `user_theses` — тезисы запроса пользователя;  
   - `assistant_theses` — тезисы ответа ассистента;  
   - `message` — полный текст ответа.
5. Тезисы (`user_theses` и `assistant_theses`) сохраняются в БД и становятся частью контекста для следующих запросов.
6. Пользователь в консоли видит только человеко-читаемый `message`.

## Telegram-бот

При команде `/start` бот выводит приветствие, **своё имя** (из профиля BotFather) и используемую модель, затем меню в виде **кнопок**:

- **Вывести контекст** — вывод сохранённых тезисов в хронологическом порядке.
- **Очистить контекст** — полная очистка контекста пользователя.
- **Главное меню** — повторный показ меню.

Любое текстовое сообщение пользователя (не совпадающее с подписями кнопок) трактуется как **запрос к модели**.  
Логика обработки такая же, как в CLI: используется контекст пользователя, сохраняются новые тезисы, в Telegram отправляется только `message`.

У каждого пользователя бота своя таблица контекста в БД (`context_tg_<telegram_id>`).

Скриншоты, демонстрирующие работы бота находятся в папке /screeshots

## Структура проекта

```
llm_memory/
├── .env.example              # Шаблон: OPENAI_API_KEY, OPENAI_MODEL, TELEGRAM_BOT_TOKEN, LOG_LEVEL
├── .gitignore                 # Игнорирование .env, context.db, __pycache__, venv
├── config.py                  # Загрузка .env: OPENAI_API_KEY, OPENAI_MODEL, TELEGRAM_BOT_TOKEN
├── main.py                    # Точка входа CLI: run_cli()
├── requirements.txt           # openai, pydantic, python-dotenv, python-telegram-bot
├── README.md                  # Документация (этот файл)
│
├── cli/                       # Консольный интерфейс
│   ├── __init__.py            # Экспорт run_cli
│   └── menu.py                # Главное меню 1–4; режим диалога; вывод/очистка контекста
│
├── telegram_bot/              # Telegram-бот (логика как у CLI, кнопки вместо пунктов меню)
│   ├── __init__.py            # Экспорт run_bot
│   ├── __main__.py            # Запуск: python3 -m telegram_bot
│   ├── bot.py                 # Обработчики /start и сообщений; имя бота при подключении; user_id = tg_<id>
│   └── keyboards.py           # Reply-клавиатура: Вывести контекст, Очистить контекст, Главное меню
│
├── openai_client/             # Работа с OpenAI API
│   ├── __init__.py            # Экспорт OpenAIClient и DialogResponse
│   ├── client.py              # OpenAIClient: chat() с Structured Outputs и контекстом
│   └── schemas.py             # Pydantic DialogResponse (user_theses, assistant_theses, message)
│
└── database/                  # Хранилище контекста (общее для CLI и бота)
    ├── __init__.py            # Экспорт ContextDB и DEFAULT_USER_ID
    └── db.py                  # SQLite: таблица context_<user_id> на пользователя; add_turn, get_context_text, get_all_entries, clear
```

### Пояснения к файлам

| Файл | Назначение |
|------|------------|
| **config.py** | Читает `.env`: `OPENAI_API_KEY`, `OPENAI_MODEL`, `TELEGRAM_BOT_TOKEN`, `LOG_LEVEL`. |
| **main.py** | Запускает `run_cli()` — цикл меню и диалога. |
| **cli/menu.py** | Приветствие и модель при старте; меню (1–4); диалог с моделью, вывод и очистка контекста. |
| **telegram_bot/bot.py** | Обработка `/start` (приветствие + имя бота + модель + кнопки), текста (кнопки или сообщение в диалоге); контекст по `tg_<user_id>`. |
| **telegram_bot/keyboards.py** | Reply-клавиатура с кнопками меню. |
| **openai_client/schemas.py** | Схема ответа модели: списки тезисов пользователя и ассистента + полный текст ответа (`message`). |
| **openai_client/client.py** | Формирует запрос с контекстом из БД, вызывает `chat.completions.parse()` с Pydantic-схемой, обрабатывает отказы. |
| **database/db.py** | Подключение к `context.db`; для каждого пользователя таблица `context_<user_id>` с полями `id`, `created_at`, `user_theses`, `assistant_theses` (JSON). Методы: добавление хода, получение контекста строкой, выборка всех записей, очистка + VACUUM + базовая обработка ошибок. |

## Переменные окружения

| Переменная | Обязательна | Значение по умолчанию | Описание |
|-----------|-------------|------------------------|----------|
| `OPENAI_API_KEY` | да | — | Ключ доступа к OpenAI API. |
| `OPENAI_MODEL` | нет | `gpt-4o-mini` | Модель OpenAI для Structured Outputs. |
| `TELEGRAM_BOT_TOKEN` | для бота | — | Токен Telegram-бота от `@BotFather`. |
| `LOG_LEVEL` | нет | `INFO` | Уровень логирования (DEBUG/INFO/WARNING/ERROR/CRITICAL). |

## База данных

Файл `context.db` в корне проекта. Для поддержки нескольких пользователей у каждого своя таблица `context_<user_id>`.

- Для CLI сейчас используется `context_default`.
- Для Telegram-пользователей таблицы имеют вид `context_tg_<telegram_id>`.

Тезисы (`user_theses` и `assistant_theses`) хранятся в виде JSON-строк, что упрощает эволюцию структуры без миграций схемы.
