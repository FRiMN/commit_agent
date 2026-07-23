import re
from dataclasses import dataclass
from enum import StrEnum
from typing import List

from llm_providers.common import AbstractLlmProvider


class HistoryMessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Mode(StrEnum):
    commit = "commit"
    pr = "pr"


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

    def review_with_agent(self, text: str, system_prompt: str) -> str:
        temp_history = [
            HistoryMessage(role=HistoryMessageRole.system, content=system_prompt),
            HistoryMessage(role=HistoryMessageRole.user, content=f"Проверь это сообщение:\n\n{text}"),
        ]
        return self.provider(temp_history)

    @staticmethod
    def parse_review_result(response: str) -> tuple[bool, str]:
        status_match = re.search(r"<review_status>(.*?)</review_status>", response, re.DOTALL)
        is_ok = bool(status_match and status_match.group(1).strip() == "ok")

        issues_match = re.search(r"<review_issues>(.*?)</review_issues>", response, re.DOTALL)
        issues = issues_match.group(1).strip() if issues_match else ""

        return is_ok, issues

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
