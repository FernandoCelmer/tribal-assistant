import json
from datetime import datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knob_rules import Metrics
from tribal_assistant.core.agents.knobs import Knobs, KnobStore, Tuner
from tribal_assistant.core.config import settings
from tribal_assistant.core.game.camera import Shot
from tribal_assistant.core.game.scraper.game import BuildingSnapshot, GameVillage
from tribal_assistant.core.models.frame import VillageFrame
from tribal_assistant.core.models.village import Village
from tribal_assistant.core.repositories.frames import FrameRepository, LevelDiff
from tribal_assistant.core.services.timelapse import FramePolicy, TimelapseService

JPEG = b"\xff\xd8\xff\xe0fake-jpeg\xff\xd9"


async def village(session: AsyncSession) -> Village:
    row = Village(game_id="777", name="Aldeia", coords="500|500", is_own=True)
    session.add(row)
    await session.commit()
    return row


def frame(village_id: int, hours: int, points: int, levels: dict[str, int]) -> VillageFrame:
    return VillageFrame(
        village_id=village_id,
        taken_at=datetime(2026, 9, 1) + timedelta(hours=hours),
        image=JPEG,
        width=300,
        height=200,
        points=points,
        levels=json.dumps(levels),
    )


def game_village(levels: dict[str, int], points: int = 100) -> GameVillage:
    return GameVillage(
        game_id="777", name="Aldeia", coords="500|500", points=points, wood=0, clay=0, iron=0, storage=0,
        pop_current=0, pop_max=0, wood_prod=0, clay_prod=0, iron_prod=0,
        buildings=tuple(BuildingSnapshot(name=name, level=level) for name, level in levels.items()),
    )


def test_level_diff_lists_only_what_went_up() -> None:
    assert LevelDiff.ups({"main": 9, "wood": 5}, {"main": 10, "wood": 5, "farm": 1}) == [("main", 9, 10), ("farm", 0, 1)]
    assert LevelDiff.gained({"main": 9}, {"main": 11}) == 2
    assert LevelDiff.parse("não é json") == {}


def test_policy_keeps_first_level_up_and_after_interval() -> None:
    policy = FramePolicy(Knobs())
    last = frame(1, 0, 100, {"main": 9})
    start = last.taken_at

    assert policy.due(None, {"main": 9}, start)
    assert policy.due(last, {"main": 10}, start + timedelta(minutes=5))
    assert not policy.due(last, {"main": 9}, start + timedelta(hours=2))
    assert policy.due(last, {"main": 9}, start + timedelta(hours=3))


def test_policy_never_goes_below_the_minimum_interval() -> None:
    policy = FramePolicy(Knobs({"timelapse.interval_hours": 0.01}))

    assert policy.interval == timedelta(hours=0.5)


def test_interval_shrinks_with_many_builds_and_settles_back() -> None:
    busy = {name: value for name, value, _ in Tuner.plan(Knobs(), Metrics(rounds=20, builds_done=5))}
    calm = {name: value for name, value, _ in Tuner.plan(Knobs({"timelapse.interval_hours": 2.0}), Metrics(rounds=20, builds_done=0))}

    assert busy["timelapse.interval_hours"] < 3.0
    assert 2.0 < calm["timelapse.interval_hours"] <= 3.0


async def test_record_keeps_a_frame_only_when_due(session: AsyncSession) -> None:
    row = await village(session)
    service = TimelapseService(session)
    shots = {"777": Shot(JPEG, 300, 200)}

    assert await service.record([game_village({"main": 1})], shots, Knobs()) == 1
    assert await service.record([game_village({"main": 1})], shots, Knobs()) == 0
    assert await service.record([game_village({"main": 2})], shots, Knobs()) == 1
    assert await service.record([game_village({"main": 3})], {}, Knobs()) == 0

    frames = await service.frames(row.id)
    assert [f.levels for f in frames] == [{"main": 1}, {"main": 2}]


async def test_most_levels_gained_counts_level_ups_per_village(session: AsyncSession) -> None:
    row = await village(session)
    for hours, levels in ((0, {"main": 1}), (1, {"main": 2, "wood": 1}), (2, {"main": 3, "wood": 2})):
        session.add(frame(row.id, hours, 100, levels))
    await session.commit()

    assert await FrameRepository(session).most_levels_gained(datetime(2026, 9, 1)) == 4
    assert (await KnobStore(session).metrics()).builds_done == 0.0


async def test_frames_route_lists_with_diff_and_serves_the_jpeg(client: AsyncClient, session: AsyncSession, monkeypatch) -> None:
    monkeypatch.setattr(settings, "play", False)
    row = await village(session)
    session.add(frame(row.id, 0, 100, {"main": 9, "wood": 3}))
    session.add(frame(row.id, 4, 130, {"main": 10, "wood": 3}))
    await session.commit()

    r = await client.get(f"/api/v1/villages/{row.id}/frames")
    items = r.json()

    assert r.status_code == 200
    assert "image" not in items[0]
    assert items[0]["diff"] == [] and items[0]["points_gained"] == 0
    assert items[1]["diff"] == [{"name": "main", "label": "Edifício principal", "before": 9, "after": 10}]
    assert items[1]["points_gained"] == 30

    image = await client.get(f"/api/v1/frames/{items[1]['id']}.jpg")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    assert "max-age=31536000" in image.headers["cache-control"]
    assert image.content == JPEG


async def test_frames_route_is_empty_and_missing_image_is_404(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/villages/42/frames")).json() == []
    assert (await client.get("/api/v1/frames/42.jpg")).status_code == 404
