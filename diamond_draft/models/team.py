from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from diamond_draft.models.player import Batter, Pitcher, Player


@dataclass
class Team:
    """A fantasy team with a fixed roster of 11 players."""

    SLOT_REQUIREMENTS: ClassVar[dict[str, int]] = {
        "SP": 2,
        "C": 1,
        "1B": 1,
        "2B": 1,
        "3B": 1,
        "SS": 1,
        "OF": 3,
        "DH": 1,
    }
    MAX_ROSTER_SIZE: ClassVar[int] = sum(SLOT_REQUIREMENTS.values())  # 11

    name: str
    is_human: bool = False
    roster: list[Player] = field(default_factory=list)
    wins: int = 0
    losses: int = 0

    def add_player(self, player: Player) -> None:
        if self.is_full():
            raise ValueError(f"{self.name} roster is already full ({self.MAX_ROSTER_SIZE} players).")
        self.roster.append(player)

    def is_full(self) -> bool:
        return len(self.roster) >= self.MAX_ROSTER_SIZE

    def open_slots(self) -> dict[str, int]:
        """Returns remaining slots by position."""
        filled: dict[str, int] = {}
        for player in self.roster:
            filled[player.position] = filled.get(player.position, 0) + 1
        return {
            pos: required - filled.get(pos, 0)
            for pos, required in self.SLOT_REQUIREMENTS.items()
            if required - filled.get(pos, 0) > 0
        }

    def needs_position(self, position: str) -> bool:
        return self.open_slots().get(position, 0) > 0

    def total_points(self) -> float:
        from diamond_draft.engine.score_engine import ScoreEngine

        return sum(ScoreEngine.score(p) for p in self.roster)

    def record_str(self) -> str:
        return f"{self.wins}-{self.losses}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "is_human": self.is_human,
            "roster": [p.to_dict() for p in self.roster],
            "wins": self.wins,
            "losses": self.losses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Team:
        team = cls(name=data["name"], is_human=data["is_human"])
        team.roster = [Player.from_dict(p) for p in data["roster"]]
        team.wins = data["wins"]
        team.losses = data["losses"]
        return team

    def __str__(self) -> str:
        return f"{self.name} ({self.record_str()})"
