"""Shared pytest fixtures for the Diamond Draft test suite."""
from __future__ import annotations

import pytest

from diamond_draft.models.player import Batter, Pitcher, Position
from diamond_draft.models.team import Team
from diamond_draft.models.league import League


# ---------------------------------------------------------------------------
# Player factories
# ---------------------------------------------------------------------------

@pytest.fixture
def make_batter():
    def _factory(
        name="Test Batter",
        mlb_team="Yankees",
        position=Position.OUTFIELD,
        stats=None,
        mlb_id=None,
        weekly_factor=1.0,
        injured_weeks_remaining=0,
    ):
        if stats is None:
            stats = {"HR": 10, "RBI": 50, "R": 40, "SB": 5, "H": 100, "SO": 80}
        b = Batter(
            name=name,
            mlb_team=mlb_team,
            position=str(position),
            stats=stats,
            mlb_id=mlb_id,
        )
        b.weekly_factor = weekly_factor
        b.injured_weeks_remaining = injured_weeks_remaining
        return b

    return _factory


@pytest.fixture
def make_pitcher():
    def _factory(
        name="Test Pitcher",
        mlb_team="Dodgers",
        position=Position.STARTING_PITCHER,
        stats=None,
        mlb_id=None,
        weekly_factor=1.0,
        injured_weeks_remaining=0,
    ):
        if stats is None:
            stats = {"W": 15, "SO": 200, "IP": 180, "SV": 0, "L": 5, "ERA": 3.50}
        p = Pitcher(
            name=name,
            mlb_team=mlb_team,
            position=str(position),
            stats=stats,
            mlb_id=mlb_id,
        )
        p.weekly_factor = weekly_factor
        p.injured_weeks_remaining = injured_weeks_remaining
        return p

    return _factory


@pytest.fixture
def sample_batter(make_batter):
    return make_batter()


@pytest.fixture
def sample_pitcher(make_pitcher):
    return make_pitcher()


# ---------------------------------------------------------------------------
# Team factory
# ---------------------------------------------------------------------------

@pytest.fixture
def make_team():
    def _factory(name="Team A", is_human=False, wins=0, losses=0):
        t = Team(name=name, is_human=is_human)
        t.wins = wins
        t.losses = losses
        return t

    return _factory


@pytest.fixture
def full_roster_team(make_team, make_batter, make_pitcher):
    """A Team with all 14 roster slots filled."""
    t = make_team(name="Full Team", is_human=True)
    players = [
        make_pitcher(name="SP1", position="SP"),
        make_pitcher(name="SP2", position="SP"),
        make_batter(name="Catcher", position="C"),
        make_batter(name="First", position="1B"),
        make_batter(name="Second", position="2B"),
        make_batter(name="Third", position="3B"),
        make_batter(name="Short", position="SS"),
        make_batter(name="OF1", position="OF"),
        make_batter(name="OF2", position="OF"),
        make_batter(name="OF3", position="OF"),
        make_batter(name="DH", position="DH"),
        make_pitcher(name="BenchSP", position="SP"),
        make_batter(name="BenchOF", position="OF"),
        make_batter(name="Bench1B", position="1B"),
    ]
    for p in players:
        t.roster.append(p)
    return t


# ---------------------------------------------------------------------------
# League / multi-team fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def six_teams(make_team, make_batter):
    """Six teams; index 0 is human, rest are CPU. Each has one batter."""
    teams = [
        make_team(name=f"Team {i}", is_human=(i == 0))
        for i in range(6)
    ]
    for t in teams:
        t.roster.append(make_batter(name=f"Player {t.name}", mlb_team="Test"))
    return teams


@pytest.fixture
def league_with_schedule(six_teams):
    league = League(teams=six_teams)
    league.generate_schedule()
    return league


# ---------------------------------------------------------------------------
# Draft player pool
# ---------------------------------------------------------------------------

@pytest.fixture
def player_pool(make_batter, make_pitcher):
    """84 uniquely-named players sufficient for a 6-team × 14-player draft."""
    pool = []
    for i in range(12):
        pool.append(make_pitcher(
            name=f"SP{i}",
            position="SP",
            stats={"W": max(1, 15 - i), "SO": 200, "IP": 180, "SV": 0, "L": 5, "ERA": 3.0 + i * 0.1},
        ))
    for i in range(6):
        pool.append(make_pitcher(
            name=f"RP{i}",
            position="RP",
            stats={"W": 3, "SO": 60, "IP": 60, "SV": max(1, 15 - i), "L": 2, "ERA": 2.50},
        ))
    batter_configs = [
        ("C",  6),
        ("1B", 6),
        ("2B", 6),
        ("3B", 6),
        ("SS", 6),
        ("OF", 18),
        ("DH", 6),
    ]
    for pos, count in batter_configs:
        for i in range(count):
            pool.append(make_batter(
                name=f"{pos}{i}",
                position=pos,
                stats={"HR": 10 + i, "RBI": 50, "R": 40, "SB": 5, "H": 100, "SO": 80},
            ))
    return pool
