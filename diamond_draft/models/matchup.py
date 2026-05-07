from __future__ import annotations

from dataclasses import dataclass

from diamond_draft.models.team import Team


@dataclass
class Matchup:
    """A single weekly head-to-head contest between two teams."""

    home: Team
    away: Team
    week: int

    def scores(self) -> tuple[float, float]:
        """Return (home_points, away_points). Centralises the score calculation."""
        return self.home.total_points(), self.away.total_points()

    def determine_winner(self) -> Team | None:
        """Returns the winning team, or None on a tie."""
        home_pts, away_pts = self.scores()
        if home_pts > away_pts:
            return self.home
        if away_pts > home_pts:
            return self.away
        return None  # tie

    def summary(self) -> dict:
        home_pts, away_pts = self.scores()
        if home_pts > away_pts:
            winner_name = self.home.name
        elif away_pts > home_pts:
            winner_name = self.away.name
        else:
            winner_name = "Tie"
        return {
            "week": self.week,
            "home": self.home.name,
            "away": self.away.name,
            "home_points": round(home_pts, 2),
            "away_points": round(away_pts, 2),
            "winner": winner_name,
        }

    def to_dict(self) -> dict:
        return {
            "home": self.home.name,
            "away": self.away.name,
            "week": self.week,
        }

    def __str__(self) -> str:
        s = self.summary()
        return (
            f"Week {s['week']}: {s['home']} {s['home_points']} — "
            f"{s['away_points']} {s['away']}  (Winner: {s['winner']})"
        )
