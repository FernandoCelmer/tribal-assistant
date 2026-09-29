from tribal_assistant.core.accounts.context import AccountContext, use_account
from tribal_assistant.core.game.modules.game_sync import Findings, ReportClock


def account(account_id: int) -> AccountContext:
    return AccountContext(id=account_id, name=f"a{account_id}", server="br1", world_url="https://br1.example", username="u", password="p")


def test_findings_of_one_account_never_reach_another() -> None:
    with use_account(account(101)):
        Findings.screens().append("market")
        Findings.texts().append(("k", "mail", "t", "x"))

    with use_account(account(102)):
        assert Findings.screens() == []
        assert Findings.texts() == []
        Findings.clear()

    with use_account(account(101)):
        assert Findings.screens() == ["market"]
        Findings.clear()
        assert Findings.screens() == []


def test_report_clock_runs_per_account() -> None:
    with use_account(account(201)):
        ReportClock.mark()
        assert ReportClock.due() is False

    with use_account(account(202)):
        assert ReportClock.due() is True
