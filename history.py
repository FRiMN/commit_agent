import re
from dataclasses import dataclass
from enum import StrEnum
from typing import List

from llm_providers.common import AbstractLlmProvider


class HistoryMessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


@dataclass
class HistoryMessage:
    role: HistoryMessageRole
    content: str


class History(object):
    talk_history: List[HistoryMessage]

    def __init__(self, llm_provider: AbstractLlmProvider):
        self.provider = llm_provider
        self.talk_history = []

    @property
    def current_message(self) -> str:
        if not self.talk_history:
            return ""

        message = self.talk_history[-1].content
        match = re.search(r"<commit_message>(.*?)</commit_message>", message, re.DOTALL)
        return match.group(1).strip() if match else ""

    @property
    def current_pr_message(self) -> str:
        if not self.talk_history:
            return ""

        message = self.talk_history[-1].content
        match = re.search(r"<?pr_description>(.*?)</pr_description>", message, re.DOTALL)
        return match.group(1).strip() if match else ""

    def assistant_think(self, prompt: str | None) -> str:
        if prompt:
            user_msg = HistoryMessage(role=HistoryMessageRole.user, content=prompt)
            self.talk_history.append(user_msg)

        reply = self.provider(self.talk_history)

        # if "<commit_message>" not in reply:
        #     reminder = HistoryMessage(
        #         role=HistoryMessageRole.user,
        #         content="Ты забыл обернуть сообщение коммита в теги <commit_message>...</commit_message>. Повтори ответ.",
        #     )
        #     self.talk_history.append(reminder)
        #     reply = self.provider(self.talk_history)

        assist_msg = HistoryMessage(role=HistoryMessageRole.assistant, content=reply)
        self.talk_history.append(assist_msg)

        return re.sub(
            r"<commit_message>.*?</commit_message>|<pr_description>.*?</pr_description>",
            "",
            reply,
            flags=re.DOTALL,
        ).strip()
