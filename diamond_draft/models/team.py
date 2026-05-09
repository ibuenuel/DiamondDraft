from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from diamond_draft.models.player import Batter, Pitcher, Player


@dataclass
class Team:
    """A fantasy team with a roster of up to 14 players; 11 score each week."""

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
    ACTIVE_SIZE: ClassVar[int] = sum(SLOT_REQUIREMENTS.values())  # 11
    BENCH_SPOTS: ClassVar[int] = 3
    MAX_ROSTER_SIZE: ClassVar[int] = ACTIVE_SIZE + BENCH_SPOTS  # 14

    name: str
    is_human: bool = False
    roster: list[Player] = field(default_factory=list)
    active_lineup: list[Player] = field(default_factory=list)
    wins: int = 0
    losses: int = 0

    def add_player(self, player: Player) -> None:
        if self.is_full():
            raise ValueError(f"{self.name} roster is already full ({self.MAX_ROSTER_SIZE} players).")
        self.roster.append(player)

    def is_full(self) -> bool:
        return len(self.roster) >= self.MAX_ROSTER_SIZE

    def open_slots(self) -> dict[str, int]:
        """Returns remaining slots by position, including bench spots."""
        filled: dict[str, int] = {}
        for player in self.roster:
            filled[player.position] = filled.get(player.position, 0) + 1
        slots = {
            pos: required - filled.get(pos, 0)
            for pos, required in self.SLOT_REQUIREMENTS.items()
            if required - filled.get(pos, 0) > 0
        }
        bench_used = max(0, len(self.roster) - self.ACTIVE_SIZE)
        bench_remaining = self.BENCH_SPOTS - bench_used
        if bench_remaining > 0:
            slots["BENCH"] = bench_remaining
        return slots

    def needs_position(self, position: str) -> bool:
        slots = self.open_slots()
        return slots.get(position, 0) > 0 or slots.get("BENCH", 0) > 0

    def active_players(self) -> list[Player]:
        """Returns the 11 active players. Auto-selects top scorers if not set."""
        from diamond_draft.engine.score_engine import ScoreEngine

        if len(self.active_lineup) == self.ACTIVE_SIZE:
            return list(self.active_lineup)
        return sorted(self.roster, key=ScoreEngine.score, reverse=True)[: self.ACTIVE_SIZE]

    def bench_players(self) -> list[Player]:
        active = self.active_players()
        return [p for p in self.roster if p not in active]

    def total_points(self) -> float:
        from diamond_draft.engine.score_engine import ScoreEngine

        return sum(ScoreEngine.score(p) for p in self.active_players())

    def record_str(self) -> str:
        return f"{self.wins}-{self.losses}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "is_human": self.is_human,
            "roster": [p.to_dict() for p in self.roster],
            "active_lineup": [p.name for p in self.active_lineup],
            "wins": self.wins,
            "losses": self.losses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Team:
        team = cls(name=data["name"], is_human=data["is_human"])
        team.roster = [Player.from_dict(p) for p in data["roster"]]
        team.wins = data["wins"]
        team.losses = data["losses"]
        active_names: list[str] = data.get("active_lineup", [])
        team.active_lineup = [p for p in team.roster if p.name in active_names]
        return team

    def __str__(self) -> str:
        return f"{self.name} ({self.record_str()})"
