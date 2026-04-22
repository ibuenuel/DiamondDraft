from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from diamond_draft.models.matchup import Matchup
from diamond_draft.models.team import Team


@dataclass
class League:
    """Manages all teams, the season schedule, and standings."""

    TEAM_COUNT: ClassVar[int] = 6
    WEEKS: ClassVar[int] = 10

    teams: list[Team] = field(default_factory=list)
    schedule: list[list[Matchup]] = field(default_factory=list)

    # --- Schedule -----------------------------------------------------------

    def generate_schedule(self) -> None:
        """
        Builds a 10-week round-robin schedule.

        With 6 teams, a full round-robin takes 5 rounds (each team plays every
        other team once). Two cycles fill 10 weeks, with home/away swapped on
        the second cycle.
        """
        self.schedule = []
        n = len(self.teams)
        # Standard round-robin: fix teams[0], rotate the rest
        rotation = list(range(1, n))

        def _round(offset: int, swap_home_away: bool) -> list[Matchup]:
            week_matchups: list[Matchup] = []
            fixed = 0
            slots = [fixed] + rotation[offset:] + rotation[:offset]
            for i in range(n // 2):
                a, b = slots[i], slots[n - 1 - i]
                home, away = (self.teams[b], self.teams[a]) if swap_home_away else (self.teams[a], self.teams[b])
                week_matchups.append(Matchup(home=home, away=away, week=len(self.schedule) + 1))
            return week_matchups

        for cycle in range(2):  # two full round-robins = 10 weeks
            for r in range(n - 1):  # 5 rounds per cycle
                self.schedule.append(_round(r, swap_home_away=(cycle == 1)))

    # --- Standings ----------------------------------------------------------

    def update_standings(self, matchup: Matchup) -> None:
        winner = matchup.determine_winner()
        if winner is None:
            return  # ties do not affect W/L
        loser = matchup.away if winner is matchup.home else matchup.home
        winner.wins += 1
        loser.losses += 1

    def get_standings(self) -> list[dict]:
        """Returns teams sorted by wins descending, then points as tiebreaker."""
        return sorted(
            [
                {
                    "team": t.name,
                    "wins": t.wins,
                    "losses": t.losses,
                    "points": round(t.total_points(), 1),
                }
                for t in self.teams
            ],
            key=lambda row: (row["wins"], row["points"]),
            reverse=True,
        )

    # --- Serialization ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "teams": [t.to_dict() for t in self.teams],
            "schedule": [
                [m.to_dict() for m in week]
                for week in self.schedule
            ],
        }

    @classmethod
    def from_dict(cls, data: dict, teams: list[Team]) -> League:
        """Reconstruct League from saved data; teams are resolved by name."""
        team_map = {t.name: t for t in teams}
        league = cls(teams=teams)
        league.schedule = [
            [
                Matchup(
                    home=team_map[m["home"]],
                    away=team_map[m["away"]],
                    week=m["week"],
                )
                for m in week
            ]
            for week in data["schedule"]
        ]
        return league
