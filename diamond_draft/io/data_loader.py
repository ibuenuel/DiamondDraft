from __future__ import annotations

import json
import logging
from pathlib import Path

from diamond_draft.models.player import Batter, Pitcher, Player

logger = logging.getLogger(__name__)

# Pybaseball column name -> our stats key
_BATTING_COL_MAP: dict[str, str] = {
    "HR": "HR",
    "RBI": "RBI",
    "R": "R",
    "SB": "SB",
    "H": "H",
    "SO": "SO",
}
_PITCHING_COL_MAP: dict[str, str] = {
    "W": "W",
    "SO": "SO",
    "IP": "IP",
    "SV": "SV",
    "ERA": "ERA",
    "L": "L",
}
# Fielding position normalisations
_OUTFIELD_POSITIONS = {"LF", "CF", "RF"}
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
      2. pybaseball live fetch (requires internet)
      3. Bundled sample data  (data/sample_players.json)
    """

    SAMPLE_PATH = Path("data/sample_players.json")

    def __init__(self, year: int = 2024, use_cache: bool = True) -> None:
        self.year = year
        self._use_cache = use_cache
        self.CACHE_PATH = Path(f"data/players_{year}.json")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> list[Player]:
        if self._use_cache and self.CACHE_PATH.exists():
            logger.info("Loading players from cache: %s", self.CACHE_PATH)
            return self._load_json(self.CACHE_PATH)

        try:
            players = self._fetch_from_pybaseball()
            self._save_cache(players)
            return players
        except Exception as exc:
            logger.debug("pybaseball fetch failed (%s); falling back to sample data.", exc)

        return self._load_sample()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_from_pybaseball(self) -> list[Player]:
        import pybaseball  # deferred — not imported at module level

        pybaseball.cache.enable()

        batting_df = pybaseball.batting_stats(self.year, qual=50)
        pitching_df = pybaseball.pitching_stats(self.year, qual=20)

        try:
            fielding_df = pybaseball.fielding_stats(self.year, qual=10)
            position_map = self._build_position_map(fielding_df)
        except Exception:
            logger.warning("fielding_stats fetch failed; using default positions.")
            position_map = {}

        batters = [
            self._build_batter(row, position_map)
            for _, row in batting_df.iterrows()
        ]
        pitchers = [
            self._build_pitcher(row)
            for _, row in pitching_df.iterrows()
        ]

        # Deduplicate: a two-way player (e.g. Ohtani) may appear in both lists.
        # Keep the pitcher entry in the pitchers list and skip in batters.
        pitcher_names = {p.name for p in pitchers}
        batters = [b for b in batters if b.name not in pitcher_names]

        return batters + pitchers

    def _build_position_map(self, fielding_df) -> dict[str, str]:
        """Map player name -> normalised position from fielding data."""
        pos_map: dict[str, str] = {}
        pos_col = "Pos" if "Pos" in fielding_df.columns else "position"
        for _, row in fielding_df.iterrows():
            name = str(row.get("Name", "")).strip()
            raw_pos = str(row.get(pos_col, "")).strip().upper()
            normalised = _POSITION_NORM.get(raw_pos, raw_pos)
            if name and normalised:
                pos_map.setdefault(name, normalised)
        return pos_map

    def _build_batter(self, row, position_map: dict[str, str]) -> Batter:
        name = str(row.get("Name", "Unknown")).strip()
        team = str(row.get("Team", "???")).strip()
        position = position_map.get(name, "OF")  # default to OF if unknown
        if position not in Batter.POSITIONS:
            position = "OF"

        stats = {
            key: float(row.get(col, 0) or 0)
            for col, key in _BATTING_COL_MAP.items()
        }
        return Batter(name=name, mlb_team=team, position=position, stats=stats)

    def _build_pitcher(self, row) -> Pitcher:
        name = str(row.get("Name", "Unknown")).strip()
        team = str(row.get("Team", "???")).strip()
        stats = {
            key: float(row.get(col, 0) or 0)
            for col, key in _PITCHING_COL_MAP.items()
        }
        return Pitcher(name=name, mlb_team=team, position="SP", stats=stats)

    # ------------------------------------------------------------------
    # Cache / sample I/O
    # ------------------------------------------------------------------

    def _save_cache(self, players: list[Player]) -> None:
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump([p.to_dict() for p in players], fh, indent=2)
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
