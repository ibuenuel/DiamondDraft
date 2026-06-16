"""Unit tests for DraftSystem (snake draft engine)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from diamond_draft.engine.draft_system import DraftSystem
from diamond_draft.models.team import Team


# ---------------------------------------------------------------------------
# Helper: build a small draft with N teams and a minimal pool
# ---------------------------------------------------------------------------

def _make_small_draft(make_team, make_batter, make_pitcher, n_teams=6, pool=None):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(n_teams)]
    if pool is None:
        # enough players for a full draft (n_teams × 14)
        pool = []
        for i in range(n_teams * Team.MAX_ROSTER_SIZE):
            pos = "SP" if i % 14 < 2 else "OF"
            if pos == "SP":
                pool.append(make_pitcher(name=f"Draft{i}", position="SP",
                                          stats={"W": 20 - i % 20, "SO": 200, "IP": 180,
                                                 "SV": 0, "L": 5}))
            else:
                pool.append(make_batter(name=f"Draft{i}", position="OF",
                                         stats={"HR": 40 - i % 40, "RBI": 50, "R": 40,
                                                "SB": 5, "H": 100, "SO": 80}))
    return DraftSystem(teams=teams, player_pool=pool), teams, pool


# ---------------------------------------------------------------------------
# _build_snake_order
# ---------------------------------------------------------------------------

def test_build_snake_order_two_teams():
    """2 teams, 14 rounds → [0,1, 1,0, 0,1, ...]"""
    from diamond_draft.models.team import Team as T
    teams = [object(), object()]  # stubs
    # Patch MAX_ROSTER_SIZE temporarily to 2 rounds for readability
    original = T.MAX_ROSTER_SIZE
    T.MAX_ROSTER_SIZE = 2
    try:
        from diamond_draft.engine.score_engine import ScoreEngine
        draft = DraftSystem.__new__(DraftSystem)
        draft._teams = teams
        draft._available = []
        draft._current_pick = 0
        draft._pick_sequence = draft._build_snake_order()
        assert draft._pick_sequence == [0, 1, 1, 0]
    finally:
        T.MAX_ROSTER_SIZE = original


def test_build_snake_order_three_teams():
    from diamond_draft.models.team import Team as T
    teams = [object(), object(), object()]
    original = T.MAX_ROSTER_SIZE
    T.MAX_ROSTER_SIZE = 2
    try:
        draft = DraftSystem.__new__(DraftSystem)
        draft._teams = teams
        draft._available = []
        draft._current_pick = 0
        draft._pick_sequence = draft._build_snake_order()
        assert draft._pick_sequence == [0, 1, 2, 2, 1, 0]
    finally:
        T.MAX_ROSTER_SIZE = original


def test_build_snake_order_length(make_team, make_batter, make_pitcher, player_pool):
    draft, teams, _ = _make_small_draft(make_team, make_batter, make_pitcher, pool=player_pool)
    assert draft.total_picks == 6 * Team.MAX_ROSTER_SIZE


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def test_current_team_is_human_at_start(make_team, make_batter, make_pitcher, player_pool):
    draft, teams, _ = _make_small_draft(make_team, make_batter, make_pitcher, pool=player_pool)
    assert draft.current_team.is_human is True


def test_current_pick_number_starts_at_1(make_team, make_batter, make_pitcher, player_pool):
    draft, _, _ = _make_small_draft(make_team, make_batter, make_pitcher, pool=player_pool)
    assert draft.current_pick_number == 1


def test_is_complete_false_at_start(make_team, make_batter, make_pitcher, player_pool):
    draft, _, _ = _make_small_draft(make_team, make_batter, make_pitcher, pool=player_pool)
    assert draft.is_complete is False


# ---------------------------------------------------------------------------
# available_players / available_for_position
# ---------------------------------------------------------------------------

def test_available_players_sorted_by_score_descending(
    make_team, make_batter, player_pool
):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    available = draft.available_players()
    scores = [p.stats.get("HR", 0) + p.stats.get("W", 0) * 4 for p in available]
    # Just verify it's sorted descending by checking no adjacent pair is out of order
    from diamond_draft.engine.score_engine import ScoreEngine
    real_scores = [ScoreEngine.score(p) for p in available]
    assert real_scores == sorted(real_scores, reverse=True)


def test_available_for_position_filters_correctly(
    make_team, make_batter, make_pitcher, player_pool
):
    teams = [make_team(name=f"T{i}") for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    sp_only = draft.available_for_position("SP")
    assert all(p.position == "SP" for p in sp_only)
    assert len(sp_only) > 0


# ---------------------------------------------------------------------------
# make_pick
# ---------------------------------------------------------------------------

def test_make_pick_removes_player_from_available(
    make_team, make_batter, make_pitcher, player_pool
):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    player = draft.available_players()[0]
    draft.make_pick(player)
    assert player not in draft._available


def test_make_pick_adds_player_to_current_team_roster(
    make_team, make_batter, make_pitcher, player_pool
):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    player = draft.available_players()[0]
    draft.make_pick(player)
    assert player in teams[0].roster


def test_make_pick_advances_pick_cursor(
    make_team, make_batter, make_pitcher, player_pool
):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    draft.make_pick(draft.available_players()[0])
    assert draft.current_pick_number == 2


def test_make_pick_unavailable_player_raises_value_error(
    make_team, make_batter, make_pitcher, player_pool
):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    ghost = make_batter(name="Ghost")  # not in pool
    with pytest.raises(ValueError, match="no longer available"):
        draft.make_pick(ghost)


def test_make_pick_wrong_position_no_force_raises_value_error(
    make_team, make_batter
):
    """make_pick raises ValueError when team.needs_position returns False."""
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(2)]
    pool = [make_batter(name=f"P{i}", position="OF") for i in range(28)]
    draft = DraftSystem(teams=teams, player_pool=pool)
    player = pool[0]
    # Simulate a full roster: patch needs_position to always return False
    teams[0].needs_position = lambda _: False
    with pytest.raises(ValueError):
        draft.make_pick(player)


def test_make_pick_wrong_position_with_force_succeeds(
    make_team, make_batter, make_pitcher
):
    teams = [make_team(name="Human", is_human=True)]
    sp_pool = [make_pitcher(name=f"SP{i}", position="SP",
                             stats={"W": 15, "SO": 200, "IP": 180, "SV": 0, "L": 5})
               for i in range(14)]
    draft = DraftSystem(teams=teams, player_pool=sp_pool)
    # Fill both SP slots normally
    draft.make_pick(draft.available_players()[0])
    draft.make_pick(draft.available_players()[0])
    # Remaining SPs don't fit a slot, but force=True should work
    draft.make_pick(draft.available_players()[0], force=True)
    assert len(teams[0].roster) == 3


def test_make_pick_after_draft_complete_raises_runtime_error(
    make_team, make_batter, make_pitcher
):
    teams = [make_team(name="Human", is_human=True)]
    pool = [make_pitcher(name=f"SP{i}", position="SP",
                          stats={"W": 15, "SO": 200, "IP": 180, "SV": 0, "L": 5})
            for i in range(Team.MAX_ROSTER_SIZE)]
    draft = DraftSystem(teams=teams, player_pool=pool)
    for _ in range(Team.MAX_ROSTER_SIZE):
        draft.make_pick(draft.available_players()[0], force=True)
    extra = make_pitcher(name="Extra", position="SP",
                          stats={"W": 1, "SO": 1, "IP": 1, "SV": 0, "L": 0})
    draft._available.append(extra)
    with pytest.raises(RuntimeError, match="complete"):
        draft.make_pick(extra)


# ---------------------------------------------------------------------------
# cpu_pick
# ---------------------------------------------------------------------------

def test_cpu_pick_returns_player(make_team, player_pool):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    # Human picks first, then cpu_pick for T1
    draft.make_pick(draft.available_players()[0])  # human picks
    player = draft.cpu_pick()
    assert player is not None
    assert player in draft._available


def test_cpu_pick_empty_pool_raises_runtime_error(make_team):
    teams = [make_team(name=f"T{i}") for i in range(2)]
    draft = DraftSystem(teams=teams, player_pool=[])
    # Manually bypass is_complete so we can call cpu_pick
    draft._current_pick = 0
    with pytest.raises(RuntimeError):
        draft.cpu_pick()


def test_cpu_pick_no_position_match_returns_best_available(make_team, player_pool):
    """cpu_pick falls back to best remaining player when no slot fits any position."""
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    # No position will match — forces the fallback path (draft_system.py:156)
    draft.current_team.needs_position = lambda pos: False
    best = draft.available_players()[0]
    result = draft.cpu_pick()
    assert result is best


# ---------------------------------------------------------------------------
# advance_cpu_turns
# ---------------------------------------------------------------------------

def test_advance_cpu_turns_stops_at_human_turn(make_team, player_pool):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    # Human picks once (pick 1, round 1)
    draft.make_pick(draft.available_players()[0])
    # Snake order for 6 teams: round 1 [0,1,2,3,4,5], round 2 [5,4,3,2,1,0]
    # After human pick, advance_cpu_turns picks T1,T2,T3,T4,T5,T5,T4,T3,T2,T1
    # before stopping at T0's turn in round 2 → 10 CPU picks
    cpu_picks = draft.advance_cpu_turns()
    assert len(cpu_picks) == 10
    assert draft.current_team.is_human is True


def test_advance_cpu_turns_does_nothing_when_draft_complete(make_team, player_pool):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    # Force-complete the draft by advancing cursor past the end
    draft._current_pick = draft.total_picks
    assert draft.is_complete is True
    result = draft.advance_cpu_turns()
    assert result == []


def test_advance_cpu_turns_returns_players_in_order(make_team, player_pool):
    teams = [make_team(name=f"T{i}", is_human=(i == 0)) for i in range(6)]
    draft = DraftSystem(teams=teams, player_pool=player_pool)
    draft.make_pick(draft.available_players()[0])  # human pick round 1
    cpu_picks = draft.advance_cpu_turns()
    assert isinstance(cpu_picks, list)
    assert all(p is not None for p in cpu_picks)
