import sys

from git_provider import AbstractGitProvider
from history import History
from pager_provider import AbstractPagerProvider
from view import View


class AbstractCommand(object):
    trigger: str

    def __call__(self):
        raise NotImplementedError()


class UndoCommand(AbstractCommand):
    trigger = "/undo"

    def __init__(self, history: History, view: View):
        self.history = history
        self.view = view

    def __call__(self):
        self.history.talk_history.pop()
        self.view.show_info("Последнее изменение сообщения коммита отменено.")
        self.view.show_current_commit_message(self.history.current_message)


class ExitCommand(AbstractCommand):
    trigger = "/exit"

    def __call__(self):
        raise KeyboardInterrupt()


class SaveCommand(AbstractCommand):
    trigger = "/save"

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


class ShowDiffCommand(AbstractCommand):
    trigger = "/diff"

    def __init__(self, git_provider: AbstractGitProvider, pager: AbstractPagerProvider):
        self.git = git_provider
        self.pager = pager

    def __call__(self):
        diff = self.git.get_last_diff()
        self.pager(diff)
