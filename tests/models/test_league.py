"""Unit tests for the League model."""
from __future__ import annotations

from collections import Counter

import pytest

from diamond_draft.models.league import League
from diamond_draft.models.matchup import Matchup


# ---------------------------------------------------------------------------
# Class-level constants
# ---------------------------------------------------------------------------

def test_league_team_count_is_6():
    assert League.TEAM_COUNT == 6


def test_league_weeks_is_10():
    assert League.WEEKS == 10


# ---------------------------------------------------------------------------
# generate_schedule()
# ---------------------------------------------------------------------------

def test_generate_schedule_produces_10_weeks(league_with_schedule):
    assert len(league_with_schedule.schedule) == 10


def test_generate_schedule_produces_3_matchups_per_week(league_with_schedule):
    for week in league_with_schedule.schedule:
        assert len(week) == 3


def test_generate_schedule_no_team_plays_itself(league_with_schedule):
    for week in league_with_schedule.schedule:
        for m in week:
            assert m.home is not m.away


def test_generate_schedule_each_team_plays_10_games(league_with_schedule):
    appearances: Counter = Counter()
    for week in league_with_schedule.schedule:
        for m in week:
            appearances[m.home.name] += 1
            appearances[m.away.name] += 1
    for team in league_with_schedule.teams:
        assert appearances[team.name] == 10


def test_generate_schedule_each_pair_plays_exactly_twice(league_with_schedule):
    pair_counts: Counter = Counter()
    for week in league_with_schedule.schedule:
        for m in week:
            pair = frozenset({m.home.name, m.away.name})
            pair_counts[pair] += 1
    for count in pair_counts.values():
        assert count == 2


def test_generate_schedule_home_away_swapped_in_cycle_2(league_with_schedule):
    """For every matchup in cycle 1 (weeks 1-5), there is a reverse matchup in cycle 2 (weeks 6-10)."""
    cycle1 = league_with_schedule.schedule[:5]
    cycle2 = league_with_schedule.schedule[5:]

    # Build {frozenset(a,b): (home, away)} for each cycle
    def pair_map(weeks):
        m = {}
        for week in weeks:
            for matchup in week:
                key = frozenset({matchup.home.name, matchup.away.name})
                m[key] = (matchup.home.name, matchup.away.name)
        return m

    map1 = pair_map(cycle1)
    map2 = pair_map(cycle2)

    for pair_key in map1:
        h1, a1 = map1[pair_key]
        h2, a2 = map2[pair_key]
        # Home/away should be swapped
        assert h1 == a2
        assert a1 == h2


def test_generate_schedule_week_numbers_are_sequential(league_with_schedule):
    for week_idx, week in enumerate(league_with_schedule.schedule):
        for m in week:
            assert m.week == week_idx + 1


# ---------------------------------------------------------------------------
# update_standings()
# ---------------------------------------------------------------------------

def test_update_standings_increments_winner_wins(league_with_schedule):
    m = league_with_schedule.schedule[0][0]
    home, away = m.home, m.away
    home.total_points = lambda: 100.0
    away.total_points = lambda: 80.0
    league_with_schedule.update_standings(m)
    assert home.wins == 1
    assert away.losses == 1


def test_update_standings_increments_loser_losses(league_with_schedule):
    m = league_with_schedule.schedule[0][0]
    home, away = m.home, m.away
    home.total_points = lambda: 50.0
    away.total_points = lambda: 90.0
    league_with_schedule.update_standings(m)
    assert away.wins == 1
    assert home.losses == 1


def test_update_standings_tie_does_not_change_records(league_with_schedule):
    m = league_with_schedule.schedule[0][0]
    home, away = m.home, m.away
    home.total_points = lambda: 75.0
    away.total_points = lambda: 75.0
    league_with_schedule.update_standings(m)
    assert home.wins == 0
    assert home.losses == 0
    assert away.wins == 0
    assert away.losses == 0


# ---------------------------------------------------------------------------
# get_standings()
# ---------------------------------------------------------------------------

def test_get_standings_sorted_by_wins_descending(league_with_schedule):
    teams = league_with_schedule.teams
    for i, t in enumerate(teams):
        t.wins = len(teams) - i  # descending wins
        t.total_points = lambda v=float(i): v
    standings = league_with_schedule.get_standings()
    wins = [row["wins"] for row in standings]
    assert wins == sorted(wins, reverse=True)


def test_get_standings_tiebreak_by_points(league_with_schedule):
    t1, t2 = league_with_schedule.teams[0], league_with_schedule.teams[1]
    t1.wins = t2.wins = 5
    t1.total_points = lambda: 200.0
    t2.total_points = lambda: 100.0
    standings = league_with_schedule.get_standings()
    # t1 has more points → ranked higher
    top_names = [row["team"] for row in standings[:2]]
    assert top_names[0] == t1.name


def test_get_standings_contains_required_keys(league_with_schedule):
    standings = league_with_schedule.get_standings()
    for row in standings:
        for key in ("team", "wins", "losses", "points"):
            assert key in row


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def test_to_dict_and_from_dict_round_trip(league_with_schedule):
    data = league_with_schedule.to_dict()
    teams = league_with_schedule.teams
    restored = League.from_dict(data, teams)
    assert len(restored.schedule) == 10
    for w_orig, w_rest in zip(league_with_schedule.schedule, restored.schedule):
        for m_orig, m_rest in zip(w_orig, w_rest):
            assert m_orig.week == m_rest.week
            assert m_orig.home.name == m_rest.home.name
            assert m_orig.away.name == m_rest.away.name


def test_from_dict_links_matchups_to_correct_team_objects(league_with_schedule):
    data = league_with_schedule.to_dict()
    teams = league_with_schedule.teams
    team_map = {t.name: t for t in teams}
    restored = League.from_dict(data, teams)
    for week in restored.schedule:
        for m in week:
            assert m.home is team_map[m.home.name]
            assert m.away is team_map[m.away.name]
