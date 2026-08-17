from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    enabled: bool
    executor: Any


class ToolRegistry:
    """
    Единый каталог инструментов EddieAI.

    Agent не должен напрямую знать, как устроен
    каждый конкретный инструмент.
    """

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        executor: Any,
        description: str,
        enabled: bool = True,
    ):
        if not name.strip():
            raise ValueError(
                "Tool name cannot be empty."
            )

        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            enabled=enabled,
            executor=executor,
        )

    def get(
        self,
        name: str,
    ) -> ToolSpec | None:
        return self._tools.get(name)

    def require(
        self,
        name: str,
    ) -> ToolSpec:
        tool = self.get(name)

        if tool is None:
            raise KeyError(
                f"Tool not found: {name}"
            )

        if not tool.enabled:
            raise PermissionError(
                f"Tool disabled: {name}"
            )

        return tool

    def enable(
        self,
        name: str,
    ):
        tool = self.get(name)

        if tool is None:
            raise KeyError(
                f"Tool not found: {name}"
            )

        tool.enabled = True

    def disable(
        self,
        name: str,
    ):
        tool = self.get(name)

        if tool is None:
            raise KeyError(
                f"Tool not found: {name}"
            )

        tool.enabled = False

    def names(self):
        return list(
            self._tools.keys()
        )

    def describe(self):
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "enabled": tool.enabled,
            }
            for tool in self._tools.values()
        ]

    def call(
        self,
        name: str,
        method: str,
        **kwargs,
    ):
        tool = self.require(name)

        function: Callable | None = getattr(
            tool.executor,
            method,
            None,
        )

        if function is None:
            raise AttributeError(
                f"Tool '{name}' has no method "
                f"'{method}'."
            )

        return function(**kwargs)
