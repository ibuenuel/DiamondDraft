"""Unit tests for PlayoffSimulator and PlayoffResult."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from diamond_draft.engine.playoff_simulator import PlayoffResult, PlayoffSimulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0)):
    """4 seeds with deterministic total_points."""
    seeds = [make_team(name=f"Seed{i+1}") for i in range(4)]
    for seed, score in zip(seeds, pts):
        seed.total_points = lambda s=score: s
    return seeds


def _noop_applier(sim):
    """Patch the applier so weekly mutations are no-ops."""
    sim._applier.apply = lambda teams: []
    sim._applier.set_cpu_lineups = lambda teams: None


# ===========================================================================
# Initialisation
# ===========================================================================

def test_init_wrong_number_of_seeds_raises_value_error(make_team):
    with pytest.raises(ValueError, match="4"):
        PlayoffSimulator([make_team(name="T1"), make_team(name="T2"), make_team(name="T3")])


def test_init_stores_four_seeds(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    assert len(sim.seeds) == 4


def test_is_complete_false_at_start(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    assert sim.is_complete is False


def test_is_complete_true_when_champion_set(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    sim.champion = seeds[0]
    assert sim.is_complete is True


def test_round_name_semifinal(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    sim.current_round = 0
    assert sim.round_name == "Semifinal"


def test_round_name_final(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    sim.current_round = 1
    assert sim.round_name == "Final"


def test_round_name_empty_after_complete(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    sim.current_round = 2
    assert sim.round_name == ""


# ===========================================================================
# simulate_round — Semifinal
# ===========================================================================

def test_simulate_round_when_complete_raises_runtime_error(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    sim.champion = seeds[0]
    with pytest.raises(RuntimeError):
        sim.simulate_round()


def test_semifinal_pairings_seed0_vs_seed3_and_seed1_vs_seed2(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    results = sim.simulate_round()
    assert results[0].home is seeds[0]
    assert results[0].away is seeds[3]
    assert results[1].home is seeds[1]
    assert results[1].away is seeds[2]


def test_semifinal_returns_two_results(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    results = sim.simulate_round()
    assert len(results) == 2


def test_current_round_advances_after_semifinal(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    assert sim.current_round == 1


def test_semifinal_results_stored(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    assert len(sim.semifinal_results) == 2


# ===========================================================================
# simulate_round — Final
# ===========================================================================

def test_final_sets_champion(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()  # semifinals
    sim.simulate_round()  # final
    assert sim.champion is not None


def test_is_complete_after_two_rounds(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    sim.simulate_round()
    assert sim.is_complete is True


def test_final_returns_one_result(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    results = sim.simulate_round()
    assert len(results) == 1


def test_champion_is_highest_scorer_overall(make_team):
    # Seed0 scores 100, beats Seed3 (70); Seed1 scores 90, beats Seed2 (80)
    # Final: Seed0 (100) beats Seed1 (90) → champion is Seed0
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    sim.simulate_round()
    assert sim.champion is seeds[0]


# ===========================================================================
# Tie-breaking
# ===========================================================================

def test_semifinal_tie_higher_seed_advances(make_team):
    # Both SF matchups end in a tie → lower seed index (higher seed) advances
    seeds = _make_seeds(make_team, pts=(50.0, 50.0, 50.0, 50.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    results = sim.simulate_round()
    # SF1: seeds[0] vs seeds[3] → tie → seeds[0] (index 0) advances
    assert results[0].winner is seeds[0]
    # SF2: seeds[1] vs seeds[2] → tie → seeds[1] (index 1) advances
    assert results[1].winner is seeds[1]


def test_final_tie_lower_seed_index_wins(make_team):
    # All equal → seeds[0] and seeds[1] advance from SFs; final tie → seeds[0] wins
    seeds = _make_seeds(make_team, pts=(50.0, 50.0, 50.0, 50.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    sim.simulate_round()
    assert sim.champion is seeds[0]


def test_final_higher_seed_is_home(make_team):
    # seeds[0] wins SF1, seeds[1] wins SF2 → seeds[0] (index 0 < 1) is home in final
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    sim.simulate_round()
    assert sim.final_result.home is seeds[0]


# ===========================================================================
# PlayoffResult.summary()
# ===========================================================================

def test_playoff_result_summary_dict_shape(make_team):
    home = make_team(name="HomeT")
    away = make_team(name="AwayT")
    result = PlayoffResult(home=home, away=away, home_points=100.5,
                           away_points=90.3, winner=home, week=11)
    s = result.summary()
    for key in ("week", "home", "away", "home_points", "away_points", "winner"):
        assert key in s


def test_playoff_result_summary_winner_name(make_team):
    home = make_team(name="HomeT")
    away = make_team(name="AwayT")
    result = PlayoffResult(home=home, away=away, home_points=100.0,
                           away_points=80.0, winner=home, week=11)
    assert result.summary()["winner"] == "HomeT"


def test_playoff_result_summary_points_rounded(make_team):
    home = make_team(name="HomeT")
    away = make_team(name="AwayT")
    result = PlayoffResult(home=home, away=away, home_points=77.123,
                           away_points=66.789, winner=home, week=11)
    s = result.summary()
    assert s["home_points"] == pytest.approx(77.12)
    assert s["away_points"] == pytest.approx(66.79)


# ===========================================================================
# Serialisation
# ===========================================================================

def test_to_dict_champion_is_none_before_complete(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    assert sim.to_dict()["champion"] is None


def test_to_dict_contains_champion_name_after_complete(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    sim.simulate_round()
    d = sim.to_dict()
    assert d["champion"] == sim.champion.name


def test_to_dict_current_round_after_semifinal(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    assert sim.to_dict()["current_round"] == 1


def test_from_dict_restores_champion(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    sim.simulate_round()
    team_map = {t.name: t for t in seeds}
    restored = PlayoffSimulator.from_dict(sim.to_dict(), team_map)
    assert restored.champion.name == sim.champion.name


def test_from_dict_restores_current_round(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    team_map = {t.name: t for t in seeds}
    restored = PlayoffSimulator.from_dict(sim.to_dict(), team_map)
    assert restored.current_round == 1


def test_from_dict_restores_semifinal_results(make_team):
    seeds = _make_seeds(make_team, pts=(100.0, 90.0, 80.0, 70.0))
    sim = PlayoffSimulator(seeds)
    _noop_applier(sim)
    sim.simulate_round()
    team_map = {t.name: t for t in seeds}
    restored = PlayoffSimulator.from_dict(sim.to_dict(), team_map)
    assert len(restored.semifinal_results) == 2


def test_simulate_round_updates_injury_report(make_team):
    seeds = _make_seeds(make_team)
    sim = PlayoffSimulator(seeds)
    sim._applier.apply = lambda teams: ["Player X injured"]
    sim._applier.set_cpu_lineups = lambda teams: None
    sim.simulate_round()
    assert sim.injury_report == ["Player X injured"]
