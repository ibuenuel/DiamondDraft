"""League domain model for Diamond Draft.

A ``League`` owns the list of teams, the pre-generated season schedule, and
the live standings. The schedule is a two-cycle round-robin that produces
exactly 10 weeks of matchups for six teams.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from diamond_draft.models.matchup import Matchup
from diamond_draft.models.team import Team


@dataclass
class League:
    """Manage teams, the season schedule, and weekly standings.

    The schedule is generated once after the draft completes and is never
    mutated — ``SeasonSimulator`` reads weeks from it sequentially.
    Standings are updated in-place by ``update_standings`` after each matchup.

    Attributes:
        teams: All six ``Team`` objects in the league.
        schedule: List of weekly matchup lists. ``schedule[i]`` is the list of
            ``Matchup`` objects for week ``i + 1``.
    """

    TEAM_COUNT: ClassVar[int] = 6
    """Number of teams in the league (always six in a standard draft)."""

    WEEKS: ClassVar[int] = 10
    """Total number of regular-season weeks (two full round-robin cycles)."""

    teams:    list[Team]            = field(default_factory=list)
    schedule: list[list[Matchup]]   = field(default_factory=list)

    # ------------------------------------------------------------------
    # Schedule generation
    # ------------------------------------------------------------------

    def generate_schedule(self) -> None:
        """Build a 10-week round-robin schedule and store it in ``self.schedule``.

        With 6 teams, a single round-robin requires 5 rounds (each team plays
        every other team once). Two cycles fill 10 weeks; home and away are
        swapped on the second cycle to ensure each pair plays once at each
        location over the season.

        The standard "fix one team, rotate the rest" algorithm is used. Team at
        index 0 is fixed; the other five rotate one position per round.
        """
        self.schedule = []
        n        = len(self.teams)
        rotation = list(range(1, n))   # indices 1..n-1 rotate each round

        def _round(offset: int, swap_home_away: bool) -> list[Matchup]:
            week_matchups: list[Matchup] = []
            slots = [0] + rotation[offset:] + rotation[:offset]
            for i in range(n // 2):
                a, b = slots[i], slots[n - 1 - i]
                if swap_home_away:
                    home, away = self.teams[b], self.teams[a]
                else:
                    home, away = self.teams[a], self.teams[b]
                week_matchups.append(
                    Matchup(home=home, away=away, week=len(self.schedule) + 1)
                )
            return week_matchups

        for cycle in range(2):              # two full round-robins = 10 weeks
            for r in range(n - 1):          # 5 rounds per cycle
                self.schedule.append(_round(r, swap_home_away=(cycle == 1)))

    # ------------------------------------------------------------------
    # Standings
    # ------------------------------------------------------------------

    def update_standings(self, matchup: Matchup) -> None:
        """Increment the winner's win count and the loser's loss count.

        Tied matchups (identical scores) do not affect the standings; this
        is consistent with standard fantasy baseball tie-breaking rules.

        Args:
            matchup: The completed ``Matchup`` whose scores are already set.
        """
        winner = matchup.determine_winner()
        if winner is None:
            return   # tie — neither team's record changes
        loser = matchup.away if winner is matchup.home else matchup.home
        winner.wins   += 1
        loser.losses  += 1

    def get_standings(self) -> list[dict]:
        """Return all teams sorted by wins (descending) with points as a tiebreaker.

        Returns:
            A list of dicts, each containing ``"team"``, ``"wins"``,
            ``"losses"``, and ``"points"`` keys, sorted from first to last place.
        """
        return sorted(
            [
                {
                    "team":   t.name,
                    "wins":   t.wins,
                    "losses": t.losses,
                    "points": round(t.total_points(), 1),
                }
                for t in self.teams
            ],
            key=lambda row: (row["wins"], row["points"]),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the league to a JSON-compatible dictionary.

        Returns:
            A plain dict with ``"teams"`` and ``"schedule"`` keys.
        """
        return {
            "teams": [t.to_dict() for t in self.teams],
            "schedule": [
                [m.to_dict() for m in week]
                for week in self.schedule
            ],
        }

    @classmethod
    def from_dict(cls, data: dict, teams: list[Team]) -> League:
        """Reconstruct a ``League`` from saved data using pre-built teams.

        Teams are resolved by name from the provided list rather than being
        re-constructed from scratch, so the caller controls team identity.

        Args:
            data: A dict previously produced by ``to_dict``.
            teams: The list of ``Team`` objects already reconstructed from
                the same save file. Used to link ``Matchup`` home/away refs.

        Returns:
            A fully initialised ``League`` instance with the saved schedule.
        """
        team_map = {t.name: t for t in teams}
        league   = cls(teams=teams)
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
