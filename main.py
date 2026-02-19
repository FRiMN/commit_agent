# /// script
# dependencies = [
#   "requests",
# ]
# requires-python = ">=3.8"
# ///
from pathlib import Path

from commands.dispatcher import CommandDispatcher
from commands.commands import (
    CommitCommand,
    ExitCommand,
    HelpCommand,
    SaveCommand,
    ShowDiffCommand,
    UndoCommand,
    HistoryCommand,
)
from git_provider import ShellGitProvider
from history import History, HistoryMessage, HistoryMessageRole
from llm_providers.ollama import OllamaLlmProvider
from pager_provider import LessPagerProvider
from view import View


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent / "system_prompt.md"
    return prompt_path.read_text()


SYSTEM_PROMPT = _load_system_prompt()

view = View()
llm_provider = OllamaLlmProvider("qwen2.5-coder:14b", "http://localhost:11434", view)
history = History(llm_provider)
git_provider = ShellGitProvider()
pager = LessPagerProvider()

help_command = HelpCommand(view)
commands = (
    UndoCommand(history, view),
    ExitCommand(),
    SaveCommand(history, git_provider, view),
    CommitCommand(history, git_provider, view),
    ShowDiffCommand(git_provider, pager),
    HistoryCommand(history, pager),
    help_command,
)
command_dispatcher = CommandDispatcher(commands)
help_command.set_command_dispatcher(command_dispatcher)


def assistant_think(user_input: str | None):
    view.show_thinking()
    reply = history.assistant_think(user_input)
    view.show_reply(reply)
    view.show_current_commit_message(history.current_message)


def loop():
    user_input = None
    skip_think = False
    while True:
        if not skip_think:
            assistant_think(user_input)

        view.show_user_input_prefix()
        user_input = view.wait_user_input()

        skip_think = False
        if command_dispatcher.is_command(user_input):
            command_dispatcher(user_input)
            skip_think = True

            if command_dispatcher.is_terminator(user_input):
                break


if __name__ == "__main__":
    sys_msg = HistoryMessage(role=HistoryMessageRole.system, content=SYSTEM_PROMPT)
    history.talk_history.append(sys_msg)

    samples = git_provider.get_commit_messages_samples()
    if samples:
        samples_msg = HistoryMessage(
            role=HistoryMessageRole.user,
            content=f"Вот примеры сообщений коммитов из вашего репозитория:\n{samples}",
        )
        history.talk_history.append(samples_msg)

    diff = git_provider.get_last_diff()
    diff_msg = HistoryMessage(
        role=HistoryMessageRole.user, content=f"Вот diff изменений:\n{diff}"
    )
    history.talk_history.append(diff_msg)

    try:
        help_command()
        loop()
    except (KeyboardInterrupt, EOFError):
        view.show_error("Прерываю выполнение.")
