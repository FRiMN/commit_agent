from __future__ import annotations
import re
from typing import Iterable, TYPE_CHECKING

from git_provider import AbstractGitProvider
from history import History, HistoryMessage, HistoryMessageRole, Mode
from pager_provider import AbstractPagerProvider
from view import View

if TYPE_CHECKING:
    from commands.dispatcher import CommandDispatcher


class AbstractCommand(object):
    trigger: str
    is_terminator = False
    help_text: str = "No description available."

    def __call__(self):
        raise NotImplementedError()


class UndoCommand(AbstractCommand):
    trigger = "/undo"
    help_text = "Undo the last change to the commit message."

    def __init__(self, history: History, view: View):
        self.history = history
        self.view = view

    def __call__(self):
        if self.history.talk_history[-1].role == HistoryMessageRole.user:
            self.history.talk_history.pop()
        else:
            # Удаляем и сообщение юзера и сообщение ассистента
            self.history.talk_history.pop()
            self.history.talk_history.pop()

        self.view.show_info("Последнее изменение сообщения коммита отменено.")
        self.view.show_current_commit_message(self.history.current_message)


class ExitCommand(AbstractCommand):
    trigger = "/exit"
    help_text = "Exit the commit message editor without saving."
    is_terminator = True

    def __call__(self):
        pass


class SaveCommand(AbstractCommand):
    trigger = "/save"
    help_text = "Save the commit message and amend the last commit."
    is_terminator = True

    def __init__(self, history: History, git_provider: AbstractGitProvider, view: View):
        self.provider = git_provider
        self.view = view
        self.history = history

    def __call__(self):
        msg = self.history.current_message
        self.provider.amend(msg)
        self.view.show_info("Выполнен amend")


class CommitCommand(SaveCommand):
    trigger = "/commit"
    help_text = "Alias for /save. Save the commit message and amend the last commit."


class PRCommand(AbstractCommand):
    trigger = "/pr"
    help_text = "Display the generated PR/MR description for copy-paste."

    def __init__(self, history: History, view: View):
        self.history = history
        self.view = view

    def __call__(self):
        pr_message = self.history.current_pr_message
        if pr_message:
            self.view.show_info("PR/MR description:")
            self.view.show_reply(pr_message)
        else:
            self.view.show_error("No PR/MR description found in the conversation.")


class ReviewCommand(AbstractCommand):
    trigger = "/review"
    help_text = "Review the current message and auto-fix issues found."

    def __init__(self, history: History, view: View, mode: Mode, reviewer_system_prompt: str):
        self.history = history
        self.view = view
        self.mode = mode
        self.reviewer_system_prompt = reviewer_system_prompt

    def __call__(self):
        if self.mode == Mode.pr:
            current_msg = self.history.current_pr_message
        else:
            current_msg = self.history.current_message

        if not current_msg:
            self.view.show_error("Нет сообщения для проверки. Сначала сгенерируйте сообщение.")
            return

        self.view.show_thinking()
        review_response = self.history.review_with_agent(
            current_msg, self.reviewer_system_prompt
        )

        status_match = re.search(
            r"<review_status>(.*?)</review_status>", review_response, re.DOTALL
        )
        if status_match and status_match.group(1).strip() == "ok":
            self.view.show_process("✓ Сообщение прошло проверку")
            return

        issues_match = re.search(
            r"<review_issues>(.*?)</review_issues>", review_response, re.DOTALL
        )
        if issues_match:
            self.view.show_process("✗ Найдены проблемы. Замечания ревьювера:")
            self.view.show_reply(issues_match.group(1).strip())
        else:
            self.view.show_process("Ревьювер вернул неожиданный ответ. Показываю как есть:")
            self.view.show_reply(review_response)

        correction_msg = HistoryMessage(
            role=HistoryMessageRole.user,
            content=(
                "Исправь сообщение с учётом следующих замечаний ревьювера:\n\n"
                f"{issues_match.group(1).strip() if issues_match else review_response}"
            ),
        )
        self.history.talk_history.append(correction_msg)

        self.view.show_thinking()
        reply = self.history.assistant_think(None)
        self.view.show_reply(reply)

        if self.mode == Mode.pr:
            self.view.show_current_commit_message(self.history.current_pr_message)
        else:
            self.view.show_current_commit_message(self.history.current_message)


class ShowDiffCommand(AbstractCommand):
    trigger = "/diff"
    help_text = "Show the git diff of the last commit."

    def __init__(self, git_provider: AbstractGitProvider, pager: AbstractPagerProvider):
        self.git = git_provider
        self.pager = pager

    def __call__(self):
        diff = self.git.get_last_diff()
        self.pager(diff)


class HistoryCommand(AbstractCommand):
    trigger = "/history"
    help_text = "Show the full conversation history in less."

    def __init__(self, history: History, pager: AbstractPagerProvider):
        self.history = history
        self.pager = pager

    def __call__(self):
        history_str = "\n\n".join(
            f"[{msg.role.value.upper()}]: {msg.content}"
            for msg in self.history.talk_history
        )
        self.pager(history_str)


class HelpCommand(AbstractCommand):
    trigger = "/help"
    help_text = "Show a list of available commands and their descriptions."

    def __init__(self, view: View):
        self.view = view
        self._commands = None
        self._command_dispatcher = None

    @property
    def commands(self) -> Iterable[AbstractCommand]:
        if self._command_dispatcher is None:
            raise ValueError(
                "CommandDispatcher not set. Call set_command_dispatcher first."
            )
        return self._command_dispatcher.commands

    def set_command_dispatcher(self, command_dispatcher: CommandDispatcher):
        self._command_dispatcher = command_dispatcher

    def __call__(self):
        help_text = "Available commands:\n"
        for command in self.commands:
            help_text += f"- {command.trigger}: {command.help_text}\n"
        self.view.show_info(help_text)
