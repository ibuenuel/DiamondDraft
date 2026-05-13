"""Application-wide constants for Diamond Draft.

All tuneable values, API endpoints, position mappings, and display labels
live here. No other module should define constants that govern game rules,
API configuration, or UI parameters — import from this module instead.

Adding a new tunable value:
    1. Define it here with a ``Final`` type annotation.
    2. Add a one-line docstring comment explaining its purpose and units.
    3. Import ``config`` in the consuming module and reference ``config.X``.
"""
from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Season configuration
# ---------------------------------------------------------------------------

AVAILABLE_YEARS: Final[list[int]] = [2022, 2023, 2024, 2025]
"""MLB seasons available for player data loading."""

DEFAULT_YEAR: Final[int] = 2024
"""Pre-selected year shown when opening the New Game dialog."""

# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------

INJURY_CHANCE: Final[float] = 0.08
"""Probability (0–1) that a healthy player becomes injured at the start of a week."""

INJURY_MIN_WEEKS: Final[int] = 1
"""Minimum number of weeks an injured player misses (weekly_factor = 0)."""

INJURY_MAX_WEEKS: Final[int] = 2
"""Maximum number of weeks an injured player misses."""

VARIANCE_MIN: Final[float] = 0.7
"""Lower bound of the random weekly performance multiplier for healthy players."""

VARIANCE_MAX: Final[float] = 1.3
"""Upper bound of the random weekly performance multiplier for healthy players."""

# ---------------------------------------------------------------------------
# MLB Stats API
# ---------------------------------------------------------------------------

MLB_API_BASE_URL: Final[str] = "https://statsapi.mlb.com/api/v1"
"""Root URL for the official MLB Stats REST API (v1)."""

MLB_API_TIMEOUT: Final[int] = 15
"""Request timeout in seconds for all outbound MLB API calls."""

QUALIFIED_PLAYER_LIMIT: Final[int] = 500
"""Maximum players fetched per stat group.

Using ``playerPool=all`` avoids the plate-appearance threshold that would
otherwise exclude most catchers and part-time players from the results.
"""

# ---------------------------------------------------------------------------
# Position normalisation
# ---------------------------------------------------------------------------

POSITION_ALIASES: Final[dict[str, str]] = {
    "LF": "OF",
    "CF": "OF",
    "RF": "OF",
    "P":  "SP",
}
"""Map non-standard position codes returned by the MLB API to canonical ones.

The MLB API occasionally returns outfield sub-positions (LF, CF, RF) and the
generic pitcher code (P). Normalise these before constructing player objects
so the rest of the application only ever deals with the canonical set.
"""

# ---------------------------------------------------------------------------
# Player image / logo endpoints
# ---------------------------------------------------------------------------

HEADSHOT_URL_TEMPLATES: Final[list[str]] = [
    "https://securea.mlb.com/mlb/images/players/head_shot/{}.jpg",
    "https://midfield.mlbstatic.com/v1/people/{}/spots/spot-120.jpg",
]
"""Ordered list of headshot URL templates.

Each template must contain exactly one ``{}`` placeholder for the MLB person ID.
The fetcher tries them in order and falls back to the next on any network or
HTTP error.
"""

TEAM_LOGO_URL_TEMPLATE: Final[str] = (
    "https://a.espncdn.com/i/teamlogos/mlb/500/{}.png"
)
"""ESPN CDN team logo template. ``{}`` is replaced with the ESPN abbreviation."""

MLB_PEOPLE_SEARCH_URL: Final[str] = (
    "https://statsapi.mlb.com/api/v1/people/search?names={}&sportId=1"
)
"""MLB Stats API people-search endpoint. ``{}`` is replaced with the URL-encoded player name."""

# ---------------------------------------------------------------------------
# Team ESPN abbreviation map
# ---------------------------------------------------------------------------

TEAM_ESPN_ABBREV: Final[dict[str, str]] = {
    "Arizona Diamondbacks":  "ari",
    "Atlanta Braves":        "atl",
    "Baltimore Orioles":     "bal",
    "Boston Red Sox":        "bos",
    "Chicago Cubs":          "chc",
    "Chicago White Sox":     "cws",
    "Cincinnati Reds":       "cin",
    "Cleveland Guardians":   "cle",
    "Colorado Rockies":      "col",
    "Detroit Tigers":        "det",
    "Houston Astros":        "hou",
    "Kansas City Royals":    "kc",
    "Los Angeles Angels":    "laa",
    "Los Angeles Dodgers":   "lad",
    "Miami Marlins":         "mia",
    "Milwaukee Brewers":     "mil",
    "Minnesota Twins":       "min",
    "New York Mets":         "nym",
    "New York Yankees":      "nyy",
    "Oakland Athletics":     "oak",
    "Philadelphia Phillies": "phi",
    "Pittsburgh Pirates":    "pit",
    "San Diego Padres":      "sd",
    "San Francisco Giants":  "sf",
    "Seattle Mariners":      "sea",
    "St. Louis Cardinals":   "stl",
    "Tampa Bay Rays":        "tb",
    "Texas Rangers":         "tex",
    "Toronto Blue Jays":     "tor",
    "Washington Nationals":  "wsh",
    # Relocated franchise alias — keep both keys so old save files still resolve.
    "Athletics":             "oak",
}
"""Map from full MLB franchise name to ESPN CDN logo abbreviation.

Used by PlayerDetailDialog to construct the team logo URL. Keys match the
``mlb_team`` field stored on Player objects (sourced from the MLB Stats API).
"""

# ---------------------------------------------------------------------------
# Stat display labels
# ---------------------------------------------------------------------------

BATTING_STAT_LABELS: Final[dict[str, str]] = {
    "HR":  "Home Runs",
    "RBI": "Runs Batted In",
    "R":   "Runs",
    "SB":  "Stolen Bases",
    "H":   "Hits",
    "SO":  "Strikeouts",
}
"""Human-readable labels for batter stat keys shown in PlayerDetailDialog."""

PITCHING_STAT_LABELS: Final[dict[str, str]] = {
    "W":   "Wins",
    "SO":  "Strikeouts",
    "IP":  "Innings Pitched",
    "SV":  "Saves",
    "L":   "Losses",
}
"""Human-readable labels for pitcher stat keys shown in PlayerDetailDialog."""

# ---------------------------------------------------------------------------
# CPU draft team names
# ---------------------------------------------------------------------------

CPU_TEAM_NAMES: Final[list[str]] = [
    "Yankees",
    "Red Sox",
    "Dodgers",
    "Cubs",
    "Cardinals",
]
"""Display names assigned to the five CPU-controlled teams during the snake draft."""
