from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style


class Colors:
    """ANSI color codes"""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


PROMPT_STYLE = Style.from_dict({
    "prompt": "ansigreen bold",
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
            style=PROMPT_STYLE,
            completer=self._completer,
            complete_while_typing=True,
        )

    @staticmethod
    def cprint(text: str, color: str = Colors.RESET, end: str = "\n"):
        print(f"{color}{text}{Colors.RESET}", end=end)

    def wait_user_input(self) -> str:
        return self._prompt.prompt().strip()

    def show_question(self, text: str):
        self.cprint(text, Colors.CYAN, end="")

    def show_thinking(self):
        self.cprint("Думаю...", Colors.YELLOW)

    def show_process(self, text: str):
        self.cprint(text, Colors.YELLOW)

    def show_info(self, text: str):
        self.cprint(text, Colors.BLUE)

    def show_error(self, text: str):
        self.cprint(text, Colors.RED)

    def show_current_commit_message(self, text: str):
        self.show_info("Текущее сообщение коммита:")
        self.cprint(text, Colors.RESET + Colors.BOLD)

    def show_reply(self, text: str):
        self.cprint(text, Colors.MAGENTA)

    def show_debug(self, text: str):
        self.cprint(text, Colors.GRAY)
