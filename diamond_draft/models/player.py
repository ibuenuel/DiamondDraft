from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(eq=False)
class Player(ABC):
    """Abstract base for all MLB fantasy players."""

    name: str
    mlb_team: str
    position: str
    stats: dict[str, float] = field(default_factory=dict)
    mlb_id: int | None = None
    weekly_factor: float = field(default=1.0)
    injured_weeks_remaining: int = field(default=0)

    @property
    def player_id(self) -> str:
        return f"{self.name}_{self.mlb_team}_{self.position}".replace(" ", "_")

    @abstractmethod
    def calculate_fantasy_points(self) -> float: ...

    def to_dict(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "mlb_team": self.mlb_team,
            "position": self.position,
            "stats": self.stats,
            "mlb_id": self.mlb_id,
            "weekly_factor": self.weekly_factor,
            "injured_weeks_remaining": self.injured_weeks_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Player:
        player_cls = Batter if data["type"] == "Batter" else Pitcher
        player = player_cls(
            name=data["name"],
            mlb_team=data["mlb_team"],
            position=data["position"],
            stats=data["stats"],
            mlb_id=data.get("mlb_id"),
        )
        player.weekly_factor = data.get("weekly_factor", 1.0)
        player.injured_weeks_remaining = data.get("injured_weeks_remaining", 0)
        return player

    def __str__(self) -> str:
        return f"{self.name} ({self.position}, {self.mlb_team})"

    def __hash__(self) -> int:
        return hash(self.player_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            return NotImplemented
        return self.player_id == other.player_id


@dataclass(eq=False)
class Batter(Player):
    """A position player (non-pitcher)."""

    POSITIONS: ClassVar[frozenset[str]] = frozenset(
        {"C", "1B", "2B", "3B", "SS", "OF", "DH"}
    )

    def calculate_fantasy_points(self) -> float:
        from diamond_draft.engine.score_engine import ScoreEngine

        return ScoreEngine.score(self)


@dataclass(eq=False)
class Pitcher(Player):
    """A starting or relief pitcher."""

    POSITIONS: ClassVar[frozenset[str]] = frozenset({"SP", "RP"})

    def calculate_fantasy_points(self) -> float:
        from diamond_draft.engine.score_engine import ScoreEngine

        return ScoreEngine.score(self)
