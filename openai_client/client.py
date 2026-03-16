"""OpenAI API client with Structured Outputs."""

import logging

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from openai_client.schemas import DialogResponse

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_BASE = """Ты — полезный ассистент. Отвечай на запросы пользователя.

У тебя всегда есть два источника информации:
1) текущий запрос пользователя;
2) исторический контекст диалога (тезисы из прошлых сообщений), если он передан в системном сообщении.

Всегда учитывай исторический контекст:
- если в контексте есть факты о пользователе (имя, предпочтения и т.п.), считай их актуальными;
- если пользователь спрашивает о факте, который упоминался ранее (например: "как меня зовут?"), найди его в контексте и ответь согласно найденной информации, а не говори, что не знаешь;
- если в контексте и текущем запросе есть противоречие, приоритет у более свежей информации из текущего запроса.

Если тебе нужна актуальная информация из внешнего мира (новости, курсы валют, расписания, свежая документация и т.п.), которой может не быть в твоей внутренней памяти,
обращайся к инструменту web_search, чтобы найти данные в интернете, а затем используй их в своём структурированном ответе.

Твои ответы должны быть в структурированном виде:
1. user_theses — список тезисов запроса пользователя. Каждый тезис начинай с фраз: "Пользователь спросил ...", "Пользователь уточнил ..." и т.п.
2. assistant_theses — список тезисов твоего ответа. Каждый тезис начинай с фраз: "Ассистент пояснил ...", "Ассистент спросил ..." и т.п.
3. message — полный развёрнутый ответ пользователю для отображения в чате."""


class OpenAIClient:
    """Client for chat completions with structured output and context."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        self._model = model or OPENAI_MODEL

    @property
    def model(self) -> str:
        return self._model

    def chat(self, user_message: str, system_context: str = "") -> DialogResponse:
        """
        Send user message to the model with optional context; return structured response.
        """
        system_content = SYSTEM_PROMPT_BASE
        if system_context.strip():
            system_content = (
                SYSTEM_PROMPT_BASE
                + "\n\nИсторический контекст диалога (для учёта в ответах):\n"
                + system_context
            )

        user_content = f"Сообщение пользователя: {user_message}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        try:
            # Примечание: helper .parse сейчас поддерживает только tools типа "function",
            # поэтому web_search явно не передаём, а лишь инструктируем модель в промпте.
            completion = self._client.chat.completions.parse(
                model=self._model,
                messages=messages,
                response_format=DialogResponse,
            )
        except Exception as e:  # noqa: BLE001
            # Не логируем содержимое запроса, только факт ошибки.
            logger.exception("Ошибка при обращении к OpenAI (model=%s)", self._model)
            raise RuntimeError(
                "Не удалось получить ответ от модели. Попробуйте ещё раз позже."
            ) from e

        msg = completion.choices[0].message
        if getattr(msg, "refusal", None):
            return DialogResponse(
                user_theses=[],
                assistant_theses=[],
                message=f"[Отказ модели: {msg.refusal}]",
            )
        return msg.parsed
