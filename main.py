# /// script
# dependencies = [
#   "requests",
# ]
# requires-python = ">=3.8"
# ///
import sys

from commands.dispatcher import CommandDispatcher
from commands.commands import (
    AbstractCommand,
    CommitCommand,
    ExitCommand,
    HelpCommand,
    SaveCommand,
    ShowDiffCommand,
    UndoCommand,
)
from git_provider import ShellGitProvider
from history import History, HistoryMessage, HistoryMessageRole
from llm_providers.ollama import OllamaLlmProvider
from pager_provider import LessPagerProvider
from view import View

SYSTEM_PROMPT = """# Commit Message Composer

Ты эксперт по git-коммитам. Твоя задача - помочь написать идеальное сообщение коммита.

## Твои обязанности:
1. Проанализировать полученный diff изменений
2. Предложить краткое, информативное сообщение коммита на русском или английском языке
3. Переносить текст на новую строку, если он длиннее 80 символов

## Анализ стиля коммитов:
В начале диалога я предоставлю примеры сообщений коммитов из вашего репозитория.
Проанализируй их и имитируй обнаруженный стиль (язык, форма глагола, форматирование) в своём предложении.
Если примеров нет, используй стандартные best practices для git-коммитов.

## Форматирование:
- Всегда указывай сообщение коммита в самом конце после "Commit message:" 
- Заканчивай сообщение паттерном "@@@@"
- например: "Commit message: Add new authentication feature @@@@"

## Правила ведения диалога:
- НЕ ЗАБЫВАЙ: Вся история содержит оригинальный diff — ВСЕГДА опирайся на него
- При уточнениях от пользователя сохраняй контекст оригинального diff
- Не пересматривай diff, используй его как источник истины
- Каждый ответ должен учитывать весь предыдущий контекст диалога

## Порядок работы:
1. Сразу в первом сообщении предложи вариант commit message (даже если есть вопросы)
2. Отвечай на вопросы и уточнения пользователя
3. Модифицируй commit message по запросу
4. Веди диалог естественно, не теряя контекст diff
"""

view = View()
llm_provider = OllamaLlmProvider(
    "mistral-large-3:675b-cloud", "http://localhost:11434", view
)
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
        loop()
    except (KeyboardInterrupt, EOFError):
        view.show_error("Прерываю выполнение.")
