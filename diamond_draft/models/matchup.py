"""Matchup domain model for Diamond Draft.

A ``Matchup`` represents a single weekly head-to-head contest between a home
team and an away team. Scores are computed on demand (not stored) so that
lineup changes made before ``simulate_week`` is called are always reflected.
"""
from __future__ import annotations

from dataclasses import dataclass

from diamond_draft.models.team import Team


@dataclass
class Matchup:
    """A single weekly head-to-head fantasy contest between two teams.

    Scores are computed lazily via ``Team.total_points()`` each time
    ``scores()`` is called. This means that changing a team's lineup after
    constructing the matchup but before reading its score is always safe.

    Attributes:
        home: The home team for this matchup.
        away: The away team for this matchup.
        week: 1-based week number within the season (1–10).
    """

    home: Team
    away: Team
    week: int

    # ------------------------------------------------------------------
    # Score access
    # ------------------------------------------------------------------

    def scores(self) -> tuple[float, float]:
        """Return the home and away fantasy point totals for this matchup.

        Returns:
            A 2-tuple of ``(home_points, away_points)``.
        """
        return self.home.total_points(), self.away.total_points()

    def determine_winner(self) -> Team | None:
        """Return the winning team, or ``None`` on a tie.

        Returns:
            The ``Team`` with the higher score, or ``None`` when both teams
            scored exactly the same number of points.
        """
        home_pts, away_pts = self.scores()
        if home_pts > away_pts:
            return self.home
        if away_pts > home_pts:
            return self.away
        return None  # tie — neither team gets a win

    def summary(self) -> dict:
        """Return a human-readable summary of this matchup's result.

        Returns:
            A dict with keys ``"week"``, ``"home"``, ``"away"``,
            ``"home_points"``, ``"away_points"``, and ``"winner"``
            (team name or ``"Tie"``).
        """
        home_pts, away_pts = self.scores()
        if home_pts > away_pts:
            winner_name = self.home.name
        elif away_pts > home_pts:
            winner_name = self.away.name
        else:
            winner_name = "Tie"
        return {
            "week":        self.week,
            "home":        self.home.name,
            "away":        self.away.name,
            "home_points": round(home_pts, 2),
            "away_points": round(away_pts, 2),
            "winner":      winner_name,
        }

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the matchup to a JSON-compatible dictionary.

        Only the team names and week number are stored — scores are
        re-calculated from the teams' current stats on load.

        Returns:
            A plain dict with ``"home"``, ``"away"``, and ``"week"`` keys.
        """
        return {
            "home": self.home.name,
            "away": self.away.name,
            "week": self.week,
        }

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        s = self.summary()
        return (
            f"Week {s['week']}: {s['home']} {s['home_points']} — "
            f"{s['away_points']} {s['away']}  (Winner: {s['winner']})"
        )
