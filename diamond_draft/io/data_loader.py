from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from diamond_draft.models.player import Batter, Pitcher, Player

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _PROJECT_ROOT / "data"

_BASE_URL = "https://statsapi.mlb.com/api/v1"

_POSITION_NORM: dict[str, str] = {
    "LF": "OF",
    "CF": "OF",
    "RF": "OF",
    "P": "SP",
}


class DataLoader:
    """
    Loads MLB player data for a given season year and returns a list of Player objects.

    Resolution order:
      1. Local JSON cache  (data/players_YYYY.json)
      2. MLB Stats API live fetch (requires internet)
      3. Bundled sample data  (data/sample_players.json)
    """

    SAMPLE_PATH = _DATA_DIR / "sample_players.json"

    def __init__(self, year: int = 2024, use_cache: bool = True) -> None:
        self.year = year
        self._use_cache = use_cache
        self.CACHE_PATH = _DATA_DIR / f"players_{year}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> tuple[list[Player], str]:
        """Returns (players, source) where source is 'cache', 'live', or 'sample'."""
        if self._use_cache and self.CACHE_PATH.exists():
            logger.info("Loading players from cache: %s", self.CACHE_PATH)
            return self._load_json(self.CACHE_PATH), "cache"

        try:
            players = self._fetch_from_mlb_api()
            self._save_cache(players)
            return players, "live"
        except Exception as exc:
            logger.warning("MLB Stats API fetch failed: %s", exc, exc_info=True)

        logger.warning("Falling back to bundled sample data for %d.", self.year)
        return self._load_sample(), "sample"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_from_mlb_api(self) -> list[Player]:
        batters = self._fetch_group("hitting")
        pitchers = self._fetch_group("pitching")
        pitcher_names = {p.name for p in pitchers}
        batters = [b for b in batters if b.name not in pitcher_names]
        players = batters + pitchers
        self._validate_positions(players)
        return players

    def _fetch_group(self, group: str) -> list[Player]:
        url = (
            f"{_BASE_URL}/stats"
            f"?stats=season&group={group}&season={self.year}"
            f"&playerPool=qualified&limit=500"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        splits = resp.json()["stats"][0]["splits"]
        if group == "hitting":
            return [self._build_batter(s) for s in splits]
        return [self._build_pitcher(s) for s in splits]

    def _build_batter(self, split: dict) -> Batter:
        name = split["player"]["fullName"]
        team = split["team"]["name"]
        pos = _POSITION_NORM.get(
            split["position"]["abbreviation"],
            split["position"]["abbreviation"],
        )
        if pos not in Batter.POSITIONS:
            pos = "OF"
        s = split["stat"]
        stats = {
            "HR":  float(s.get("homeRuns", 0)),
            "RBI": float(s.get("rbi", 0)),
            "R":   float(s.get("runs", 0)),
            "SB":  float(s.get("stolenBases", 0)),
            "H":   float(s.get("hits", 0)),
            "SO":  float(s.get("strikeOuts", 0)),
        }
        return Batter(name=name, mlb_team=team, position=pos, stats=stats)

    def _build_pitcher(self, split: dict) -> Pitcher:
        name = split["player"]["fullName"]
        team = split["team"]["name"]
        s = split["stat"]
        stats = {
            "W":   float(s.get("wins", 0)),
            "SO":  float(s.get("strikeOuts", 0)),
            "IP":  float(s.get("inningsPitched", 0)),
            "SV":  float(s.get("saves", 0)),
            "ERA": float(s.get("era", 0)),
            "L":   float(s.get("losses", 0)),
        }
        return Pitcher(name=name, mlb_team=team, position="SP", stats=stats)

    def _validate_positions(self, players: list[Player]) -> None:
        from diamond_draft.models.team import Team
        positions = {p.position for p in players}
        required = set(Team.SLOT_REQUIREMENTS) - {"SP", "OF"}
        missing = required - positions
        if missing:
            raise RuntimeError(
                f"Player pool missing positions {missing}. "
                "Falling back to sample data."
            )

    # ------------------------------------------------------------------
    # Cache / sample I/O
    # ------------------------------------------------------------------

    def _save_cache(self, players: list[Player]) -> None:
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump([p.to_dict() for p in players], fh, indent=2, ensure_ascii=False)
        logger.info("Cached %d players to %s", len(players), self.CACHE_PATH)

    def _load_json(self, path: Path) -> list[Player]:
        with open(path, encoding="utf-8") as fh:
            return [Player.from_dict(d) for d in json.load(fh)]

    def _load_sample(self) -> list[Player]:
        if not self.SAMPLE_PATH.exists():
            raise FileNotFoundError(
                f"No network, no cache, and no sample data found at {self.SAMPLE_PATH}. "
                "Please run the app with an active internet connection at least once."
            )
        logger.info("Loading bundled sample data from %s", self.SAMPLE_PATH)
        return self._load_json(self.SAMPLE_PATH)
