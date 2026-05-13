"""Team domain model for Diamond Draft.

A ``Team`` holds a roster of up to ``MAX_ROSTER_SIZE`` (14) players and
tracks which 11 are in the active lineup for a given week. Eleven scoring
slots are defined by ``SLOT_REQUIREMENTS``; the remaining three spots are
bench slots that contribute no points but allow roster flexibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from diamond_draft.models.player import Batter, Pitcher, Player


@dataclass
class Team:
    """A fantasy team with a 14-player roster; 11 score each week.

    Roster constraints are enforced via ``SLOT_REQUIREMENTS``. The active
    lineup is a list of exactly ``ACTIVE_SIZE`` players; bench players do not
    contribute points. When ``active_lineup`` is not yet populated,
    ``active_players`` falls back to selecting the top scorers automatically.

    Attributes:
        name: Display name for the team (human-chosen or CPU default).
        is_human: ``True`` for the single human-controlled team.
        roster: All players on this team (active + bench).
        active_lineup: The current 11-player active lineup. Set by the
            user via ``LineupScreen`` or auto-selected by ``SeasonSimulator``
            for CPU teams.
        wins: Number of weekly matchups won this season.
        losses: Number of weekly matchups lost this season.
    """

    SLOT_REQUIREMENTS: ClassVar[dict[str, int]] = {
        "SP": 2,
        "C":  1,
        "1B": 1,
        "2B": 1,
        "3B": 1,
        "SS": 1,
        "OF": 3,
        "DH": 1,
    }
    """Required number of players per position in the active lineup."""

    ACTIVE_SIZE: ClassVar[int] = sum(SLOT_REQUIREMENTS.values())   # 11
    """Total number of scoring players per week (sum of all slot requirements)."""

    BENCH_SPOTS: ClassVar[int] = 3
    """Number of non-scoring bench slots available per team."""

    MAX_ROSTER_SIZE: ClassVar[int] = ACTIVE_SIZE + BENCH_SPOTS     # 14
    """Maximum total roster size (active + bench)."""

    name:          str
    is_human:      bool          = False
    roster:        list[Player]  = field(default_factory=list)
    active_lineup: list[Player]  = field(default_factory=list)
    wins:          int           = 0
    losses:        int           = 0

    # ------------------------------------------------------------------
    # Roster management
    # ------------------------------------------------------------------

    def add_player(self, player: Player) -> None:
        """Add *player* to the roster.

        Args:
            player: The player to add.

        Raises:
            ValueError: If the roster is already at ``MAX_ROSTER_SIZE``.
        """
        if self.is_full():
            raise ValueError(
                f"{self.name} roster is already full ({self.MAX_ROSTER_SIZE} players)."
            )
        self.roster.append(player)

    def is_full(self) -> bool:
        """Return ``True`` when the roster has reached ``MAX_ROSTER_SIZE``.

        Returns:
            ``True`` if no more players can be added.
        """
        return len(self.roster) >= self.MAX_ROSTER_SIZE

    def open_slots(self) -> dict[str, int]:
        """Return a mapping of positions to their remaining open slot count.

        Includes bench spots as the ``"BENCH"`` key once all active slots are
        filled, so callers can determine whether a player of any position can
        still be added to the roster.

        Returns:
            Dict of ``{position: remaining_count}`` for every position with at
            least one open slot. Empty when the roster is full.
        """
        filled: dict[str, int] = {}
        for player in self.roster:
            filled[player.position] = filled.get(player.position, 0) + 1

        slots = {
            pos: required - filled.get(pos, 0)
            for pos, required in self.SLOT_REQUIREMENTS.items()
            if required - filled.get(pos, 0) > 0
        }
        bench_used      = max(0, len(self.roster) - self.ACTIVE_SIZE)
        bench_remaining = self.BENCH_SPOTS - bench_used
        if bench_remaining > 0:
            slots["BENCH"] = bench_remaining
        return slots

    def needs_position(self, position: str) -> bool:
        """Return ``True`` when the team can accept a player at *position*.

        A player is acceptable either when there is a matching open position
        slot OR when there is at least one bench spot available.

        Args:
            position: The position code to check (e.g. ``"OF"``, ``"SP"``).

        Returns:
            ``True`` if the player can be added to the roster.
        """
        slots = self.open_slots()
        return slots.get(position, 0) > 0 or slots.get("BENCH", 0) > 0

    # ------------------------------------------------------------------
    # Lineup access
    # ------------------------------------------------------------------

    def active_players(self) -> list[Player]:
        """Return the ``ACTIVE_SIZE`` scoring players for the current week.

        When ``active_lineup`` is not yet populated (e.g. before the first
        week has been simulated), auto-selects the highest-scoring players.
        This ensures CPU teams always have a valid active lineup even if
        ``SeasonSimulator._WeeklyFactorApplier.set_cpu_lineups`` has not run.

        Returns:
            List of exactly ``ACTIVE_SIZE`` players.
        """
        from diamond_draft.engine.score_engine import ScoreEngine

        if len(self.active_lineup) == self.ACTIVE_SIZE:
            return list(self.active_lineup)
        return sorted(self.roster, key=ScoreEngine.score, reverse=True)[: self.ACTIVE_SIZE]

    def bench_players(self) -> list[Player]:
        """Return the players not in the active lineup.

        Returns:
            List of players on the bench (may be empty if all players fit
            in the active lineup).
        """
        active = self.active_players()
        return [p for p in self.roster if p not in active]

    def total_points(self) -> float:
        """Calculate and return this week's total fantasy points for the team.

        Sums ``ScoreEngine.score`` for each active player. Injured players
        contribute 0 points because their ``weekly_factor`` is 0.0.

        Returns:
            Total fantasy points as a non-negative float.
        """
        from diamond_draft.engine.score_engine import ScoreEngine

        return sum(ScoreEngine.score(p) for p in self.active_players())

    def record_str(self) -> str:
        """Return the win-loss record as a formatted string.

        Returns:
            A string of the form ``"<wins>-<losses>"``.
        """
        return f"{self.wins}-{self.losses}"

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise this team to a JSON-compatible dictionary.

        Returns:
            A plain dict containing all fields needed to fully restore
            this team via ``from_dict``.
        """
        return {
            "name":          self.name,
            "is_human":      self.is_human,
            "roster":        [p.to_dict() for p in self.roster],
            "active_lineup": [p.name for p in self.active_lineup],
            "wins":          self.wins,
            "losses":        self.losses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Team:
        """Reconstruct a ``Team`` from a serialised dictionary.

        Active lineup is restored by matching player names, which preserves
        the user's lineup choices across save/load cycles.

        Args:
            data: A dict previously produced by ``to_dict``.

        Returns:
            A fully initialised ``Team`` instance.
        """
        team         = cls(name=data["name"], is_human=data["is_human"])
        team.roster  = [Player.from_dict(p) for p in data["roster"]]
        team.wins    = data["wins"]
        team.losses  = data["losses"]
        active_names: list[str] = data.get("active_lineup", [])
        team.active_lineup = [p for p in team.roster if p.name in active_names]
        return team

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.name} ({self.record_str()})"
