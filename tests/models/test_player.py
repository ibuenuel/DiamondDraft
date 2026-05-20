"""Unit tests for Player, Batter, and Pitcher models."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from diamond_draft.models.player import Batter, Pitcher, Player, Position


# ---------------------------------------------------------------------------
# player_id property
# ---------------------------------------------------------------------------

def test_batter_player_id_format():
    b = Batter(name="Aaron Judge", mlb_team="New York Yankees", position="OF", stats={})
    assert b.player_id == "Aaron_Judge_New_York_Yankees_OF"


def test_pitcher_player_id_format():
    p = Pitcher(name="Sandy Koufax", mlb_team="Los Angeles Dodgers", position="SP", stats={})
    assert p.player_id == "Sandy_Koufax_Los_Angeles_Dodgers_SP"


def test_player_id_has_no_raw_spaces():
    b = Batter(name="Mike Trout", mlb_team="Los Angeles Angels", position="OF", stats={})
    assert " " not in b.player_id


# ---------------------------------------------------------------------------
# __str__
# ---------------------------------------------------------------------------

def test_player_str_representation(make_batter):
    b = make_batter(name="Test Batter", mlb_team="Yankees", position="OF")
    assert str(b) == "Test Batter (OF, Yankees)"


# ---------------------------------------------------------------------------
# Equality and hash
# ---------------------------------------------------------------------------

def test_player_equality_same_id(make_batter):
    b1 = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    b2 = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    assert b1 == b2


def test_player_equality_different_position(make_batter, make_pitcher):
    b = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    p = make_pitcher(name="Doe", mlb_team="Cubs", position="SP")
    assert b != p


def test_player_not_equal_to_non_player(make_batter):
    b = make_batter()
    assert b.__eq__("not a player") is NotImplemented


def test_player_hash_consistency(make_batter):
    b1 = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    b2 = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    assert hash(b1) == hash(b2)


def test_batter_usable_in_set(make_batter):
    b1 = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    b2 = make_batter(name="Doe", mlb_team="Cubs", position="OF")
    s = {b1, b2}
    assert len(s) == 1


# ---------------------------------------------------------------------------
# calculate_fantasy_points delegation
# ---------------------------------------------------------------------------

def test_calculate_fantasy_points_batter_delegates_to_score_engine(make_batter):
    b = make_batter()
    with patch("diamond_draft.engine.score_engine.ScoreEngine.score", return_value=99.9):
        result = b.calculate_fantasy_points()
    assert result == pytest.approx(99.9)


def test_calculate_fantasy_points_pitcher_delegates_to_score_engine(make_pitcher):
    p = make_pitcher()
    with patch("diamond_draft.engine.score_engine.ScoreEngine.score", return_value=77.7):
        result = p.calculate_fantasy_points()
    assert result == pytest.approx(77.7)


# ---------------------------------------------------------------------------
# Serialisation round-trips
# ---------------------------------------------------------------------------

def test_batter_to_dict_round_trip(make_batter):
    b = make_batter(name="Judge", mlb_team="Yankees", position="OF",
                    stats={"HR": 30}, weekly_factor=0.8, injured_weeks_remaining=1)
    restored = Player.from_dict(b.to_dict())
    assert restored == b
    assert restored.weekly_factor == pytest.approx(0.8)
    assert restored.injured_weeks_remaining == 1


def test_pitcher_to_dict_round_trip(make_pitcher):
    p = make_pitcher(name="Verlander", mlb_team="Astros", position="SP",
                     stats={"W": 18}, weekly_factor=1.1, injured_weeks_remaining=0)
    restored = Player.from_dict(p.to_dict())
    assert restored == p
    assert restored.weekly_factor == pytest.approx(1.1)


def test_from_dict_restores_weekly_factor(make_batter):
    b = make_batter(weekly_factor=0.5)
    restored = Player.from_dict(b.to_dict())
    assert restored.weekly_factor == pytest.approx(0.5)


def test_from_dict_restores_injured_weeks_remaining(make_pitcher):
    p = make_pitcher(injured_weeks_remaining=2)
    restored = Player.from_dict(p.to_dict())
    assert restored.injured_weeks_remaining == 2


def test_from_dict_defaults_weekly_factor_when_missing(make_batter):
    data = make_batter().to_dict()
    del data["weekly_factor"]
    restored = Player.from_dict(data)
    assert restored.weekly_factor == pytest.approx(1.0)


def test_from_dict_defaults_injured_weeks_when_missing(make_batter):
    data = make_batter().to_dict()
    del data["injured_weeks_remaining"]
    restored = Player.from_dict(data)
    assert restored.injured_weeks_remaining == 0


def test_from_dict_unknown_type_raises_key_error(make_batter):
    data = make_batter().to_dict()
    data["type"] = "UnknownType"
    with pytest.raises(KeyError):
        Player.from_dict(data)


# ---------------------------------------------------------------------------
# Position enum
# ---------------------------------------------------------------------------

def test_position_enum_string_equality():
    assert Position.OUTFIELD == "OF"
    assert Position.STARTING_PITCHER == "SP"
    assert Position.CATCHER == "C"


def test_batter_positions_class_var():
    assert "OF" in Batter.POSITIONS
    assert "SP" not in Batter.POSITIONS
    assert "RP" not in Batter.POSITIONS


def test_pitcher_positions_class_var():
    assert "SP" in Pitcher.POSITIONS
    assert "RP" in Pitcher.POSITIONS
    assert "OF" not in Pitcher.POSITIONS
