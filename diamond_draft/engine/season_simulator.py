from __future__ import annotations

import random

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.league import League
from diamond_draft.models.matchup import Matchup


class SeasonSimulator:
    """
    Drives the week-by-week season loop.

    Responsibilities:
    - Simulate a single week (run matchups, update standings)
    - Simulate all remaining weeks at once
    - Track the current week number

    SeasonSimulator owns the loop; League owns the schedule and standings.
    ScoreEngine is injected so it can be swapped in tests.
    """

    INJURY_CHANCE: float = 0.08
    INJURY_MIN_WEEKS: int = 1
    INJURY_MAX_WEEKS: int = 2

    def __init__(
        self,
        league: League,
        score_engine: type[ScoreEngine] = ScoreEngine,
    ) -> None:
        self._league = league
        self._score_engine = score_engine
        self.current_week: int = 0  # 0 = draft not yet played; 1-10 = week index
        self.injury_report: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_weeks(self) -> int:
        return League.WEEKS

    @property
    def is_complete(self) -> bool:
        return self.current_week >= League.WEEKS

    @property
    def weeks_remaining(self) -> int:
        return max(0, League.WEEKS - self.current_week)

    def simulate_week(self) -> list[Matchup]:
        """
        Simulate the next week and update standings.
        Returns the played matchups so the GUI can display results.
        """
        if self.is_complete:
            raise RuntimeError("Season is already complete — all 10 weeks have been played.")

        self.current_week += 1
        self._apply_weekly_factors()
        self._set_cpu_lineups()

        week_matchups = self._league.schedule[self.current_week - 1]

        for matchup in week_matchups:
            self._league.update_standings(matchup)

        return week_matchups

    def _set_cpu_lineups(self) -> None:
        """Auto-select the best active lineup for every CPU team."""
        from diamond_draft.models.team import Team

        for team in self._league.teams:
            if not team.is_human:
                team.active_lineup = sorted(
                    team.roster,
                    key=self._score_engine.score,
                    reverse=True,
                )[: Team.ACTIVE_SIZE]

    def _apply_weekly_factors(self) -> None:
        """Randomise each player's weekly_factor and apply injury logic."""
        self.injury_report = []
        for team in self._league.teams:
            for player in team.roster:
                if player.injured_weeks_remaining > 0:
                    player.injured_weeks_remaining -= 1
                    player.weekly_factor = 0.0
                elif random.random() < self.INJURY_CHANCE:
                    player.injured_weeks_remaining = random.randint(
                        self.INJURY_MIN_WEEKS, self.INJURY_MAX_WEEKS
                    )
                    player.weekly_factor = 0.0
                    self.injury_report.append(
                        f"{player.name} ({team.name}) — out {player.injured_weeks_remaining} week(s)"
                    )
                else:
                    player.weekly_factor = random.uniform(
                        self._score_engine.VARIANCE_MIN,
                        self._score_engine.VARIANCE_MAX,
                    )

    def simulate_all(self) -> list[list[Matchup]]:
        """Simulate all remaining weeks and return results grouped by week."""
        results: list[list[Matchup]] = []
        while not self.is_complete:
            results.append(self.simulate_week())
        return results

    # ------------------------------------------------------------------
    # Serialization support
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"current_week": self.current_week}

    def restore_week(self, week: int) -> None:
        """Restore simulator state from a saved game (used by SaveManager)."""
        if not (0 <= week <= League.WEEKS):
            raise ValueError(f"Invalid week {week}; must be 0–{League.WEEKS}.")
        self.current_week = week
