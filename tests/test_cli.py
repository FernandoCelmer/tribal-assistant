from typer.testing import CliRunner

from tribal_assistant import __version__
from tribal_assistant.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("serve", "sync", "status", "farm", "world"):
        assert command in result.stdout


def test_farm_add_rejects_bad_coords() -> None:
    result = runner.invoke(app, ["farm", "add", "500-500"])
    assert result.exit_code == 1
