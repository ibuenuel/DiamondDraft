"""Unit tests for SeasonSimulator and _WeeklyFactorApplier."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from diamond_draft.engine.season_simulator import SeasonSimulator, _WeeklyFactorApplier
from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.league import League


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_team_with_roster(make_team, make_batter, name="T", n=3, is_human=False):
    t = make_team(name=name, is_human=is_human)
    for i in range(n):
        t.roster.append(make_batter(name=f"{name}_P{i}"))
    return t


def _patch_random(monkeypatch, random_val=0.99, uniform_val=1.1, randint_val=1):
    """Patch all random calls in season_simulator module."""
    import diamond_draft.engine.season_simulator as mod
    monkeypatch.setattr(mod.random, "random", lambda: random_val)
    monkeypatch.setattr(mod.random, "uniform", lambda a, b: uniform_val)
    monkeypatch.setattr(mod.random, "randint", lambda a, b: randint_val)


# ===========================================================================
# _WeeklyFactorApplier
# ===========================================================================

class TestWeeklyFactorApplier:

    def test_healthy_player_gets_uniform_factor(self, monkeypatch, make_team, make_batter):
        _patch_random(monkeypatch, random_val=0.99, uniform_val=1.1)
        t = _make_team_with_roster(make_team, make_batter, n=1)
        applier = _WeeklyFactorApplier(ScoreEngine)
        applier.apply([t])
        assert t.roster[0].weekly_factor == pytest.approx(1.1)

    def test_healthy_player_injury_chance_triggers_injury(self, monkeypatch, make_team, make_batter):
        _patch_random(monkeypatch, random_val=0.01, randint_val=2)  # < INJURY_CHANCE
        t = _make_team_with_roster(make_team, make_batter, n=1)
        applier = _WeeklyFactorApplier(ScoreEngine)
        applier.apply([t])
        assert t.roster[0].weekly_factor == pytest.approx(0.0)
        assert t.roster[0].injured_weeks_remaining == 2

    def test_apply_returns_injury_report_for_newly_injured(self, monkeypatch, make_team, make_batter):
        _patch_random(monkeypatch, random_val=0.01, randint_val=1)
        t = _make_team_with_roster(make_team, make_batter, n=1)
        applier = _WeeklyFactorApplier(ScoreEngine)
        report = applier.apply([t])
        assert len(report) == 1
        assert t.roster[0].name in report[0]

    def test_apply_injury_report_empty_when_no_injuries(self, monkeypatch, make_team, make_batter):
        _patch_random(monkeypatch, random_val=0.99)
        t = _make_team_with_roster(make_team, make_batter, n=3)
        applier = _WeeklyFactorApplier(ScoreEngine)
        report = applier.apply([t])
        assert report == []

    def test_already_injured_player_decrements_counter(self, monkeypatch, make_team, make_batter):
        _patch_random(monkeypatch, random_val=0.99)  # no new injuries
        t = make_team(name="T")
        p = make_batter(name="Hurt", injured_weeks_remaining=2)
        t.roster.append(p)
        applier = _WeeklyFactorApplier(ScoreEngine)
        applier.apply([t])
        assert p.injured_weeks_remaining == 1
        assert p.weekly_factor == pytest.approx(0.0)

    def test_already_injured_player_does_not_reroll_injury(self, monkeypatch, make_team, make_batter):
        # Even if random.random() < INJURY_CHANCE, already-injured player must not re-roll
        _patch_random(monkeypatch, random_val=0.01, randint_val=2)
        t = make_team(name="T")
        p = make_batter(name="Hurt", injured_weeks_remaining=1)
        t.roster.append(p)
        applier = _WeeklyFactorApplier(ScoreEngine)
        applier.apply([t])
        assert p.injured_weeks_remaining == 0  # decremented, not re-assigned
        assert p.weekly_factor == pytest.approx(0.0)

    def test_apply_processes_all_teams_all_players(self, monkeypatch, make_team, make_batter):
        _patch_random(monkeypatch, random_val=0.99, uniform_val=1.2)
        t1 = _make_team_with_roster(make_team, make_batter, name="T1", n=3)
        t2 = _make_team_with_roster(make_team, make_batter, name="T2", n=3)
        applier = _WeeklyFactorApplier(ScoreEngine)
        applier.apply([t1, t2])
        for team in [t1, t2]:
            for p in team.roster:
                assert p.weekly_factor == pytest.approx(1.2)

    def test_set_cpu_lineups_ignores_human_team(self, make_team, make_batter):
        human = _make_team_with_roster(make_team, make_batter, name="Human",
                                        n=Team_size(), is_human=True)
        human.active_lineup = []  # empty to detect if changed
        applier = _WeeklyFactorApplier(ScoreEngine)
        applier.set_cpu_lineups([human])
        assert human.active_lineup == []

    def test_set_cpu_lineups_sets_top_scorers_for_cpu(self, make_team, make_batter):
        from diamond_draft.models.team import Team
        cpu = make_team(name="CPU", is_human=False)
        # 14 players with distinct scores
        players = [make_batter(name=f"P{i}", stats={"HR": i}) for i in range(14)]
        for p in players:
            cpu.roster.append(p)

        scores_map = {p.name: float(i) for i, p in enumerate(players)}
        with patch("diamond_draft.engine.score_engine.ScoreEngine.score",
                   side_effect=lambda p: scores_map[p.name]):
            applier = _WeeklyFactorApplier(ScoreEngine)
            applier.set_cpu_lineups([cpu])

        assert len(cpu.active_lineup) == Team.ACTIVE_SIZE
        # Top 11 players are P3..P13
        lineup_names = {p.name for p in cpu.active_lineup}
        for i in range(3, 14):
            assert f"P{i}" in lineup_names


def Team_size():
    from diamond_draft.models.team import Team
    return Team.ACTIVE_SIZE


# ===========================================================================
# SeasonSimulator
# ===========================================================================

class TestSeasonSimulator:

    def _make_sim(self, league_with_schedule):
        return SeasonSimulator(league=league_with_schedule)

    # --- Properties ---

    def test_initial_current_week_is_zero(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        assert sim.current_week == 0

    def test_total_weeks_is_10(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        assert sim.total_weeks == 10

    def test_is_complete_false_at_start(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        assert sim.is_complete is False

    def test_is_complete_true_at_week_10(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.current_week = 10
        assert sim.is_complete is True

    def test_weeks_remaining_starts_at_10(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        assert sim.weeks_remaining == 10

    def test_weeks_remaining_decrements_with_week(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.current_week = 3
        assert sim.weeks_remaining == 7

    def test_weeks_remaining_never_negative(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.current_week = 99
        assert sim.weeks_remaining == 0

    # --- simulate_week ---

    def test_simulate_week_increments_current_week(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with patch.object(sim._applier, "apply", return_value=[]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            sim.simulate_week()
        assert sim.current_week == 1

    def test_simulate_week_returns_three_matchups(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with patch.object(sim._applier, "apply", return_value=[]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            matchups = sim.simulate_week()
        assert len(matchups) == 3

    def test_simulate_week_calls_update_standings(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with patch.object(sim._applier, "apply", return_value=[]), \
             patch.object(sim._applier, "set_cpu_lineups"), \
             patch.object(league_with_schedule, "update_standings") as mock_update:
            sim.simulate_week()
        assert mock_update.call_count == 3

    def test_simulate_week_when_complete_raises_runtime_error(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.current_week = 10
        with pytest.raises(RuntimeError, match="complete"):
            sim.simulate_week()

    def test_simulate_week_sets_injury_report(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with patch.object(sim._applier, "apply", return_value=["Player X injured"]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            sim.simulate_week()
        assert sim.injury_report == ["Player X injured"]

    def test_injury_report_reset_each_week(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with patch.object(sim._applier, "apply", return_value=["Injury"]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            sim.simulate_week()
        with patch.object(sim._applier, "apply", return_value=[]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            sim.simulate_week()
        assert sim.injury_report == []

    # --- simulate_all ---

    def test_simulate_all_plays_all_remaining_weeks(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with patch.object(sim._applier, "apply", return_value=[]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            results = sim.simulate_all()
        assert len(results) == 10
        assert sim.is_complete

    def test_simulate_all_from_week_5_plays_5_more(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.current_week = 5
        with patch.object(sim._applier, "apply", return_value=[]), \
             patch.object(sim._applier, "set_cpu_lineups"):
            results = sim.simulate_all()
        assert len(results) == 5
        assert sim.current_week == 10

    # --- restore_week ---

    def test_restore_week_sets_current_week(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.restore_week(5)
        assert sim.current_week == 5

    def test_restore_week_zero_is_valid(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.restore_week(0)
        assert sim.current_week == 0

    def test_restore_week_10_is_valid(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.restore_week(10)
        assert sim.current_week == 10

    def test_restore_week_negative_raises_value_error(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with pytest.raises(ValueError):
            sim.restore_week(-1)

    def test_restore_week_11_raises_value_error(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        with pytest.raises(ValueError):
            sim.restore_week(11)

    # --- to_dict ---

    def test_to_dict_contains_current_week(self, league_with_schedule):
        sim = self._make_sim(league_with_schedule)
        sim.current_week = 7
        assert sim.to_dict() == {"current_week": 7}
