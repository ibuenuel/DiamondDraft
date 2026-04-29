# Diamond Draft

**MLB Fantasy League Simulator** — OOP Course Project (Wirtschaftsinformatik, 2026)

Diamond Draft is a local MLB Fantasy League Simulator with a graphical desktop interface.
The player drafts a team from real MLB players and competes in a simulated season against
CPU-managed teams. Scoring is based on actual 2024 MLB statistics fetched via
[pybaseball](https://github.com/jldbc/pybaseball).

---

## Features

- **Snake Draft** — interactive draft against 5 CPU teams (6 teams total)
- **Real MLB Data** — 2024 season statistics via pybaseball (cached locally after first load)
- **Standard Fantasy Scoring** — batting and pitching points per the rules below
- **10-Week Season** — weekly head-to-head matchups with live standings
- **Save / Load** — full game state persisted as JSON
- **Desktop GUI** — built with Python's standard `tkinter` library

---

## Scoring System

### Batting

| Statistic       | Points |
|-----------------|--------|
| Home Run (HR)   | +4     |
| RBI             | +1     |
| Run (R)         | +1     |
| Stolen Base (SB)| +2     |
| Hit (H)         | +1     |
| Strikeout (SO)  | −1     |

### Pitching

| Statistic             | Points |
|-----------------------|--------|
| Win (W)               | +4     |
| Strikeout (SO)        | +1     |
| Inning Pitched (IP)   | +1     |
| Save (SV)             | +4     |
| ERA < 3.00 (bonus)    | +2     |
| Loss (L)              | −4     |

---

## Roster Slots (per team)

| Position           | Slots |
|--------------------|-------|
| Starting Pitcher (SP) | 2  |
| Catcher (C)           | 1  |
| First Baseman (1B)    | 1  |
| Second Baseman (2B)   | 1  |
| Third Baseman (3B)    | 1  |
| Shortstop (SS)        | 1  |
| Outfielder (OF)       | 3  |
| Designated Hitter (DH)| 1  |
| **Total**             | **11** |

---

## Project Structure

```
DiamondDraft/
├── main.py                          # Entry point
├── requirements.txt
│
├── data/                            # Auto-populated on first run (gitignored)
├── saves/                           # JSON save slots (gitignored)
│
└── diamond_draft/
    ├── models/
    │   ├── player.py                # Player (ABC), Batter, Pitcher
    │   ├── team.py                  # Team with roster management
    │   ├── matchup.py               # Weekly head-to-head matchup
    │   └── league.py                # League: teams, schedule, standings
    ├── engine/
    │   ├── score_engine.py          # Stateless fantasy point calculator
    │   ├── draft_system.py          # Snake draft logic + CPU picks
    │   └── season_simulator.py      # Week-by-week season orchestration
    ├── io/
    │   ├── data_loader.py           # pybaseball fetch + local JSON cache
    │   └── save_manager.py          # Full game state JSON persistence
    └── gui/
        ├── app.py                   # Root Tk window + screen router
        ├── screens/
        │   ├── home_screen.py       # Start / Load / Quit
        │   ├── draft_screen.py      # Interactive snake draft
        │   ├── season_screen.py     # Weekly simulation controls
        │   ├── standings_screen.py  # League standings table
        │   └── matchup_screen.py    # Per-week matchup detail
        └── widgets/
            └── player_table.py      # Reusable sortable Treeview widget
```

---

## OOP Architecture

The project is strictly object-oriented, following **DRY**, **KISS**, and **SOLID** principles.

```
GUI  →  engine  →  models
 |          |
 └──  io  ──┘  →  models
```

- `Player` is an abstract base class; `Batter` and `Pitcher` inherit from it (**Inheritance**)
- `ScoreEngine` is the single source of truth for all scoring constants (**DRY**)
- `App` (tkinter root) acts as the **composition root**, injecting dependencies into screens
- `DataLoader`, `SaveManager`, `ScoreEngine` each have exactly one reason to change (**SRP**)
- No circular imports — dependencies flow in one direction only

---

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd DiamondDraft

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
```

> **First run:** The application fetches 2024 MLB stats via pybaseball (takes ~10–15 seconds).
> Results are cached in `data/players_2024.json` — all subsequent launches are instant.

---

## Minimum Goals (guaranteed by course end)

- [x] Load player data via pybaseball
- [x] Snake Draft: human picks interactively, CPU picks by stat rank
- [x] Fantasy points calculated per scoring table
- [x] 10-week season with weekly matchups
- [x] Standings updated after each week
- [x] Save / load game state (JSON)
- [x] Working tkinter GUI
- [x] Clean OOP structure with Batter/Pitcher inheriting from Player

## Extension Goals

- [ ] Smart CPU draft (stat-prioritized picks)
- [ ] Trade / Waiver Wire between weeks
- [ ] Detailed player stat view in GUI
- [ ] Playoffs after regular season (top 4 teams)
- [ ] Achievements / milestones
- [ ] Export season stats as CSV

---

## Developer

**Ismail Bünül** — OOP Course, Wirtschaftsinformatik, 2026
