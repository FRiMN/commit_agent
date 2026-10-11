import json
from copy import copy
from dataclasses import asdict
from typing import List, Iterator

import requests

from llm_providers.common import AbstractLlmProvider, LLMError
from history import HistoryMessage, HistoryMessageRole
from view import View


class LlamaCppLlmProvider(AbstractLlmProvider):
    _timeout = 60 * 5

    def __init__(self, model: str, base_url: str, view: View):
        self._base_url = base_url.rstrip('/')
        self.model = model

        view.show_debug(f"llama.cpp на адресе {base_url}")
        view.show_debug(f"Используется модель {model}")

    def _call_llamacpp(self, messages: List[dict]) -> str:
        """
        Отправляет запрос к /chat/completions llama.cpp и возвращает текст ответа.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            resp = requests.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=self._timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Ошибка соединения с llama.cpp: {e}") from e
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"Некорректный ответ от llama.cpp: {e}") from e

    def _call_llamacpp_stream(self, messages: List[dict]) -> Iterator[str]:
        """
        Отправляет запрос к /chat/completions llama.cpp и возвращает чанки (стриминг).
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        try:
            resp = requests.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=self._timeout
            )
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue

                # Пропускаем строки SSE с исключительно data:finish
                line = line.lstrip("data: ")
                data = json.loads(line)
                
                # Разные LLM ответы могут приходить как отдельное сообщение
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

                    # Проверка на завершение
                    if data.get("done") or choices[0].get("finish_reason"):
                        break
                elif data.get("done"):
                    break
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Ошибка соединения с llama.cpp: {e}") from e
        except (KeyError, ValueError) as e:
            raise LLMError(f"Некорректный ответ от llama.cpp: {e}\n{resp.content=}") from e

    def __call__(self, messages: List[HistoryMessage]) -> str:
        messages = merge_role_messages(messages)
        messages = [asdict(m) for m in messages]
        assert len(messages), "Expected messages"
        return self._call_llamacpp(messages)

    def stream(self, messages: List[HistoryMessage]) -> Iterator[str]:
        messages = merge_role_messages(messages)
        messages = [asdict(m) for m in messages]
        assert len(messages), "Expected messages"
        yield from self._call_llamacpp_stream(messages)


def merge_role_messages(messages: List[HistoryMessage]) -> List[HistoryMessage]:
    merged_messages: list[HistoryMessage] = []
    for m in messages:
        prev_m = merged_messages[-1] if len(merged_messages) else None
        if not prev_m:
            merged_messages.append(m)
            continue

        prev_m: HistoryMessage
        if m.role != prev_m.role:
            merged_messages.append(m)
            continue

        merged_m = HistoryMessage(
            role=m.role,
            content='\n'.join([prev_m.content, m.content])
        )
        merged_messages[-1] = merged_m

    return merged_messages
