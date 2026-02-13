from typing import Iterable

from commands.commands import AbstractCommand


class CommandDispatcher(object):
    commands: Iterable[AbstractCommand]

    def __init__(self, commands: Iterable[AbstractCommand]):
        self.commands = commands

    def is_command(self, trigger: str) -> bool:
        return bool(self.get_command(trigger))

    def is_terminator(self, trigger: str) -> bool:
        return self.get_command(trigger).is_terminator

    def get_command(self, trigger: str) -> AbstractCommand | None:
        try:
            command = next(iter(
                [_ for _ in self.commands if _.trigger == trigger.lower().strip()]
            ))
        except StopIteration:
            return None
        return command

    def __call__(self, trigger: str):
        command = self.get_command(trigger)
        if not command:
            return

        command()
