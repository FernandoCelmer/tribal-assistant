"""Quest popup parsing: HTML in, dataclasses out (no browser, no side effects)."""

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

PROGRESS_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


@dataclass
class QuestGoal:
    title: str
    text: str
    current: int | None = None
    target: int | None = None

    @property
    def done(self) -> bool:
        return self.target is not None and self.current is not None and self.current >= self.target


@dataclass
class Quest:
    quest_id: str
    line_id: str
    title: str
    state: str
    description: str = ""
    goals: list[QuestGoal] = field(default_factory=list)
    can_complete: bool = False


@dataclass
class QuestReward:
    reward_id: str
    label: str


def _state(li: Tag) -> str:
    for cls in li.get("class") or []:
        if cls.startswith("quest-state-"):
            return cls.removeprefix("quest-state-")
    return "unknown"


def parse_quest_list(html: str) -> list[Quest]:
    """Quest lines in the left bar: id, line, title and state (new, progress, finished)."""
    soup = BeautifulSoup(html, "lxml")
    quests = []
    for li in soup.select(".questline-list li.quest-state"):
        link = li.select_one("a.quest-link")
        if link is None or not link.get("data-quest-id"):
            continue
        quests.append(
            Quest(
                quest_id=str(link["data-quest-id"]),
                line_id=str(link.get("data-questline-id", "")),
                title=li.get_text(" ", strip=True),
                state=_state(li),
            )
        )
    return quests


def parse_quest_body(html: str) -> tuple[str, list[QuestGoal], bool]:
    """Description, goals and whether "Missão completa" is offered for the open quest."""
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one("#main-tab .quest-body") or soup.select_one(".quest-body")
    if body is None:
        return "", [], False
    description = body.select_one(".quest-description")
    goals = []
    for goal in body.select(".goal"):
        title = goal.select_one("h5")
        text = goal.select_one("p")
        label = goal.select_one(".progress-bar > .label") or goal.select_one(".progress-bar .label")
        current = target = None
        if label and (match := PROGRESS_RE.search(label.get_text())):
            current, target = int(match.group(1)), int(match.group(2))
        goals.append(
            QuestGoal(
                title=title.get_text(strip=True) if title else "",
                text=text.get_text(strip=True) if text else "",
                current=current,
                target=target,
            )
        )
    complete = body.select_one(".status-btn")
    can_complete = complete is not None and "hidden" not in (complete.get("class") or [])
    return (description.get_text(" ", strip=True) if description else ""), goals, can_complete


def parse_rewards(html: str) -> list[QuestReward]:
    """Claimable rewards in the "Recompensas" tab."""
    soup = BeautifulSoup(html, "lxml")
    rewards = []
    for button in soup.select(".reward-system-claim-button[data-reward-id]"):
        row = button.find_parent("tr")
        label = row.get_text(" ", strip=True) if row else ""
        rewards.append(QuestReward(reward_id=str(button["data-reward-id"]), label=label.replace("Reivindicar", "").strip()))
    return rewards
