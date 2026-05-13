"""Playoff simulation engine for Diamond Draft.

Drives the two-round knockout bracket (Semifinal → Final) that follows the
regular season. The top four teams by standings seed compete; the higher seed
advances on a points tie so there is always a definitive winner.

Public API mirrors the narrow contract of ``SeasonSimulator``:

- ``simulate_round()`` applies injuries/variance, runs that round's matchups,
  stores the results, and returns them.
- ``is_complete`` is ``True`` once the champion has been decided.
- ``to_dict`` / ``from_dict`` support save/load via ``SaveManager``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.engine.season_simulator import _WeeklyFactorApplier
from diamond_draft.models.matchup import Matchup
from diamond_draft.models.team import Team

# Playoff weeks start right after the regular season.
_SEMIFINAL_WEEK = 11
_FINAL_WEEK     = 12


@dataclass
class PlayoffResult:
    """Immutable record of one playoff matchup's outcome.

    Scores are captured at the moment the matchup is simulated so they remain
    stable even after the next round's weekly factors are applied.

    Attributes:
        home:        Home team for this matchup.
        away:        Away team for this matchup.
        home_points: Fantasy points scored by the home team.
        away_points: Fantasy points scored by the away team.
        winner:      The team that advances; never ``None`` (ties broken by seed).
        week:        Playoff week number (11 = Semifinal, 12 = Final).
    """

    home:        Team
    away:        Team
    home_points: float
    away_points: float
    winner:      Team
    week:        int

    def summary(self) -> dict:
        """Return a display-ready summary dict matching ``Matchup.summary()``'s shape."""
        return {
            "week":        self.week,
            "home":        self.home.name,
            "away":        self.away.name,
            "home_points": round(self.home_points, 2),
            "away_points": round(self.away_points, 2),
            "winner":      self.winner.name,
        }


class PlayoffSimulator:
    """Drive the two-round knockout playoff bracket.

    Seeds are ranked 1st–4th coming out of the regular season:

    - Semifinal: #1 vs #4,  #2 vs #3
    - Final:     winner of SF1 vs winner of SF2

    On a points tie the higher seed (lower index in ``seeds``) advances, so
    there is always a decisive winner — no ties in the postseason.

    Args:
        seeds: Exactly four ``Team`` objects ordered from 1st to 4th place.
    """

    ROUND_NAMES: dict[int, str] = {0: "Semifinal", 1: "Final"}

    def __init__(self, seeds: list[Team]) -> None:
        if len(seeds) != 4:
            raise ValueError(f"Playoffs require exactly 4 seeds, got {len(seeds)}.")
        self.seeds: list[Team] = seeds
        self.current_round: int = 0
        self.semifinal_results: list[PlayoffResult] = []
        self.final_result: PlayoffResult | None = None
        self.champion: Team | None = None
        self.injury_report: list[str] = []
        self._applier = _WeeklyFactorApplier(ScoreEngine)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        return self.champion is not None

    @property
    def round_name(self) -> str:
        return self.ROUND_NAMES.get(self.current_round, "")

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_round(self) -> list[PlayoffResult]:
        """Simulate the next playoff round and return its results.

        Applies injury/variance mutations to the four playoff teams, auto-sets
        CPU lineups, runs this round's matchups, stores the results, and
        advances ``current_round``.

        Returns:
            A list of ``PlayoffResult`` objects for the round just played.

        Raises:
            RuntimeError: If called when ``is_complete`` is ``True``.
        """
        if self.is_complete:
            raise RuntimeError("Playoffs are already complete — a champion has been crowned.")

        # Mutate weekly factors for the four participating teams only.
        self.injury_report = self._applier.apply(self.seeds)
        self._applier.set_cpu_lineups(self.seeds)

        if self.current_round == 0:
            results = self._run_semifinals()
            self.semifinal_results = results
            self.current_round = 1
            return results

        if self.current_round == 1:
            result = self._run_final()
            self.final_result = result
            self.champion = result.winner
            self.current_round = 2
            return [result]

        raise RuntimeError("Unexpected playoff state.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_semifinals(self) -> list[PlayoffResult]:
        """Run Semifinal 1 (#1 vs #4) and Semifinal 2 (#2 vs #3)."""
        s1 = self._play(self.seeds[0], self.seeds[3], seed_home=0, seed_away=3, week=_SEMIFINAL_WEEK)
        s2 = self._play(self.seeds[1], self.seeds[2], seed_home=1, seed_away=2, week=_SEMIFINAL_WEEK)
        return [s1, s2]

    def _run_final(self) -> PlayoffResult:
        """Run the Final between the two semifinal winners."""
        w1 = self.semifinal_results[0].winner
        w2 = self.semifinal_results[1].winner
        # Higher seed (lower index in self.seeds) is home.
        seed_w1 = self.seeds.index(w1)
        seed_w2 = self.seeds.index(w2)
        if seed_w1 <= seed_w2:
            return self._play(w1, w2, seed_home=seed_w1, seed_away=seed_w2, week=_FINAL_WEEK)
        return self._play(w2, w1, seed_home=seed_w2, seed_away=seed_w1, week=_FINAL_WEEK)

    def _play(
        self,
        home: Team,
        away: Team,
        seed_home: int,
        seed_away: int,
        week: int,
    ) -> PlayoffResult:
        """Compute scores for one matchup and return a ``PlayoffResult``.

        Scores are read immediately (not lazily) so they remain stable after
        the next round's weekly factors are applied. Ties are broken by seed
        rank — the lower seed index (higher standing) always advances.
        """
        matchup = Matchup(home=home, away=away, week=week)
        home_pts, away_pts = matchup.scores()
        if home_pts > away_pts:
            winner = home
        elif away_pts > home_pts:
            winner = away
        else:
            # Tie: higher seed advances (lower index = better standing).
            winner = home if seed_home < seed_away else away
        return PlayoffResult(
            home=home,
            away=away,
            home_points=home_pts,
            away_points=away_pts,
            winner=winner,
            week=week,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise playoff state to a JSON-compatible dict."""
        return {
            "current_round":      self.current_round,
            "seeds":              [t.name for t in self.seeds],
            "semifinal_results":  [_result_to_dict(r) for r in self.semifinal_results],
            "final_result":       _result_to_dict(self.final_result) if self.final_result else None,
            "champion":           self.champion.name if self.champion else None,
        }

    @classmethod
    def from_dict(cls, data: dict, team_map: dict[str, Team]) -> PlayoffSimulator:
        """Reconstruct a ``PlayoffSimulator`` from a saved dict.

        Args:
            data:     Dict previously produced by ``to_dict``.
            team_map: Mapping from team name to ``Team`` object.

        Returns:
            A fully restored ``PlayoffSimulator``.
        """
        seeds = [team_map[name] for name in data["seeds"]]
        sim = cls(seeds)
        sim.current_round = int(data["current_round"])
        sim.semifinal_results = [
            _result_from_dict(r, team_map) for r in data.get("semifinal_results", [])
        ]
        final_raw = data.get("final_result")
        sim.final_result = _result_from_dict(final_raw, team_map) if final_raw else None
        champion_name = data.get("champion")
        sim.champion = team_map[champion_name] if champion_name else None
        return sim


# ---------------------------------------------------------------------------
# Module-level helpers (private)
# ---------------------------------------------------------------------------

def _result_to_dict(r: PlayoffResult) -> dict:
    return {
        "home":        r.home.name,
        "away":        r.away.name,
        "home_points": r.home_points,
        "away_points": r.away_points,
        "winner":      r.winner.name,
        "week":        r.week,
    }


def _result_from_dict(d: dict, team_map: dict[str, Team]) -> PlayoffResult:
    return PlayoffResult(
        home=team_map[d["home"]],
        away=team_map[d["away"]],
        home_points=float(d["home_points"]),
        away_points=float(d["away_points"]),
        winner=team_map[d["winner"]],
        week=int(d["week"]),
    )
