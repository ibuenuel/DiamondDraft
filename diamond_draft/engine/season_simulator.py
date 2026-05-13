"""Season simulation engine for Diamond Draft.

Drives the week-by-week fantasy season loop. The public API is intentionally
narrow: callers invoke ``simulate_week`` or ``simulate_all`` and receive
``Matchup`` objects back. All internal state mutation (injuries, weekly
factors, CPU lineup selection) is handled by private helpers.

Separation of concerns:
    - ``SeasonSimulator`` — owns the week-sequencing loop and the public API.
    - ``_WeeklyFactorApplier`` — owns player-state mutation (injuries and
      performance variance). Extracted so that the mutation logic can be
      reasoned about and tested in isolation.
"""
from __future__ import annotations

import random
from typing import ClassVar

from diamond_draft import config
from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.league import League
from diamond_draft.models.matchup import Matchup


class _WeeklyFactorApplier:
    """Apply injury and performance-variance mutations before each simulated week.

    Encapsulates the two player-state mutation responsibilities that were
    previously inlined inside ``SeasonSimulator``:

    1. **Injury progression** — decrement ``injured_weeks_remaining`` for
       existing injuries; randomly inflict new injuries; set
       ``weekly_factor = 0.0`` for injured players.
    2. **Performance variance** — assign a random ``weekly_factor`` in
       ``[VARIANCE_MIN, VARIANCE_MAX]`` to healthy players.

    This class is private to the module (``_`` prefix). External code must
    not instantiate it directly.

    Args:
        score_engine: The ``ScoreEngine`` class (or compatible substitute)
            used to rank players when auto-selecting CPU lineups. Injected
            rather than imported directly to support test doubles.
    """

    def __init__(self, score_engine: type[ScoreEngine]) -> None:
        self._score_engine = score_engine

    def apply(self, teams: list) -> list[str]:
        """Mutate weekly state for all players across all teams.

        Processes injury recovery, new injury rolls, and performance-variance
        assignment in a single pass over every roster. Returns a human-readable
        injury report so the UI can notify the user of newly injured players.

        Args:
            teams: All ``Team`` objects in the league (human and CPU alike).

        Returns:
            A list of injury-report strings (one per newly injured player).
            Empty list when no new injuries occurred this week.
        """
        injury_report: list[str] = []

        for team in teams:
            for player in team.roster:
                if player.injured_weeks_remaining > 0:
                    # Player is already injured — advance recovery counter.
                    player.injured_weeks_remaining -= 1
                    player.weekly_factor = 0.0
                elif random.random() < config.INJURY_CHANCE:
                    # Healthy player becomes injured this week.
                    player.injured_weeks_remaining = random.randint(
                        config.INJURY_MIN_WEEKS, config.INJURY_MAX_WEEKS
                    )
                    player.weekly_factor = 0.0
                    injury_report.append(
                        f"{player.name} ({team.name}) "
                        f"— out {player.injured_weeks_remaining} week(s)"
                    )
                else:
                    # Healthy player: assign random performance variance.
                    player.weekly_factor = random.uniform(
                        self._score_engine.VARIANCE_MIN,
                        self._score_engine.VARIANCE_MAX,
                    )

        return injury_report

    def set_cpu_lineups(self, teams: list) -> None:
        """Auto-select the highest-scoring active lineup for each CPU team.

        Ranks all roster players by their projected score and picks the top
        ``ACTIVE_SIZE`` players as the active lineup. Human-controlled teams
        are skipped — the user manages their own lineup via ``LineupScreen``.

        Args:
            teams: All ``Team`` objects in the league.
        """
        from diamond_draft.models.team import Team

        for team in teams:
            if not team.is_human:
                team.active_lineup = sorted(
                    team.roster,
                    key=self._score_engine.score,
                    reverse=True,
                )[: Team.ACTIVE_SIZE]


class SeasonSimulator:
    """Drive the week-by-week fantasy season loop.

    Orchestrates the 10-week season: advancing the week counter, delegating
    player-state mutations to ``_WeeklyFactorApplier``, running each week's
    matchups, and updating league standings. The public API is intentionally
    minimal so that GUI code never needs to know how weeks are simulated.

    ``League`` owns the static schedule and standings; ``SeasonSimulator``
    owns only the current-week cursor and the simulation loop.

    Args:
        league: The ``League`` instance whose schedule will be simulated.
        score_engine: The scoring class to use. Defaults to ``ScoreEngine``.
            Pass a test double here to decouple integration tests from the
            real scoring weights.
    """

    # Class-level constants sourced from config so the single source of
    # truth for all tuneable values is config.py.
    INJURY_CHANCE:    ClassVar[float] = config.INJURY_CHANCE
    INJURY_MIN_WEEKS: ClassVar[int]   = config.INJURY_MIN_WEEKS
    INJURY_MAX_WEEKS: ClassVar[int]   = config.INJURY_MAX_WEEKS

    def __init__(
        self,
        league: League,
        score_engine: type[ScoreEngine] = ScoreEngine,
    ) -> None:
        self._league = league
        self._score_engine = score_engine
        self._applier = _WeeklyFactorApplier(score_engine)

        self.current_week: int = 0
        """Current week index. ``0`` means the draft has not yet been played;
        valid in-season values are ``1`` through ``League.WEEKS``."""

        self.injury_report: list[str] = []
        """Human-readable strings describing players newly injured this week.
        Reset each time ``simulate_week`` is called."""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def total_weeks(self) -> int:
        """Return the total number of regular-season weeks.

        Returns:
            The ``League.WEEKS`` constant (10 for a standard season).
        """
        return League.WEEKS

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when all scheduled weeks have been simulated.

        Returns:
            ``True`` if ``current_week >= total_weeks``, ``False`` otherwise.
        """
        return self.current_week >= League.WEEKS

    @property
    def weeks_remaining(self) -> int:
        """Return the number of weeks left to simulate.

        Returns:
            A non-negative integer; ``0`` when the season is complete.
        """
        return max(0, League.WEEKS - self.current_week)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_week(self) -> list[Matchup]:
        """Simulate the next scheduled week and update league standings.

        Advances the week counter, applies injury and variance mutations,
        auto-sets CPU lineups, runs each matchup in the schedule slot, and
        updates standings. The resulting ``Matchup`` list is returned so the
        GUI can display scores without querying the league again.

        Returns:
            The list of ``Matchup`` objects played this week, with scores
            populated and winners determined.

        Raises:
            RuntimeError: If called when ``is_complete`` is ``True``.
        """
        if self.is_complete:
            raise RuntimeError(
                "Season is already complete — all 10 weeks have been played."
            )

        self.current_week += 1
        self.injury_report = self._applier.apply(self._league.teams)
        self._applier.set_cpu_lineups(self._league.teams)

        week_matchups = self._league.schedule[self.current_week - 1]
        for matchup in week_matchups:
            self._league.update_standings(matchup)

        return week_matchups

    def simulate_all(self) -> list[list[Matchup]]:
        """Simulate all remaining weeks and return results grouped by week.

        Convenience method for fast-forwarding the entire season (e.g. when
        the user clicks "Simulate All"). Calls ``simulate_week`` repeatedly
        until ``is_complete`` is ``True``.

        Returns:
            A list of per-week matchup lists; index 0 is the next week to be
            simulated at the time this method is called.
        """
        results: list[list[Matchup]] = []
        while not self.is_complete:
            results.append(self.simulate_week())
        return results

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the simulator's mutable state to a JSON-compatible dict.

        Only the week cursor is persisted; the injury report is transient and
        is recalculated on the next ``simulate_week`` call.

        Returns:
            A dict with a single ``"current_week"`` key.
        """
        return {"current_week": self.current_week}

    def restore_week(self, week: int) -> None:
        """Restore the week cursor from a saved game.

        Called by ``SaveManager`` immediately after constructing a new
        ``SeasonSimulator`` from a loaded save file.

        Args:
            week: The saved week number. Must be in ``[0, League.WEEKS]``.

        Raises:
            ValueError: If *week* is outside the valid range.
        """
        if not (0 <= week <= League.WEEKS):
            raise ValueError(
                f"Invalid week {week}; must be in range 0–{League.WEEKS}."
            )
        self.current_week = week
