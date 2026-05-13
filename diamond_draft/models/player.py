"""Player domain model: abstract base class and concrete Batter / Pitcher types.

The module also exports the ``Position`` enum, which provides type-safe
constants for all valid MLB fantasy roster positions. Using ``StrEnum``
ensures that every ``Position`` member compares equal to its raw string
value, preserving backward compatibility with JSON saves and dict lookups
that use plain strings.

Class hierarchy::

    Player (ABC, dataclass)
    ├── Batter   — position players (C, 1B, 2B, 3B, SS, OF, DH)
    └── Pitcher  — starting and relief pitchers (SP, RP)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar


class Position(StrEnum):
    """Valid MLB fantasy roster positions.

    Inherits from ``StrEnum`` so that members compare equal to their string
    values (e.g. ``Position.CATCHER == "C"`` is ``True``). This preserves
    full backward compatibility with save files and any existing dict-based
    position lookups throughout the codebase.
    """

    CATCHER           = "C"
    FIRST_BASE        = "1B"
    SECOND_BASE       = "2B"
    THIRD_BASE        = "3B"
    SHORTSTOP         = "SS"
    OUTFIELD          = "OF"
    DESIGNATED_HITTER = "DH"
    STARTING_PITCHER  = "SP"
    RELIEF_PITCHER    = "RP"
    BENCH             = "BENCH"


@dataclass(eq=False)
class Player(ABC):
    """Abstract base class for all MLB fantasy players.

    Defines the shared interface and serialisation contract for every player
    type in the application. Concrete subclasses (``Batter``, ``Pitcher``)
    must implement ``calculate_fantasy_points`` and register themselves with
    the player registry so that ``from_dict`` can reconstruct them from save
    files without a hard-coded conditional.

    Attributes:
        name: Full player name as returned by the MLB Stats API.
        mlb_team: Full franchise name (e.g. ``"New York Yankees"``).
        position: Canonical position code (see ``Position``).
        stats: Season statistics keyed by stat abbreviation
            (e.g. ``{"HR": 30, "RBI": 90}``).
        mlb_id: Numeric MLB person ID used for headshot / logo lookups.
            May be ``None`` for sample-data players.
        weekly_factor: Performance multiplier applied by ``ScoreEngine.score``
            each week. Set to ``0.0`` when the player is injured.
        injured_weeks_remaining: Number of weeks until the player recovers.
            ``0`` means healthy.
    """

    name: str
    mlb_team: str
    position: str
    stats: dict[str, float] = field(default_factory=dict)
    mlb_id: int | None = None
    weekly_factor: float = field(default=1.0)
    injured_weeks_remaining: int = field(default=0)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def player_id(self) -> str:
        """Return a stable, human-readable unique identifier for this player.

        The ID is derived from name, team, and position so that it survives
        round-trips through JSON without needing a database-style integer key.

        Returns:
            A string of the form ``"<Name>_<Team>_<Position>"`` with spaces
            replaced by underscores.
        """
        return f"{self.name}_{self.mlb_team}_{self.position}".replace(" ", "_")

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def calculate_fantasy_points(self) -> float:
        """Calculate and return the current fantasy point score for this player.

        Implementations must delegate to ``ScoreEngine.score(self)`` and apply
        the player's ``weekly_factor`` so that injured players contribute 0 pts.

        Returns:
            Fantasy points as a non-negative float.
        """
        ...

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise this player to a JSON-compatible dictionary.

        The ``"type"`` key stores the concrete class name and is used by
        ``from_dict`` (via the player registry) to reconstruct the correct
        subclass.

        Returns:
            A plain dict containing all fields needed to fully restore this
            player via ``from_dict``.
        """
        return {
            "type":                     self.__class__.__name__,
            "name":                     self.name,
            "mlb_team":                 self.mlb_team,
            "position":                 self.position,
            "stats":                    self.stats,
            "mlb_id":                   self.mlb_id,
            "weekly_factor":            self.weekly_factor,
            "injured_weeks_remaining":  self.injured_weeks_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Player:
        """Reconstruct a Player subclass instance from a serialised dictionary.

        Uses the player registry to resolve the concrete class, so new player
        types can be added without modifying this method (Open/Closed Principle).

        Args:
            data: A dict previously produced by ``to_dict``. Must contain at
                least the keys ``"type"``, ``"name"``, ``"mlb_team"``,
                ``"position"``, and ``"stats"``.

        Returns:
            A fully initialised ``Batter`` or ``Pitcher`` instance (or any
            other registered subclass) with ``weekly_factor`` and
            ``injured_weeks_remaining`` restored from the save data.

        Raises:
            KeyError: If ``data["type"]`` does not match any registered player
                type. This indicates a corrupted or forward-incompatible save.
        """
        from diamond_draft.models.player_registry import resolve

        player_cls = resolve(data["type"])
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

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.name} ({self.position}, {self.mlb_team})"

    def __hash__(self) -> int:
        return hash(self.player_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            return NotImplemented
        return self.player_id == other.player_id


# ---------------------------------------------------------------------------
# Concrete player types
# ---------------------------------------------------------------------------

from diamond_draft.models.player_registry import register  # noqa: E402


@register("Batter")
@dataclass(eq=False)
class Batter(Player):
    """A non-pitcher position player.

    Eligible positions are the seven standard fantasy batting slots. Scoring
    is delegated entirely to ``ScoreEngine`` to keep the model free of
    business logic.
    """

    POSITIONS: ClassVar[frozenset[str]] = frozenset({
        Position.CATCHER,
        Position.FIRST_BASE,
        Position.SECOND_BASE,
        Position.THIRD_BASE,
        Position.SHORTSTOP,
        Position.OUTFIELD,
        Position.DESIGNATED_HITTER,
    })

    def calculate_fantasy_points(self) -> float:
        """Delegate batting score calculation to ScoreEngine.

        Returns:
            Fantasy points for this batter's season stats scaled by
            ``weekly_factor`` (0.0 when injured).
        """
        from diamond_draft.engine.score_engine import ScoreEngine

        return ScoreEngine.score(self)


@register("Pitcher")
@dataclass(eq=False)
class Pitcher(Player):
    """A starting or relief pitcher.

    Scoring uses pitching-specific weights defined in ``ScoreEngine``,
    including an ERA bonus for pitchers with an ERA below the threshold.
    """

    POSITIONS: ClassVar[frozenset[str]] = frozenset({
        Position.STARTING_PITCHER,
        Position.RELIEF_PITCHER,
    })

    def calculate_fantasy_points(self) -> float:
        """Delegate pitching score calculation to ScoreEngine.

        Returns:
            Fantasy points for this pitcher's season stats scaled by
            ``weekly_factor`` (0.0 when injured).
        """
        from diamond_draft.engine.score_engine import ScoreEngine

        return ScoreEngine.score(self)
