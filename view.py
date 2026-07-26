from pathlib import Path

from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text as cprint


STYLE = Style.from_dict({
    "prompt": "ansigreen bold",
    "thinking": "orange italic",
    "info": "blue",
    "error": "red",
    "debug": "gray",
    "reply": "magenta",
})


class View(object):
    def __init__(self):
        self._completer = None
        self._prompt = None
        self._history = FileHistory(Path.home() / ".commit_agent_history")

    def set_completer_words(self, words: list[str]):
        self._completer = WordCompleter(words)
        self._prompt = PromptSession(
            [("class:prompt", ">>> ")],
            history=self._history,
            style=STYLE,
            completer=self._completer,
            complete_while_typing=True,
        )

    @staticmethod
    def cprint(text: str, tag: str = "p"):
        cprint(HTML(f"<{tag}>{text}</{tag}>"), style=STYLE)

    def wait_user_input(self) -> str:
        return self._prompt.prompt().strip()

    def show_thinking(self):
        self.cprint("Думаю...", "thinking")

    def show_process(self, text: str):
        self.cprint(text, "orange")

    def show_info(self, text: str):
        self.cprint(text, "info")

    def show_error(self, text: str):
        self.cprint(text, "error")

    def show_current_commit_message(self, text: str):
        self.show_info("Текущее сообщение коммита:")
        self.cprint(text)

    def show_reply(self, text: str):
        self.cprint(text, "reply")

    def show_debug(self, text: str):
        self.cprint(text, "debug")
