from dataclasses import asdict
from typing import List

import requests

from llm_providers.common import AbstractLlmProvider, LLMError
from history import HistoryMessage
from view import View


class OllamaLlmProvider(AbstractLlmProvider):
    _timeout = 60 * 5

    def __init__(self, model: str, url: str, view: View):
        self._url = url
        self.model = model

        view.show_debug(f"Используется модель {model}")

    def _call_ollama(self, messages: List[dict]) -> str:
        """
        Отправляет запрос к /api/chat Ollama и возвращает текст ответа ассистента.
        """
        payload = {
            "model": self.model,
            # Сообщения уже в подходящем формате
            "messages": messages,
            "stream": False,
        }
        try:
            resp = requests.post(f"{self._url}/api/chat", json=payload, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Ошибка соединения с Ollama: {e}") from e
        except (KeyError, ValueError) as e:
            raise LLMError(f"Некорректный ответ от Ollama: {e}") from e

    def __call__(self, messages: List[HistoryMessage]) -> str:
        messages = [asdict(m) for m in messages]
        return self._call_ollama(messages)


