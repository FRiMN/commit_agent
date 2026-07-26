# commit_agent

Интерактивный CLI-агент для генерации сообщений коммитов и описаний PR/MR с помощью LLM.

## Требования

- Python 3.8+
- [Ollama](https://ollama.com/) с моделью `qwen2.5-coder:14b`
- [Uv](https://github.com/astral-sh/uv) для управления зависимостями

## Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone git@github.com:FRiMN/commit_agent.git
cd commit_agent
```

2. Запустите Ollama:
```bash
ollama serve
```

3. Запустите агент:
```bash
uv run main.py
```

## Установка в качестве глобальной команды

Чтобы запускать агент из любой директории с git-репозиторием:

1. Создайте скрипт в `~/.local/bin/commit`:
```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/commit << 'EOF'
#!/bin/bash
exec uv run ~/commit_agent/main.py "$@"
EOF
chmod +x ~/.local/bin/commit
```

2. Убедитесь, что `~/.local/bin` в PATH (добавьте в `~/.bashrc` или `~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

3. Теперь можно запускать в любой директории с git-репозиторием:
```bash
cd my_project_dir
commit
```

## Режимы работы

### Commit Message Mode (по умолчанию)

Генерирует сообщение коммита на основе diff последнего коммита.

```bash
uv run main.py
```

### PR/MR Description Mode

Генерирует полное описание PR/MR на основе diff ветки и истории коммитов.

```bash
uv run main.py --pr
```

С явным указанием базовой ветки:

```bash
uv run main.py --pr --base develop
```

Или с использованием синонима `--mr`:

```bash
uv run main.py --mr
```

## Доступные команды

### Общие команды (доступны в обоих режимах)

| Команда | Описание |
|---------|----------|
| `/help` | Показать список доступных команд |
| `/undo` | Отменить последнее изменение |
| `/history` | Показать полную историю диалога |
| `/exit` | Выйти без сохранения |

### Команды режима коммитов

| Команда | Описание |
|---------|----------|
| `/diff` | Показать diff последнего коммита |
| `/commit` или `/save` | Сохранить сообщение и выполнить amend |

### Команды режима PR/MR

| Команда | Описание |
|---------|----------|
| `/pr` | Показать сгенерированное описание PR/MR |

## Как это работает

### Commit Message Mode
1. Агент анализирует diff последнего коммита и примеры сообщений из вашего репозитория
2. Ведет диалог для создания идеального commit message
3. Сохраняет сообщение с помощью git amend

### PR/MR Description Mode
1. Агент определяет базовую ветку (main/master) или принимает её из параметра `--base`
2. Анализирует полный diff текущей ветки относительно базовой
3. Анализирует историю коммитов на ветке
4. Генерирует структурированное описание PR/MR:
   - Summary
   - Changes
   - Technical Details
   - Testing
   - Breaking Changes / Migration Notes
   - Related Issues

## Автоопределение базовой ветки

При запуске в PR/MR режиме без параметра `--base` агент автоматически определяет базовую ветку:

1. Проверяет `git symbolic-ref refs/remotes/origin/HEAD` (стандарт GitHub)
2. Проверяет существование локальной ветки `main`
3. Проверяет существование локальной ветки `master`
4. По умолчанию использует `main`

## Лицензия

GNU GPLv3. Подробности в [LICENSE](LICENSE) файле.
