# commit_agent

Интерактивный CLI-агент для генерации сообщений коммитов с помощью LLM.

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

## Доступные команды

| Команда | Описание |
|---------|----------|
| `/help` | Показать список доступных команд |
| `/undo` | Отменить последнее изменение сообщения коммита |
| `/diff` | Показать diff последнего коммита |
| `/history` | Показать полную историю диалога |
| `/commit` или `/save` | Сохранить сообщение и выполнить amend |
| `/exit` | Выйти без сохранения |

## Как это работает

1. Агент анализирует diff последнего коммита и примеры сообщений из вашего репозитория
2. Ведет диалог для создания идеального commit message
3. Сохраняет сообщение с помощью git amend

## Лицензия

GNU GPLv3. Подробности в [LICENSE](LICENSE) файле.