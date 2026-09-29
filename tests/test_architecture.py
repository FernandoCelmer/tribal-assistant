import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "tribal_assistant"


def imports(layer: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in (PACKAGE / layer).rglob("*.py"):
        names = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
            elif isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
        found[str(path.relative_to(PACKAGE))] = names
    return found


def offenders(layer: str, forbidden: tuple[str, ...]) -> list[str]:
    return sorted(
        f"{path}: {name}"
        for path, names in imports(layer).items()
        for name in names
        if any(name == f or name.startswith(f + ".") for f in forbidden)
    )


@pytest.mark.parametrize(
    ("layer", "forbidden"),
    [
        ("core", ("fastapi", "starlette", "tribal_assistant.api", "tribal_assistant.mcp", "tribal_assistant.cli")),
        ("mcp", ("tribal_assistant.core", "tribal_assistant.api", "sqlalchemy", "playwright")),
        ("api", ("tribal_assistant.mcp", "tribal_assistant.cli", "playwright")),
    ],
)
def test_layers_only_depend_downwards(layer: str, forbidden: tuple[str, ...]) -> None:
    assert offenders(layer, forbidden) == []
