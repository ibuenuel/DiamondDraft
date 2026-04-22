from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diamond_draft.models.player import Batter, Pitcher, Player


class ScoreEngine:
    """
    Stateless fantasy point calculator.

    All scoring constants live here — the single source of truth for the
    entire application. Neither Player nor Team duplicates any scoring logic.
    """

    # Batting: stat_key -> points per unit
    BATTING_WEIGHTS: dict[str, float] = {
        "HR": 4.0,
        "RBI": 1.0,
        "R": 1.0,
        "SB": 2.0,
        "H": 1.0,
        "SO": -1.0,
    }

    # Pitching: stat_key -> points per unit
    PITCHING_WEIGHTS: dict[str, float] = {
        "W": 4.0,
        "SO": 1.0,
        "IP": 1.0,
        "SV": 4.0,
        "L": -4.0,
    }

    ERA_BONUS_THRESHOLD: float = 3.00
    ERA_BONUS: float = 2.0

    @staticmethod
    def score(player: Player) -> float:
        """Return fantasy points for a player based on their season stats."""
        from diamond_draft.models.player import Batter, Pitcher

        if isinstance(player, Batter):
            return ScoreEngine._score_batter(player)
        if isinstance(player, Pitcher):
            return ScoreEngine._score_pitcher(player)
        raise TypeError(f"Unknown player type: {type(player)}")

    @staticmethod
    def _score_batter(player: Batter) -> float:
        return sum(
            player.stats.get(stat, 0.0) * weight
            for stat, weight in ScoreEngine.BATTING_WEIGHTS.items()
        )

    @staticmethod
    def _score_pitcher(player: Pitcher) -> float:
        base = sum(
            player.stats.get(stat, 0.0) * weight
            for stat, weight in ScoreEngine.PITCHING_WEIGHTS.items()
        )
        era = player.stats.get("ERA", 99.0)
        bonus = ScoreEngine.ERA_BONUS if era < ScoreEngine.ERA_BONUS_THRESHOLD else 0.0
        return base + bonus
