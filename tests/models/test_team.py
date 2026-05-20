"""Unit tests for the Team model."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


# ---------------------------------------------------------------------------
# Class-level constants
# ---------------------------------------------------------------------------

def test_team_max_roster_size_is_14():
    assert Team.MAX_ROSTER_SIZE == 14


def test_team_active_size_is_11():
    assert Team.ACTIVE_SIZE == 11


def test_team_bench_spots_is_3():
    assert Team.BENCH_SPOTS == 3


# ---------------------------------------------------------------------------
# add_player / is_full
# ---------------------------------------------------------------------------

def test_add_player_increases_roster_size(make_team, make_batter):
    t = make_team()
    t.add_player(make_batter())
    assert len(t.roster) == 1


def test_add_player_to_full_roster_raises_value_error(full_roster_team, make_batter):
    with pytest.raises(ValueError, match="full"):
        full_roster_team.add_player(make_batter(name="Extra"))


def test_is_full_false_when_below_max(make_team, make_batter):
    t = make_team()
    for i in range(13):
        t.roster.append(make_batter(name=f"P{i}"))
    assert t.is_full() is False


def test_is_full_true_at_max(full_roster_team):
    assert full_roster_team.is_full() is True


# ---------------------------------------------------------------------------
# open_slots
# ---------------------------------------------------------------------------

def test_open_slots_empty_team_shows_all_positions(make_team):
    t = make_team()
    slots = t.open_slots()
    assert slots["SP"] == 2
    assert slots["C"]  == 1
    assert slots["OF"] == 3
    assert slots["BENCH"] == 3


def test_open_slots_after_adding_one_sp(make_team, make_pitcher):
    t = make_team()
    t.roster.append(make_pitcher(position="SP"))
    slots = t.open_slots()
    assert slots["SP"] == 1


def test_open_slots_active_slots_filled_shows_bench(make_team, make_batter, make_pitcher):
    t = make_team()
    # Fill all 11 active slots
    for pos in ["SP", "SP", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF", "DH"]:
        if pos in ("SP",):
            t.roster.append(make_pitcher(name=f"P_{pos}_{len(t.roster)}", position=pos))
        else:
            t.roster.append(make_batter(name=f"P_{pos}_{len(t.roster)}", position=pos))
    slots = t.open_slots()
    assert "BENCH" in slots
    assert slots["BENCH"] == 3


def test_open_slots_full_roster_returns_empty_dict(full_roster_team):
    assert full_roster_team.open_slots() == {}


# ---------------------------------------------------------------------------
# needs_position
# ---------------------------------------------------------------------------

def test_needs_position_true_when_slot_open(make_team):
    t = make_team()
    assert t.needs_position("OF") is True


def test_needs_position_true_via_bench(make_team, make_batter, make_pitcher):
    t = make_team()
    for pos in ["SP", "SP", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF", "DH"]:
        if pos == "SP":
            t.roster.append(make_pitcher(name=f"P{len(t.roster)}", position=pos))
        else:
            t.roster.append(make_batter(name=f"P{len(t.roster)}", position=pos))
    # All active slots filled but bench still open — RP can go to bench
    assert t.needs_position("RP") is True


def test_needs_position_false_when_roster_full(full_roster_team):
    assert full_roster_team.needs_position("OF") is False


# ---------------------------------------------------------------------------
# active_players
# ---------------------------------------------------------------------------

def test_active_players_returns_active_size(make_team, make_batter, make_pitcher):
    t = make_team()
    players = [make_pitcher(name="SP1", position="SP"), make_pitcher(name="SP2", position="SP")]
    for pos in ["C", "1B", "2B", "3B", "SS", "OF", "OF", "OF", "DH"]:
        players.append(make_batter(name=f"B{pos}", position=pos))
    for p in players:
        t.roster.append(p)
    t.active_lineup = players  # set explicit lineup
    assert len(t.active_players()) == Team.ACTIVE_SIZE


def test_active_players_from_active_lineup_when_populated(make_team, make_batter):
    t = make_team()
    lineup = [make_batter(name=f"P{i}") for i in range(Team.ACTIVE_SIZE)]
    for p in lineup:
        t.roster.append(p)
    t.active_lineup = lineup
    assert t.active_players() == lineup


def test_active_players_auto_selects_top_scorers_when_lineup_empty(
    make_team, make_batter
):
    t = make_team()
    players = [make_batter(name=f"P{i}", stats={"HR": i}) for i in range(14)]
    for p in players:
        t.roster.append(p)
    # active_lineup is empty → auto-select top 11 by score

    scores = {p.name: float(i) for i, p in enumerate(players)}
    with patch(
        "diamond_draft.engine.score_engine.ScoreEngine.score",
        side_effect=lambda p: scores[p.name],
    ):
        active = t.active_players()

    assert len(active) == Team.ACTIVE_SIZE
    # The top 11 are P3 through P13 (highest HR values)
    active_names = {p.name for p in active}
    for i in range(3, 14):
        assert f"P{i}" in active_names


# ---------------------------------------------------------------------------
# total_points
# ---------------------------------------------------------------------------

def test_total_points_sums_active_players(make_team, make_batter):
    t = make_team()
    lineup = [make_batter(name=f"P{i}") for i in range(Team.ACTIVE_SIZE)]
    for p in lineup:
        t.roster.append(p)
    t.active_lineup = lineup

    with patch(
        "diamond_draft.engine.score_engine.ScoreEngine.score",
        return_value=10.0,
    ):
        total = t.total_points()

    assert total == pytest.approx(110.0)  # 11 × 10.0


def test_total_points_zero_for_injured_active_player(make_team, make_batter):
    t = make_team()
    # One injured player + 10 healthy (each score 10.0 normally)
    injured = make_batter(name="Injured", weekly_factor=0.0)
    healthy = [make_batter(name=f"H{i}") for i in range(10)]
    lineup = [injured] + healthy
    for p in lineup:
        t.roster.append(p)
    t.active_lineup = lineup

    def fake_score(p):
        return 0.0 if p.weekly_factor == 0.0 else 10.0

    with patch("diamond_draft.engine.score_engine.ScoreEngine.score", side_effect=fake_score):
        total = t.total_points()

    assert total == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# record_str / __str__
# ---------------------------------------------------------------------------

def test_record_str_format(make_team):
    t = make_team(wins=5, losses=3)
    assert t.record_str() == "5-3"


def test_str_representation(make_team):
    t = make_team(name="Yankees", wins=5, losses=3)
    assert str(t) == "Yankees (5-3)"


# ---------------------------------------------------------------------------
# bench_players
# ---------------------------------------------------------------------------

def test_bench_players_excludes_active(make_team, make_batter, make_pitcher):
    t = make_team()
    active = [make_pitcher(name="SP1", position="SP"), make_pitcher(name="SP2", position="SP")]
    for pos in ["C", "1B", "2B", "3B", "SS", "OF", "OF", "OF", "DH"]:
        active.append(make_batter(name=f"A{pos}", position=pos))
    bench = [make_batter(name="Bench1"), make_batter(name="Bench2"), make_batter(name="Bench3")]
    for p in active + bench:
        t.roster.append(p)
    t.active_lineup = active

    bench_result = t.bench_players()
    assert len(bench_result) == 3
    bench_names = {p.name for p in bench_result}
    assert bench_names == {"Bench1", "Bench2", "Bench3"}


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def test_team_to_dict_round_trip(make_team, make_batter):
    t = make_team(name="Cubs", is_human=True, wins=3, losses=7)
    p = make_batter(name="Player A")
    t.roster.append(p)
    t.active_lineup = [p]

    data = t.to_dict()
    restored = Team.from_dict(data)

    assert restored.name == "Cubs"
    assert restored.is_human is True
    assert restored.wins == 3
    assert restored.losses == 7
    assert len(restored.roster) == 1
    assert restored.roster[0].name == "Player A"


def test_from_dict_restores_active_lineup_by_name(make_team, make_batter):
    t = make_team(name="Sox")
    players = [make_batter(name=f"P{i}") for i in range(Team.ACTIVE_SIZE)]
    for p in players:
        t.roster.append(p)
    t.active_lineup = players

    restored = Team.from_dict(t.to_dict())
    restored_names = [p.name for p in restored.active_lineup]
    original_names = [p.name for p in players]
    assert restored_names == original_names
