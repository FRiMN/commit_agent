# /// script
# dependencies = [
#   "requests",
# ]
# requires-python = ">=3.8"
# ///
import argparse
import os
import subprocess
import sys
import tempfile
from typing import List, Dict

import requests


# ANSI color codes
class Colors:
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


# Function to print colored text
def cprint(text: str, color: str = Colors.RESET, end: str = "\n"):
    print(f"{color}{text}{Colors.RESET}", end=end)


cprint(f"Работаю в: {os.getcwd()}", Colors.GRAY)
cprint(f"Аргументы: {sys.argv[1:]}", Colors.GRAY)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"

SYSTEM_PROMPT_TEMPLATE = """# Commit Message Composer

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
Всегда указывай сообщение коммита в самом конце после "Commit message:" 
например: "Commit message: Add new authentication feature"

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


class GitError(Exception):
    """Ошибка выполнения git-команды."""

    pass


class OllamaError(Exception):
    """Ошибка взаимодействия с Ollama."""

    pass


def run_git_command(args: List[str], check: bool = True) -> str:
    """
    Выполняет git-команду и возвращает stdout.
    При ошибке выбрасывает GitError.
    """
    try:
        proc = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=check,
        )
        if proc.returncode != 0:
            raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
        return proc.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"git {' '.join(args)}: {e.stderr.strip()}") from e
    except FileNotFoundError as e:
        raise GitError("Git не установлен или не найден в PATH") from e


def get_last_commit_diff() -> str:
    """
    Возвращает diff последнего коммита (изменения относительно родителя).
    Для первого коммита возвращает diff всего коммита.
    """
    # Проверяем, есть ли родительский коммит
    try:
        run_git_command(["rev-parse", "HEAD^"], check=False)
        has_parent = True
    except GitError:
        has_parent = False

    if has_parent:
        diff = run_git_command(["diff", "HEAD^", "HEAD", "--no-color"])
    else:
        # Первый коммит: берём diff из самого коммита
        diff = run_git_command(["show", "--format=", "--no-color", "--patch", "HEAD"])
    return diff


def get_commit_messages_samples() -> str:
    """
    Возвращает форматированные примеры сообщений коммитов из репозитория.
    Получает последние 20 сообщений и форматирует их как список.
    """
    try:
        messages = run_git_command(["log", "--format=%s", "-20"], check=False)
        if not messages:
            return ""

        lines = messages.split("\n")
        examples = "\n".join([f"- {msg}" for msg in lines if msg])
        return f"Вот примеры сообщений коммитов из вашего репозитория:\n{examples}"
    except GitError:
        return ""


def ollama_chat_completion(
    messages: List[Dict[str, str]],
    model: str,
    url: str,
) -> str:
    """
    Отправляет запрос к /api/chat Ollama и возвращает текст ответа ассистента.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    try:
        resp = requests.post(f"{url}/api/chat", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise OllamaError(f"Ошибка соединения с Ollama: {e}") from e
    except (KeyError, ValueError) as e:
        raise OllamaError(f"Некорректный ответ от Ollama: {e}") from e


def get_commit_message(message: str) -> str:
    return message.split("Commit message:")[-1].strip()


def show_diff_with_pager(diff: str) -> None:
    cprint("Использовать ли less? [Y/n]: ", Colors.CYAN, end="")
    try:
        ans = input().strip()
        if not ans or ans.lower() in ("y", "yes"):
            pager = "less"
        else:
            cprint("Команда: ", Colors.CYAN, end="")
            pager = input().strip()
    except (KeyboardInterrupt, EOFError):
        pager = ""

    if not pager:
        return

    fd, temp_file = tempfile.mkstemp(text=True)
    try:
        os.write(fd, diff.encode())
        os.close(fd)
        parts = pager.split()
        parts.append(temp_file)
        subprocess.call(parts)
    finally:
        os.unlink(temp_file)


def main():
    parser = argparse.ArgumentParser(
        description="Интерактивное создание сообщения для последнего коммита с помощью Ollama"
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL),
        help=f"Модель Ollama (по умолчанию: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL),
        help=f"URL сервера Ollama (по умолчанию: {DEFAULT_OLLAMA_URL})",
    )
    args = parser.parse_args()

    messages = []
    commit_examples = get_commit_messages_samples()

    cprint("Получение diff последнего коммита...", Colors.YELLOW)
    diff = get_last_commit_diff()

    cprint("Diff получен (первые 500 символов):", Colors.YELLOW)
    cprint(diff[:500] + ("..." if len(diff) > 500 else ""), Colors.GRAY)
    cprint("")

    cprint("Ведите диалог с LLM для уточнения сообщения.", Colors.BOLD)
    cprint(
        "Команды: '/commit' или '/save' — сохранить текущее предложение и выйти.",
        Colors.BLUE,
    )
    cprint("'/exit' или Ctrl+C — выйти без сохранения.", Colors.BLUE)
    cprint("'/diff' — показать полный diff", Colors.BLUE)
    cprint("'/message' — показать текущее сообщение коммита", Colors.BLUE)
    cprint("")

    messages.append({"role": "system", "content": SYSTEM_PROMPT_TEMPLATE})

    if commit_examples:
        messages.append({"role": "user", "content": commit_examples})

    messages.append({"role": "user", "content": f"Вот diff изменений: {diff}"})

    cprint("Думаю...", Colors.YELLOW)
    reply = ollama_chat_completion(messages, args.model, args.ollama_url)

    # Добавляем ответ ассистента в историю
    messages.append({"role": "assistant", "content": reply})
    current_message = get_commit_message(reply)

    cprint(reply, Colors.MAGENTA)

    while True:
        try:
            cprint(">>> ", Colors.GREEN, end="")
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            cprint("\nВыход без сохранения.", Colors.RED)
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() == "/diff":
            show_diff_with_pager(diff)
            continue

        if user_input.lower() == "/message":
            cprint("Текущее сообщение коммита:", Colors.CYAN)
            cprint(current_message, Colors.YELLOW)
            continue

        if user_input.lower() in ("/commit", "/save"):
            break

        if user_input.lower() == "/exit":
            cprint("Выход без сохранения.", Colors.RED)
            sys.exit(0)

        # Добавляем сообщение пользователя в историю
        messages.append({"role": "user", "content": user_input})

        cprint("Думаю...", Colors.YELLOW)
        reply = ollama_chat_completion(messages, args.model, args.ollama_url)
        messages.append({"role": "assistant", "content": reply})
        current_message = get_commit_message(reply)

        cprint(reply, Colors.MAGENTA)

    # Сохраняем сообщение через amend
    if not current_message.strip():
        cprint("Ошибка: сообщение коммита пустое. Операция отменена.", Colors.RED)
        sys.exit(1)

    cprint(f"\nСохраняем сообщение:", Colors.GREEN + Colors.BOLD)
    cprint(current_message, Colors.YELLOW)
    try:
        # Выполняем amend с новым сообщением
        run_git_command(["commit", "--amend", "-m", current_message])
        cprint("Сообщение коммита успешно обновлено.", Colors.GREEN)
    except GitError as e:
        cprint(f"Ошибка при выполнении git commit --amend: {e}", Colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()
