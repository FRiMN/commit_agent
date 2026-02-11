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
from typing import List, Dict

import requests

print(f"Работаю в: {os.getcwd()}")
print(f"Аргументы: {sys.argv[1:]}")

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "AnInterestingSurname/gemmasutra-mini-2b-v1:latest"
SYSTEM_PROMPT_TEMPLATE = """Ты помогаешь написать сообщение для git-коммита.
Ниже представлен diff изменений.
Твоя задача — предложить краткое, информативное сообщение, описывающее суть изменений.
Используй повелительное наклонение (как в английском: 'Add', 'Fix', 'Update' и т.д.).
Сообщение должно быть на русском или английском языке (определи по содержимому diff).
Не добавляй лишних комментариев, только само сообщение коммита.

Diff:

{}
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

    print("Получение diff последнего коммита...")
    diff = get_last_commit_diff()

    print("Diff получен (первые 500 символов):")
    print(diff[:500] + ("..." if len(diff) > 500 else ""))
    print()

    messages.append(
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(diff)}
    )

    print("Думаю...")
    reply = ollama_chat_completion(messages, args.model, args.ollama_url)

    # Добавляем ответ ассистента в историю
    messages.append({"role": "assistant", "content": reply})
    current_message = reply

    print("\n--- Предлагаемое сообщение коммита ---")
    print(reply)
    print("---")
    print("\nВедите диалог с LLM для уточнения сообщения.")
    print("Команды: 'commit' или 'save' — сохранить текущее предложение и выйти.")
    print("'exit' или Ctrl+C — выйти без сохранения.")

    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nВыход без сохранения.")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() == "diff":
            print("Diff:")
            print(diff)
            continue

        if user_input.lower() in ("commit", "save"):
            break

        if user_input.lower() == "exit":
            print("Выход без сохранения.")
            sys.exit(0)

        # Добавляем сообщение пользователя в историю
        messages.append({"role": "user", "content": user_input})

        print("Думаю...")
        reply = ollama_chat_completion(messages, args.model, args.ollama_url)
        messages.append({"role": "assistant", "content": reply})
        current_message = reply

        print("\n--- Ответ LLM ---")
        print(reply)
        print("---\n")

    # Сохраняем сообщение через amend
    if not current_message.strip():
        print("Ошибка: сообщение коммита пустое. Операция отменена.")
        sys.exit(1)

    print(f"\nСохраняем сообщение:\n{current_message}")
    try:
        # Выполняем amend с новым сообщением
        run_git_command(["commit", "--amend", "-m", current_message])
        print("Сообщение коммита успешно обновлено.")
    except GitError as e:
        print(f"Ошибка при выполнении git commit --amend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()