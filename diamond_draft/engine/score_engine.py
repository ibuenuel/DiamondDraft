"""Fantasy point calculation engine for Diamond Draft.

ScoreEngine is the single source of truth for all scoring rules. It is
intentionally stateless — every attribute is a class-level constant and
every method is a static method — so it can be imported and called from
anywhere without instantiation or side effects.

Design notes:
    - Weights are ClassVars so they can be injected / monkey-patched in
      unit tests without creating a subclass.
    - The ``score`` entry point dispatches by player type; callers never
      need to know whether a player is a Batter or Pitcher.
    - ``VARIANCE_MIN`` / ``VARIANCE_MAX`` and stat labels are sourced from
      ``config`` so that all tuneable values live in one place.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from diamond_draft import config

if TYPE_CHECKING:
    from diamond_draft.models.player import Batter, Pitcher, Player


class ScoreEngine:
    """Stateless fantasy point calculator.

    All scoring constants are defined here as ``ClassVar`` attributes.
    Neither ``Player`` nor ``Team`` duplicates any scoring logic — they
    call ``ScoreEngine.score`` and receive a float back.

    Attributes:
        BATTING_WEIGHTS: Points awarded per unit of each batting stat.
        PITCHING_WEIGHTS: Points awarded per unit of each pitching stat.
        ERA_BONUS_THRESHOLD: ERA below which a pitcher earns the ERA bonus.
        ERA_BONUS: Flat bonus added to a pitcher's score when ERA qualifies.
        VARIANCE_MIN: Lower bound of the random weekly performance multiplier.
        VARIANCE_MAX: Upper bound of the random weekly performance multiplier.
        BATTING_STAT_LABELS: Human-readable label for each batting stat key.
        PITCHING_STAT_LABELS: Human-readable label for each pitching stat key.
    """

    # Batting: stat key → points per unit
    BATTING_WEIGHTS: ClassVar[dict[str, float]] = {
        "HR":  4.0,
        "RBI": 1.0,
        "R":   1.0,
        "SB":  2.0,
        "H":   1.0,
        "SO": -1.0,
    }

    # Pitching: stat key → points per unit
    PITCHING_WEIGHTS: ClassVar[dict[str, float]] = {
        "W":   4.0,
        "SO":  1.0,
        "IP":  1.0,
        "SV":  4.0,
        "L":  -4.0,
    }

    ERA_BONUS_THRESHOLD: ClassVar[float] = 3.00
    """ERA value below which a pitcher earns a flat bonus."""

    ERA_BONUS: ClassVar[float] = 2.0
    """Flat point bonus awarded to pitchers whose ERA is below the threshold."""

    # Sourced from config so all tuneable values live in one place.
    VARIANCE_MIN: ClassVar[float] = config.VARIANCE_MIN
    VARIANCE_MAX: ClassVar[float] = config.VARIANCE_MAX

    # Stat display labels — used by PlayerDetailDialog and HelpDialog.
    BATTING_STAT_LABELS: ClassVar[dict[str, str]] = config.BATTING_STAT_LABELS
    PITCHING_STAT_LABELS: ClassVar[dict[str, str]] = config.PITCHING_STAT_LABELS

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @staticmethod
    def score(player: Player) -> float:
        """Return fantasy points for *player* scaled by their weekly factor.

        Dispatches to the appropriate private scorer based on the player's
        concrete type and multiplies the raw score by ``player.weekly_factor``
        so that injured players (factor == 0.0) always contribute zero points.

        Args:
            player: Any ``Player`` subclass instance. Must be either a
                ``Batter`` or a ``Pitcher``.

        Returns:
            Non-negative float representing this player's fantasy point
            contribution for the current week.

        Raises:
            TypeError: If *player* is not a recognised subclass.
        """
        from diamond_draft.models.player import Batter, Pitcher

        if isinstance(player, Batter):
            return ScoreEngine._score_batter(player) * player.weekly_factor
        if isinstance(player, Pitcher):
            return ScoreEngine._score_pitcher(player) * player.weekly_factor
        raise TypeError(
            f"ScoreEngine received an unknown player type: {type(player).__name__}"
        )

    # ------------------------------------------------------------------
    # Private scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _weighted_sum(stats: dict[str, float], weights: dict[str, float]) -> float:
        """Compute the dot product of *stats* values and *weights* values.

        Stats keys absent from *stats* are treated as zero, which is correct
        for players who did not accumulate any of that statistic.

        Args:
            stats: Player season stats keyed by abbreviation.
            weights: Points-per-unit mapping for a specific player type.

        Returns:
            Sum of ``stats[key] * weights[key]`` for all keys in *weights*.
        """
        return sum(stats.get(stat, 0.0) * weight for stat, weight in weights.items())

    @staticmethod
    def _score_batter(player: Batter) -> float:
        """Compute raw (pre-factor) fantasy points for a position player.

        Args:
            player: A ``Batter`` instance with populated ``stats``.

        Returns:
            Raw batting fantasy points before the weekly factor is applied.
        """
        return ScoreEngine._weighted_sum(player.stats, ScoreEngine.BATTING_WEIGHTS)

    @staticmethod
    def _score_pitcher(player: Pitcher) -> float:
        """Compute raw (pre-factor) fantasy points for a pitcher.

        Applies the ERA bonus when the pitcher's ERA is below the threshold.
        A missing ERA stat is treated as 99.0, which never qualifies for the
        bonus — this prevents newly-added players from receiving unearned pts.

        Args:
            player: A ``Pitcher`` instance with populated ``stats``.

        Returns:
            Raw pitching fantasy points before the weekly factor is applied.
        """
        base  = ScoreEngine._weighted_sum(player.stats, ScoreEngine.PITCHING_WEIGHTS)
        era   = player.stats.get("ERA", 99.0)
        bonus = ScoreEngine.ERA_BONUS if era < ScoreEngine.ERA_BONUS_THRESHOLD else 0.0
        return base + bonus
