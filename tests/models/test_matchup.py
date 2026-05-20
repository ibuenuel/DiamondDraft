"""Unit tests for the Matchup model — all methods are pure."""
from __future__ import annotations

import pytest

from diamond_draft.models.matchup import Matchup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matchup(home_pts: float, away_pts: float, week: int = 3, make_team=None):
    """Build a Matchup whose total_points are monkey-patched."""
    home = make_team(name="Home Team")
    away = make_team(name="Away Team")
    home.total_points = lambda: home_pts
    away.total_points = lambda: away_pts
    return Matchup(home=home, away=away, week=week)


# ---------------------------------------------------------------------------
# scores()
# ---------------------------------------------------------------------------

def test_scores_returns_home_and_away_points(make_team):
    m = _matchup(100.0, 90.0, make_team=make_team)
    assert m.scores() == (pytest.approx(100.0), pytest.approx(90.0))


# ---------------------------------------------------------------------------
# determine_winner()
# ---------------------------------------------------------------------------

def test_determine_winner_home_wins(make_team):
    m = _matchup(100.0, 90.0, make_team=make_team)
    assert m.determine_winner() is m.home


def test_determine_winner_away_wins(make_team):
    m = _matchup(80.0, 90.0, make_team=make_team)
    assert m.determine_winner() is m.away


def test_determine_winner_tie_returns_none(make_team):
    m = _matchup(75.0, 75.0, make_team=make_team)
    assert m.determine_winner() is None


# ---------------------------------------------------------------------------
# summary()
# ---------------------------------------------------------------------------

def test_summary_home_wins(make_team):
    m = _matchup(100.0, 80.0, week=5, make_team=make_team)
    s = m.summary()
    assert s["winner"] == "Home Team"
    assert s["week"] == 5


def test_summary_away_wins(make_team):
    m = _matchup(60.0, 90.0, make_team=make_team)
    s = m.summary()
    assert s["winner"] == "Away Team"


def test_summary_tie(make_team):
    m = _matchup(75.0, 75.0, make_team=make_team)
    assert m.summary()["winner"] == "Tie"


def test_summary_keys_present(make_team):
    m = _matchup(100.0, 90.0, make_team=make_team)
    s = m.summary()
    for key in ("week", "home", "away", "home_points", "away_points", "winner"):
        assert key in s


def test_summary_points_rounded_to_two_decimal_places(make_team):
    m = _matchup(100.12345, 90.98765, make_team=make_team)
    s = m.summary()
    assert s["home_points"] == pytest.approx(100.12)
    assert s["away_points"] == pytest.approx(90.99)


# ---------------------------------------------------------------------------
# to_dict()
# ---------------------------------------------------------------------------

def test_to_dict_contains_correct_keys(make_team):
    m = _matchup(100.0, 90.0, week=3, make_team=make_team)
    d = m.to_dict()
    assert d == {"home": "Home Team", "away": "Away Team", "week": 3}


# ---------------------------------------------------------------------------
# __str__
# ---------------------------------------------------------------------------

def test_str_contains_week_and_teams(make_team):
    m = _matchup(100.0, 90.0, week=7, make_team=make_team)
    s = str(m)
    assert "7" in s
    assert "Home Team" in s
    assert "Away Team" in s
