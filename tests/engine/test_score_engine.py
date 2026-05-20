"""Unit tests for ScoreEngine — fully deterministic, no mocking needed."""
from __future__ import annotations

import pytest

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.player import Batter, Pitcher, Player, Position


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _batter(stats=None, weekly_factor=1.0):
    b = Batter(name="B", mlb_team="T", position="OF", stats=stats or {})
    b.weekly_factor = weekly_factor
    return b


def _pitcher(stats=None, weekly_factor=1.0):
    p = Pitcher(name="P", mlb_team="T", position="SP", stats=stats or {})
    p.weekly_factor = weekly_factor
    return p


# ---------------------------------------------------------------------------
# _weighted_sum
# ---------------------------------------------------------------------------

def test_weighted_sum_correct_calculation():
    stats   = {"HR": 10, "RBI": 50}
    weights = {"HR": 4.0, "RBI": 1.0, "X": 2.0}
    assert ScoreEngine._weighted_sum(stats, weights) == pytest.approx(90.0)


def test_weighted_sum_missing_stats_treated_as_zero():
    assert ScoreEngine._weighted_sum({}, {"HR": 4.0}) == pytest.approx(0.0)


def test_weighted_sum_negative_weight():
    stats   = {"SO": 10}
    weights = {"SO": -1.0}
    assert ScoreEngine._weighted_sum(stats, weights) == pytest.approx(-10.0)


# ---------------------------------------------------------------------------
# Batter scoring
# ---------------------------------------------------------------------------

def test_score_batter_dot_product_correct():
    # HR×4 + RBI×1 + R×1 + SB×2 + H×1 + SO×(−1)
    # 10×4 + 50×1 + 40×1 + 5×2 + 100×1 + 80×(−1) = 40+50+40+10+100−80 = 160
    b = _batter({"HR": 10, "RBI": 50, "R": 40, "SB": 5, "H": 100, "SO": 80})
    assert ScoreEngine._score_batter(b) == pytest.approx(160.0)


def test_score_batter_empty_stats_returns_zero():
    assert ScoreEngine._score_batter(_batter({})) == pytest.approx(0.0)


def test_score_batter_applies_weekly_factor():
    b = _batter({"HR": 10}, weekly_factor=0.5)
    raw = ScoreEngine._score_batter(b)
    assert ScoreEngine.score(b) == pytest.approx(raw * 0.5)


def test_score_batter_injured_player_returns_zero():
    b = _batter({"HR": 10, "RBI": 50}, weekly_factor=0.0)
    assert ScoreEngine.score(b) == pytest.approx(0.0)


def test_score_batter_factor_above_one_scales_up():
    b = _batter({"HR": 10}, weekly_factor=1.3)
    raw = ScoreEngine._score_batter(b)
    assert ScoreEngine.score(b) == pytest.approx(raw * 1.3)


# ---------------------------------------------------------------------------
# Pitcher scoring
# ---------------------------------------------------------------------------

def test_score_pitcher_base_calculation_no_era():
    # W×4 + SO×1 + IP×1 + SV×4 + L×(−4), no ERA key → no bonus
    # 15×4 + 200 + 180 + 0 + 5×(−4) = 60+200+180+0−20 = 420
    p = _pitcher({"W": 15, "SO": 200, "IP": 180, "SV": 0, "L": 5})
    assert ScoreEngine._score_pitcher(p) == pytest.approx(420.0)


def test_score_pitcher_era_bonus_when_below_threshold():
    # base: 10×4+150+150+0+5×(−4) = 40+150+150−20 = 320; ERA 2.50 < 3.00 → +2
    p = _pitcher({"W": 10, "SO": 150, "IP": 150, "SV": 0, "L": 5, "ERA": 2.50})
    assert ScoreEngine._score_pitcher(p) == pytest.approx(322.0)


def test_score_pitcher_no_era_bonus_when_at_threshold():
    # ERA exactly 3.00: condition is ERA < 3.00, so no bonus
    p = _pitcher({"W": 10, "SO": 150, "IP": 150, "SV": 0, "L": 5, "ERA": 3.00})
    assert ScoreEngine._score_pitcher(p) == pytest.approx(320.0)


def test_score_pitcher_no_era_bonus_above_threshold():
    p = _pitcher({"W": 10, "SO": 150, "IP": 150, "SV": 0, "L": 5, "ERA": 4.50})
    assert ScoreEngine._score_pitcher(p) == pytest.approx(320.0)


def test_score_pitcher_missing_era_defaults_to_99_no_bonus():
    p = _pitcher({"W": 15, "SO": 200, "IP": 180, "SV": 0, "L": 5})
    # no "ERA" key → default 99.0 → no bonus
    assert ScoreEngine._score_pitcher(p) == pytest.approx(420.0)


def test_score_pitcher_applies_weekly_factor():
    p = _pitcher({"W": 10, "SO": 150, "IP": 150, "SV": 0, "L": 5}, weekly_factor=2.0)
    raw = ScoreEngine._score_pitcher(p)
    assert ScoreEngine.score(p) == pytest.approx(raw * 2.0)


def test_score_pitcher_injured_returns_zero():
    p = _pitcher({"W": 15, "SO": 200, "IP": 180, "SV": 0, "L": 5}, weekly_factor=0.0)
    assert ScoreEngine.score(p) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Unknown player type
# ---------------------------------------------------------------------------

def test_score_unknown_player_type_raises_type_error():
    class FakePlayer(Player):
        def calculate_fantasy_points(self):
            return 0.0

    fake = FakePlayer.__new__(FakePlayer)
    fake.name = "X"
    fake.mlb_team = "T"
    fake.position = "OF"
    fake.stats = {}
    fake.weekly_factor = 1.0
    fake.injured_weeks_remaining = 0

    with pytest.raises(TypeError):
        ScoreEngine.score(fake)


def test_score_type_error_message_contains_class_name():
    class MyCustomPlayer(Player):
        def calculate_fantasy_points(self):
            return 0.0

    fake = MyCustomPlayer.__new__(MyCustomPlayer)
    fake.name = "X"
    fake.mlb_team = "T"
    fake.position = "OF"
    fake.stats = {}
    fake.weekly_factor = 1.0
    fake.injured_weeks_remaining = 0

    with pytest.raises(TypeError, match="MyCustomPlayer"):
        ScoreEngine.score(fake)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_era_bonus_threshold_is_3_00():
    assert ScoreEngine.ERA_BONUS_THRESHOLD == pytest.approx(3.00)


def test_era_bonus_value_is_2_0():
    assert ScoreEngine.ERA_BONUS == pytest.approx(2.0)


def test_batting_weights_keys():
    assert set(ScoreEngine.BATTING_WEIGHTS.keys()) == {"HR", "RBI", "R", "SB", "H", "SO"}


def test_pitching_weights_keys():
    assert set(ScoreEngine.PITCHING_WEIGHTS.keys()) == {"W", "SO", "IP", "SV", "L"}
