import subprocess
from typing import List


class GitError(Exception):
    """Ошибка выполнения git-команды."""
    pass


class AbstractGitProvider(object):
    def amend(self, message: str) -> None:
        raise NotImplementedError()

    def get_last_diff(self) -> str:
        raise NotImplementedError()

    def get_commit_messages_samples(self) -> str:
        raise NotImplementedError()

    def get_default_branch(self) -> str:
        raise NotImplementedError()

    def get_branch_diff(self, base_branch: str | None = None) -> str:
        raise NotImplementedError()

    def get_branch_commits(self, base_branch: str | None = None) -> str:
        raise NotImplementedError()


class ShellGitProvider(AbstractGitProvider):
    @staticmethod
    def _run_command(args: List[str], check: bool = True) -> str:
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

    def amend(self, message: str):
        self._run_command(["commit", "--amend", "-m", message])

    def get_last_diff(self) -> str:
        """
        Возвращает diff последнего коммита (изменения относительно родителя).
        Для первого коммита возвращает diff всего коммита.
        """
        # Проверяем, есть ли родительский коммит
        try:
            self._run_command(["rev-parse", "HEAD^"], check=False)
            has_parent = True
        except GitError:
            has_parent = False

        if has_parent:
            diff = self._run_command(["diff", "HEAD^", "HEAD", "--no-color"])
        else:
            # Первый коммит: берём diff из самого коммита
            diff = self._run_command(["show", "--format=", "--no-color", "--patch", "HEAD"])
        return diff

    def get_commit_messages_samples(self) -> str:
        """
        Возвращает форматированные примеры сообщений коммитов из репозитория.
        Получает последние 20 сообщений и форматирует их как список.
        """
        try:
            messages = self._run_command(["log", "--format=%s", "-20"], check=False)
            if not messages:
                return ""

            lines = messages.split("\n")[1:]
            return "\n".join([f"- {msg}" for msg in lines if msg])
        except GitError:
            return ""

    def get_default_branch(self) -> str:
        """
        Определяет базовую ветку (main или master).
        Приоритет: symbolic-ref -> локальная main -> локальная master -> main по умолчанию.
        """
        # 1. Попробовать получить через symbolic-ref (GitHub стандарт)
        try:
            ref = self._run_command(
                ["symbolic-ref", "refs/remotes/origin/HEAD"], check=False
            )
            # Формат: "ref: refs/remotes/origin/main" -> "main"
            branch = ref.split("/")[-1]
            if branch in ("main", "master"):
                return branch
        except GitError:
            pass

        # 2. Проверить существование локальных веток
        try:
            self._run_command(["rev-parse", "--verify", "main"], check=False)
            return "main"
        except GitError:
            pass

        try:
            self._run_command(["rev-parse", "--verify", "master"], check=False)
            return "master"
        except GitError:
            pass

        return "main"

    def get_branch_diff(self, base_branch: str | None = None) -> str:
        """
        Возвращает diff текущей ветки относительно base_branch.
        Если base_branch не указан, определяет автоматически.
        """
        if base_branch is None:
            base_branch = self.get_default_branch()

        diff = self._run_command(["diff", f"{base_branch}...HEAD", "--no-color"])
        return diff

    def get_branch_commits(self, base_branch: str | None = None) -> str:
        """
        Возвращает список коммитов текущей ветки относительно base_branch.
        Формат: "- hash short_message"
        """
        if base_branch is None:
            base_branch = self.get_default_branch()

        try:
            messages = self._run_command(
                ["log", f"{base_branch}...HEAD", "--format=- %h %s"], check=False
            )
            return messages if messages else ""
        except GitError:
            return ""
