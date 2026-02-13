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


class View(object):
    @staticmethod
    def cprint(text: str, color: str = Colors.RESET, end: str = "\n"):
        print(f"{color}{text}{Colors.RESET}", end=end)

    @staticmethod
    def wait_user_input() -> str:
        return input().strip()

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
        self.cprint(text, Colors.YELLOW + Colors.BOLD)

    def show_reply(self, text: str):
        self.cprint(text, Colors.MAGENTA)

    def show_debug(self, text: str):
        self.cprint(text, Colors.GRAY)

    def show_user_input_prefix(self):
        self.cprint(">>> ", Colors.GREEN, end="")
