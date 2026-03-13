"""Pydantic schemas for OpenAI Structured Outputs."""

from pydantic import BaseModel, Field


class DialogResponse(BaseModel):
    """Structured response from the model: theses + full message."""

    user_theses: list[str] = Field(
        description=(
            "Список тезисов текущего запроса пользователя. "
            "Каждый тезис начинается с фраз типа: 'Пользователь спросил', 'Пользователь уточнил'."
        )
    )
    assistant_theses: list[str] = Field(
        description=(
            "Список тезисов ответа ассистента на текущий запрос. "
            "Каждый тезис начинается с фраз типа: 'Ассистент спросил', 'Ассистент пояснил'."
        )
    )
    message: str = Field(
        description="Полный ответ ассистента для пользователя."
    )
