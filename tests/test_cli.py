from typer.testing import CliRunner

from tribal_assistant.cli import app
from tribal_assistant.version import __version__

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("serve", "sync", "status", "world"):
        assert command in result.stdout
