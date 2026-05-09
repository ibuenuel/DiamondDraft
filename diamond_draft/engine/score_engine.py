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

    VARIANCE_MIN: float = 0.7
    VARIANCE_MAX: float = 1.3

    @staticmethod
    def score(player: Player) -> float:
        """Return fantasy points for a player, scaled by their weekly_factor."""
        from diamond_draft.models.player import Batter, Pitcher

        if isinstance(player, Batter):
            return ScoreEngine._score_batter(player) * player.weekly_factor
        if isinstance(player, Pitcher):
            return ScoreEngine._score_pitcher(player) * player.weekly_factor
        raise TypeError(f"Unknown player type: {type(player)}")

    @staticmethod
    def _weighted_sum(stats: dict[str, float], weights: dict[str, float]) -> float:
        return sum(stats.get(stat, 0.0) * weight for stat, weight in weights.items())

    @staticmethod
    def _score_batter(player: Batter) -> float:
        return ScoreEngine._weighted_sum(player.stats, ScoreEngine.BATTING_WEIGHTS)

    @staticmethod
    def _score_pitcher(player: Pitcher) -> float:
        base = ScoreEngine._weighted_sum(player.stats, ScoreEngine.PITCHING_WEIGHTS)
        era = player.stats.get("ERA", 99.0)
        bonus = ScoreEngine.ERA_BONUS if era < ScoreEngine.ERA_BONUS_THRESHOLD else 0.0
        return base + bonus
