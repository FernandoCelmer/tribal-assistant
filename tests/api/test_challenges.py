from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.challenges import AUTO, BLOCKED, ChallengePlan
from tribal_assistant.core.agents.learning import LessonBook
from tribal_assistant.core.game.scraper.awards import AwardsParser

AWARDS = """
<div class="award-group" id="award-group-growth"><div class="award-group-head">Realizações de crescimento</div>
<div class="award-group-content">
<div class="award-box clearfix"><div class="award level1"></div><div class="award-desc">
<strong>Arquiteto (Madeira - Nível 1)</strong><p>Conclua um total de 10 níveis de edifícios!</p>
<p class="inactive">Próximo nível: Conclua um total de 150 níveis de edifícios!</p>
<div class="progress-bar"><span class="label">52 / 150</span></div></div></div>
<div class="award-box clearfix"><div class="award level0"></div><div class="award-desc">
<strong>Mestre das Missões</strong><p class="inactive">Complete 40 missões!</p>
<div class="progress-bar"><span class="label">37 / 40</span></div></div></div>
<div class="award-box clearfix"><div class="award level0"></div><div class="award-desc">
<strong>Comandante de guerra</strong><p class="inactive">Ataque 10 diferentes jogadores</p>
<div class="progress-bar"><span class="label">0 / 1<span class="grey">.</span>000</span></div></div></div>
</div></div>
"""


def test_awards_parser_reads_level_progress_and_next_goal() -> None:
    items = {i["name"]: i for i in AwardsParser.parse(AWARDS)}

    assert items["Arquiteto"]["level"] == 1
    assert (items["Arquiteto"]["current"], items["Arquiteto"]["target"]) == (52, 150)
    assert items["Arquiteto"]["description"] == "Conclua um total de 150 níveis de edifícios!"
    assert items["Comandante de guerra"]["target"] == 1000


def test_plan_never_chases_combat_against_players() -> None:
    assert ChallengePlan.pursuit("Comandante de guerra").status == BLOCKED
    assert ChallengePlan.pursuit("Mestre das Missões").status == AUTO
    assert ChallengePlan.closest(AwardsParser.parse(AWARDS))[0]["name"] == "Mestre das Missões"


async def test_challenges_are_stored_and_served(session: AsyncSession, client: AsyncClient, tmp_path: Path) -> None:
    path = tmp_path / "awards.html"
    path.write_text(AWARDS, encoding="utf-8")
    await LessonBook(session).challenges(path)
    await session.commit()

    body = (await client.get("/api/v1/challenges")).json()

    assert {i["name"] for i in body["items"]} == {"Arquiteto", "Mestre das Missões", "Comandante de guerra"}
    assert body["summary"]["blocked"] == 1
