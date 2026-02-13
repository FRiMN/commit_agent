from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from history import HistoryMessage


class AbstractLlmProvider(object):
    def __call__(self, messages: List[HistoryMessage]) -> str:
        raise NotImplementedError()


class LLMError(Exception):
    """Ошибка взаимодействия с провайдером LLM."""
    pass
