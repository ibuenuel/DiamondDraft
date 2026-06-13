# Diamond Draft

![Tests](https://github.com/ibuenuel/DiamondDraft/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/ibuenuel/DiamondDraft/graph/badge.svg)](https://codecov.io/gh/ibuenuel/DiamondDraft)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-1f538d)

**MLB Fantasy League Simulator** — OOP Course Project (Wirtschaftsinformatik, 2026)

Diamond Draft is a local MLB Fantasy League Simulator with a graphical desktop interface.
The player drafts a team from real MLB players and competes in a simulated season against
CPU-managed teams. Scoring is based on real MLB statistics fetched via the
[MLB Stats API](https://statsapi.mlb.com) for a season year of your choice.

---

## Features

- **Snake Draft** — interactive draft against 5 CPU teams (6 teams total)
- **Real MLB Data** — season statistics via the MLB Stats API; choose any year at game start (cached locally per year after first load)
- **Standard Fantasy Scoring** — batting and pitching points per the rules below
- **10-Week Season** — weekly head-to-head matchups with live standings
- **Active Lineup Management** — set a weekly 11-player active lineup from a 14-player roster; bench players contribute no points
- **Injury System** — players have a chance to get injured each week and miss 1–2 weeks
- **Weekly Performance Variance** — healthy players receive a random performance multiplier each week (0.7×–1.3×)
- **Waiver Wire** — drop and pick up players from the free-agent pool between weeks
- **Player Detail View** — double-click any player to see full stats, headshot, team logo, and a points bar chart
- **Playoffs** — top 4 teams advance to a two-round knockout bracket (Semifinal + Final) after the regular season; animated bracket screen with score reveal and champion celebration
- **Save / Load** — full game state persisted as JSON, including mid-playoff progress
- **Desktop GUI** — built with `customtkinter` for a modern dark-themed interface with custom themed dialogs

---

## Scoring System

### Batting

```mermaid
xychart-beta
    title "Batting Points per Statistic"
    x-axis ["HR", "RBI", "Run (R)", "SB", "Hit (H)", "Strikeout (SO)"]
    y-axis "Points" -2 --> 5
    bar [4, 1, 1, 2, 1, -1]
```

### Pitching

```mermaid
xychart-beta
    title "Pitching Points per Statistic"
    x-axis ["Win (W)", "K (SO)", "IP", "Save (SV)", "ERA < 3", "Loss (L)"]
    y-axis "Points" -5 --> 5
    bar [4, 1, 1, 4, 2, -4]
```

---

## Roster Slots (per team)

Each team holds **14 players**: 11 active (scoring) and 3 bench (non-scoring).
The active lineup is set by the user each week via the Lineup screen.

```mermaid
pie title Roster Composition (14 Players Total)
    "SP — Starting Pitcher (2)" : 2
    "C — Catcher (1)" : 1
    "1B — First Baseman (1)" : 1
    "2B — Second Baseman (1)" : 1
    "3B — Third Baseman (1)" : 1
    "SS — Shortstop (1)" : 1
    "OF — Outfielder (3)" : 3
    "DH — Designated Hitter (1)" : 1
    "Bench (3)" : 3
```

---

## Project Structure

```
DiamondDraft/
├── requirements.txt
├── pyproject.toml                   # pytest configuration
│
├── tests/                           # Unit test suite (179 tests)
│   ├── conftest.py                  # Shared fixtures (player/team/league factories)
│   ├── models/
│   │   ├── test_player.py
│   │   ├── test_player_registry.py
│   │   ├── test_team.py
│   │   ├── test_matchup.py
│   │   └── test_league.py
│   └── engine/
│       ├── test_score_engine.py
│       ├── test_draft_system.py
│       ├── test_season_simulator.py
│       └── test_playoff_simulator.py
│
├── data/                            # Auto-populated on first run (gitignored)
├── saves/                           # JSON save slots (gitignored)
│
└── diamond_draft/
    ├── __main__.py                  # Entry point (python -m diamond_draft)
    ├── config.py                    # All tuneable constants, API URLs, position maps
    ├── models/
    │   ├── player.py                # Player (ABC), Batter, Pitcher
    │   ├── player_registry.py       # Registry pattern for Player deserialisation
    │   ├── team.py                  # Team with roster + active lineup management
    │   ├── matchup.py               # Weekly head-to-head matchup
    │   └── league.py                # League: teams, schedule, standings
    ├── engine/
    │   ├── score_engine.py          # Stateless fantasy point calculator
    │   ├── draft_system.py          # Snake draft logic + CPU picks
    │   ├── season_simulator.py      # Week-by-week season orchestration
    │   └── playoff_simulator.py     # Two-round knockout playoff engine
    ├── io/
    │   ├── data_loader.py           # MLB Stats API fetch + local JSON cache
    │   └── save_manager.py          # Full game state JSON persistence
    └── gui/
        ├── app.py                   # Root Tk window + GameState + screen router
        ├── navigation.py            # ScreenNavigator — centralised screen transitions
        ├── screens/
        │   ├── home_screen.py           # Start / Load / Quit
        │   ├── draft_screen.py          # Interactive snake draft
        │   ├── lineup_screen.py         # Weekly active lineup management
        │   ├── season_screen.py         # Weekly simulation controls
        │   ├── standings_screen.py      # League standings table
        │   ├── matchup_screen.py        # Per-week matchup detail
        │   ├── waiver_screen.py         # Post-week free-agent transactions
        │   └── playoff_bracket_screen.py# Animated playoff bracket UI
        └── widgets/
            ├── player_table.py      # Reusable sortable Treeview widget
            ├── player_detail_dialog.py  # Player popup: stats, headshot, bar chart
            ├── dialog.py            # Themed modal dialogs (replaces tkinter.messagebox)
            ├── help_dialog.py       # In-app baseball rules & scoring reference
            └── ui_helpers.py        # Shared CTk component factory functions
```

---

## OOP Architecture

The project is strictly object-oriented, following **DRY**, **KISS**, and **SOLID** principles.

```mermaid
flowchart LR
    GUI --> engine
    GUI --> io
    engine --> models
    io --> models
```

- **Inheritance** — `Player` is an abstract base class; `Batter` and `Pitcher` inherit from it and implement `calculate_fantasy_points()`
- **Polymorphism** — all GUI screens call `player.calculate_fantasy_points()` rather than reaching into `ScoreEngine` directly; the correct implementation is dispatched automatically
- **Registry pattern** — `player_registry.py` decouples `Player.from_dict` from concrete subclass names using `@register` / `resolve`; adding a new player type requires no changes to deserialisation code
- **DRY** — `config.py` is the single source of truth for all tuneable constants (scoring weights, API URLs, position maps, simulation parameters); `ScoreEngine` sources its values from there
- **SRP** — `DataLoader`, `SaveManager`, and `ScoreEngine` each have exactly one reason to change; `App`'s state is isolated in a `GameState` dataclass, separating window management from game logic
- **No circular imports** — `ScreenNavigator` centralises all screen transitions so screens never import each other; all dependencies flow in one direction

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/ibuenuel/DiamondDraft.git
cd DiamondDraft

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python -m diamond_draft
```

> **First run:** Select a season year on the home screen. The application fetches stats via the MLB Stats API (takes ~10–15 seconds).
> Results are cached in `data/players_YYYY.json` — selecting the same year again is instant.

---

## Tests

```bash
# Run all tests
pytest tests/

# Run with coverage report (models + engine layers)
pytest tests/ --cov=diamond_draft --cov-report=term-missing
```

```mermaid
xychart-beta
    title "Test Coverage by Layer"
    x-axis ["models/", "engine/", "config.py"]
    y-axis "Coverage %" 0 --> 100
    bar [100, 98, 100]
```

> GUI layer (`gui/`) is excluded from automated tests — requires a running Tk display.

---

## Minimum Goals (guaranteed by course end)

- [x] Load player data via MLB Stats API
- [x] Snake Draft: human picks interactively, CPU picks by stat rank
- [x] Fantasy points calculated per scoring table
- [x] 10-week season with weekly matchups
- [x] Standings updated after each week
- [x] Save / load game state (JSON)
- [x] Working desktop GUI (customtkinter)
- [x] Clean OOP structure with Batter/Pitcher inheriting from Player

## Extension Goals

- [x] Smart CPU draft (stat-prioritized picks with position-exhaustion fallback)
- [x] Waiver Wire — drop/add players between weeks
- [x] Detailed player stat view (headshot, stats table, points bar chart)
- [x] Active lineup management — set a weekly 11-player lineup from a 14-player roster
- [x] Injury system — players can miss 1–2 weeks with weekly_factor = 0
- [x] Weekly performance variance — random multiplier per player per week
- [x] Playoffs after regular season (top 4 teams) — animated bracket, score reveal, champion dialog
- [x] Unit test suite — 179 tests, 100% coverage on all models and engine layers
- [ ] Achievements / milestones
- [ ] Export season stats as CSV
- [ ] AI-Assisted Draft Assistant
- [ ] Multiplayer Support
- [ ] Mobile Port

---

## Developer

**Ismail Bünül** — OOP Course, Wirtschaftsinformatik, 2026
