"""OpenAI API client with Structured Outputs."""

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from openai_client.schemas import DialogResponse


SYSTEM_PROMPT = """Ты — полезный ассистент. Отвечай на запросы пользователя.

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

    def chat(self, user_message: str, context_text: str = "") -> DialogResponse:
        """
        Send user message to the model with optional context; return structured response.
        """
        context_block = ""
        if context_text.strip():
            context_block = (
                "Контекст предыдущего общения (используй для согласованности ответа):\n"
                f"{context_text}\n\n"
            )

        user_content = f"{context_block}Сообщение пользователя: {user_message}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        completion = self._client.chat.completions.parse(
            model=self._model,
            messages=messages,
            response_format=DialogResponse,
        )

        msg = completion.choices[0].message
        if getattr(msg, "refusal", None):
            return DialogResponse(
                user_theses=[],
                assistant_theses=[],
                message=f"[Отказ модели: {msg.refusal}]",
            )
        return msg.parsed
