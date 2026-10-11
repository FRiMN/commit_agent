# /// script
# dependencies = [
#   "requests",
#   "prompt-toolkit",
# ]
# requires-python = ">=3.8"
# ///
import argparse
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
from history import History, HistoryMessage, HistoryMessageRole, Mode
from llm_providers.ollama import OllamaLlmProvider
from llm_providers.llamacpp import LlamaCppLlmProvider
from pager_provider import LessPagerProvider
from view import View


def _load_system_prompt(mode: Mode) -> str:
    prompt_files = {
        Mode.commit: "system_prompt.md",
        Mode.pr: "system_prompt_pr.md",
        Mode.release: "system_prompt_release.md",
    }
    prompt_path = Path(__file__).parent / prompt_files[mode]
    return prompt_path.read_text()


def _parse_args():
    parser = argparse.ArgumentParser(description="Git commit message assistant")
    parser.add_argument(
        "--pr", "--mr",
        action="store_true",
        dest="pr_mode",
        help="PR/MR description mode: generate a full PR/MR description from branch diff and commits",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        dest="release_mode",
        help="Release description mode: generate release notes by comparing the latest two 'v' tags",
    )
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Base branch to merge into (default: auto-detect main/master)",
    )
    return parser.parse_args()


view = View()
args = _parse_args()
if args.release_mode:
    mode = Mode.release
elif args.pr_mode:
    mode = Mode.pr
else:
    mode = Mode.commit

if mode == Mode.commit:
    # model = "ministral-3:8b"
    model = "Tiel-Coder-35B-A3B"
elif mode == Mode.release:
    model = "nemotron-3-nano:4b"
else:
    model = "qwen3:14b"
# model = "glm-4.7:cloud"

# llm_provider = OllamaLlmProvider(model, "http://192.168.1.10:11434", view)
llm_provider = LlamaCppLlmProvider(model, "http://192.168.1.10:9931", view)
history = History(llm_provider)
git_provider = ShellGitProvider()
pager = LessPagerProvider()

system_prompt = _load_system_prompt(mode)

help_command = HelpCommand(view)
commands: list = [
    UndoCommand(history, view),
    ExitCommand(),
    HistoryCommand(history, pager),
    help_command,
]

if mode == Mode.commit:
    commands = [
        SaveCommand(history, git_provider, view),
        CommitCommand(history, git_provider, view),
        ShowDiffCommand(git_provider, pager),
    ] + commands

command_dispatcher = CommandDispatcher(commands)
help_command.set_command_dispatcher(command_dispatcher)
view.set_completer_words([cmd.trigger for cmd in commands])


def assistant_think(user_input: str | None):
    view.show_thinking()
    history.assistant_think_stream(user_input, view.stream_write)
    view.stream_end()
    if mode == Mode.commit:
        view.show_current_commit_message(history.current_message)


def loop():
    user_input = None
    skip_think = False
    while True:
        if not skip_think:
            assistant_think(user_input)

        user_input = view.wait_user_input()

        skip_think = False
        if command_dispatcher.is_command(user_input):
            command_dispatcher(user_input)
            skip_think = True

            if command_dispatcher.is_terminator(user_input):
                break


if __name__ == "__main__":
    sys_msg = HistoryMessage(role=HistoryMessageRole.user, content=system_prompt)
    history.talk_history.append(sys_msg)

    if mode == Mode.pr:
        base_branch = args.base if args.base else git_provider.get_default_branch()
        view.show_debug(f"Base branch: {base_branch}")

        branch_commits = git_provider.get_branch_commits(base_branch)
        if branch_commits:
            commits_msg = HistoryMessage(
                role=HistoryMessageRole.user,
                content=f"Вот коммиты текущей ветки:\n{branch_commits}",
            )
            history.talk_history.append(commits_msg)
    elif mode == Mode.release:
        tags = git_provider.get_latest_tags()
        if len(tags) < 2:
            view.show_error("Не найдено достаточно тегов с префиксом 'v' для сравнения (нужно минимум 2).")
        else:
            latest_tag, previous_tag = tags
            view.show_debug(f"Comparing {previous_tag} -> {latest_tag}")

            commits = git_provider.get_commits_between_tags(previous_tag, latest_tag)
            if commits:
                commits_msg = HistoryMessage(
                    role=HistoryMessageRole.user,
                    content=f"Вот список коммитов между {previous_tag} и {latest_tag}:\n{commits}",
                )
                history.talk_history.append(commits_msg)

            # diff = git_provider.get_diff_between_tags(previous_tag, latest_tag)
            # if diff:
            #     diff_msg = HistoryMessage(
            #         role=HistoryMessageRole.user,
            #         content=f"Вот diff изменений между {previous_tag} и {latest_tag}:\n{diff}",
            #     )
            #     history.talk_history.append(diff_msg)
    else:
        samples = git_provider.get_commit_messages_samples()
        if samples:
            samples_msg = HistoryMessage(
                role=HistoryMessageRole.user,
                content=f"Вот примеры сообщений коммитов из текущего репозитория:\n{samples}",
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
