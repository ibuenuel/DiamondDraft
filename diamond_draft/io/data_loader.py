"""MLB player data loading with a three-tier fallback strategy.

Resolution order (first success wins):
    1. **Local JSON cache** — ``data/players_<year>.json``, written after any
       successful live fetch so subsequent runs are instant and offline-capable.
    2. **MLB Stats API live fetch** — requires internet access; fetches both
       batting and pitching splits for the requested season year.
    3. **Bundled sample data** — ``data/sample_players.json`` shipped with the
       application; guarantees the app is always usable even without a network.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from diamond_draft import config
from diamond_draft.models.player import Batter, Pitcher, Player

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR     = _PROJECT_ROOT / "data"

# Positions that must be present in the player pool for a valid 6-team draft.
_REQUIRED_POSITIONS: frozenset[str] = frozenset({"C", "1B", "2B", "3B", "SS", "DH"})


class DataLoader:
    """Load MLB player data for a given season year and return ``Player`` objects.

    The loader is fully stateless after construction — call ``load()`` once and
    discard the instance. All file-system paths are derived from *year* at
    construction time so that multiple loaders for different seasons can coexist.

    Args:
        year: The MLB season year to load (e.g. ``2024``). Must be one of the
            years listed in ``config.AVAILABLE_YEARS``.
        use_cache: When ``True`` (default), a pre-existing cache file is used
            instead of hitting the live API. Set to ``False`` to force a
            network refresh.
    """

    SAMPLE_PATH: Path = _DATA_DIR / "sample_players.json"
    """Absolute path to the bundled fallback player dataset."""

    def __init__(self, year: int = config.DEFAULT_YEAR, use_cache: bool = True) -> None:
        self.year = year
        self._use_cache  = use_cache
        self.CACHE_PATH: Path = _DATA_DIR / f"players_{year}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> tuple[list[Player], str]:
        """Load players using the three-tier fallback strategy.

        Returns:
            A 2-tuple of ``(players, source)`` where *source* is one of
            ``"cache"``, ``"live"``, or ``"sample"``. The source string is
            displayed in the UI loading status bar.

        Raises:
            FileNotFoundError: If all three fallback tiers fail (no cache,
                no network, and no bundled sample data found on disk).
        """
        if self._use_cache and self.CACHE_PATH.exists():
            logger.info("Loading players from cache: %s", self.CACHE_PATH)
            return self._load_json(self.CACHE_PATH), "cache"

        try:
            players = self._fetch_from_mlb_api()
            self._save_cache(players)
            return players, "live"
        except (requests.RequestException, ValueError, KeyError, RuntimeError) as exc:
            logger.warning("MLB Stats API fetch failed: %s", exc, exc_info=True)

        logger.warning("Falling back to bundled sample data for %d.", self.year)
        return self._load_sample(), "sample"

    # ------------------------------------------------------------------
    # Private helpers — API fetch
    # ------------------------------------------------------------------

    def _fetch_from_mlb_api(self) -> list[Player]:
        """Fetch both batting and pitching groups from the MLB Stats API.

        Filters out pitchers who appear in the batting group (two-way players
        can appear in both; keep them only as pitchers to avoid duplicate IDs).

        Returns:
            Combined, deduplicated list of ``Batter`` and ``Pitcher`` objects.

        Raises:
            RuntimeError: If the resulting pool is missing any required position.
        """
        batters  = self._fetch_group("hitting")
        pitchers = self._fetch_group("pitching")
        # Remove two-way players from the batter list — they are already
        # represented as pitchers and would otherwise be draftable twice.
        pitcher_names = {p.name for p in pitchers}
        batters  = [b for b in batters if b.name not in pitcher_names]
        players  = batters + pitchers
        self._validate_positions(players)
        return players

    def _fetch_group(self, group: str) -> list[Player]:
        """Fetch one stat group ("hitting" or "pitching") from the MLB Stats API.

        Uses ``playerPool=all`` rather than ``playerPool=qualified`` to avoid
        the plate-appearance threshold that would exclude most catchers from
        the results. The limit is applied client-side via the API ``limit``
        parameter defined in ``config``.

        Args:
            group: Either ``"hitting"`` or ``"pitching"``.

        Returns:
            A list of ``Batter`` or ``Pitcher`` objects built from the API
            response splits.

        Raises:
            requests.RequestException: On any network or HTTP error.
            KeyError: If the API response schema differs from what is expected.
        """
        url = (
            f"{config.MLB_API_BASE_URL}/stats"
            f"?stats=season&group={group}&season={self.year}"
            f"&playerPool=all&limit={config.QUALIFIED_PLAYER_LIMIT}"
        )
        resp = requests.get(url, timeout=config.MLB_API_TIMEOUT)
        resp.raise_for_status()
        splits = resp.json()["stats"][0]["splits"]
        if group == "hitting":
            return [self._build_batter(s) for s in splits]
        return [self._build_pitcher(s) for s in splits]

    def _build_batter(self, split: dict) -> Batter:
        """Construct a ``Batter`` from a single MLB Stats API hitting split.

        Normalises the position code using ``config.POSITION_ALIASES`` and
        falls back to ``"OF"`` for any position code not in ``Batter.POSITIONS``
        (rare edge cases from the API returning unexpected codes).

        Args:
            split: A single element from the ``stats[0].splits`` list in the
                API JSON response.

        Returns:
            A fully constructed ``Batter`` instance.
        """
        name   = split["player"]["fullName"]
        team   = split["team"]["name"]
        mlb_id = int(split["player"]["id"])
        pos    = config.POSITION_ALIASES.get(
            split["position"]["abbreviation"],
            split["position"]["abbreviation"],
        )
        if pos not in Batter.POSITIONS:
            pos = "OF"
        s = split["stat"]
        stats = {
            "HR":  float(s.get("homeRuns",     0)),
            "RBI": float(s.get("rbi",          0)),
            "R":   float(s.get("runs",         0)),
            "SB":  float(s.get("stolenBases",  0)),
            "H":   float(s.get("hits",         0)),
            "SO":  float(s.get("strikeOuts",   0)),
        }
        return Batter(name=name, mlb_team=team, position=pos, stats=stats, mlb_id=mlb_id)

    def _build_pitcher(self, split: dict) -> Pitcher:
        """Construct a ``Pitcher`` from a single MLB Stats API pitching split.

        All pitchers are assigned position ``"SP"`` regardless of their API
        role code; the draft system handles SP/RP slot assignment separately.

        Args:
            split: A single element from the ``stats[0].splits`` list in the
                API JSON response.

        Returns:
            A fully constructed ``Pitcher`` instance.
        """
        name   = split["player"]["fullName"]
        team   = split["team"]["name"]
        mlb_id = int(split["player"]["id"])
        s      = split["stat"]
        stats  = {
            "W":   float(s.get("wins",           0)),
            "SO":  float(s.get("strikeOuts",     0)),
            "IP":  float(s.get("inningsPitched", 0)),
            "SV":  float(s.get("saves",          0)),
            "ERA": float(s.get("era",            0)),
            "L":   float(s.get("losses",         0)),
        }
        return Pitcher(name=name, mlb_team=team, position="SP", stats=stats, mlb_id=mlb_id)

    def _validate_positions(self, players: list[Player]) -> None:
        """Verify that the player pool covers every required roster position.

        Args:
            players: The combined player list to validate.

        Raises:
            RuntimeError: If any required position is missing. The message
                names the missing positions so the fallback logic can log it.
        """
        positions = {p.position for p in players}
        missing   = _REQUIRED_POSITIONS - positions
        if missing:
            raise RuntimeError(
                f"Player pool is missing required positions: {missing}. "
                "Falling back to sample data."
            )

    # ------------------------------------------------------------------
    # Private helpers — cache / sample I/O
    # ------------------------------------------------------------------

    def _save_cache(self, players: list[Player]) -> None:
        """Serialise *players* to the local JSON cache file.

        Creates parent directories as needed so the ``data/`` folder does not
        have to exist before the first run.

        Args:
            players: The player list to persist.
        """
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump([p.to_dict() for p in players], fh, indent=2, ensure_ascii=False)
        logger.info("Cached %d players to %s", len(players), self.CACHE_PATH)

    def _load_json(self, path: Path) -> list[Player]:
        """Deserialise a JSON player file from *path*.

        Args:
            path: Absolute path to a JSON file containing a list of player
                dicts (format produced by ``Player.to_dict``).

        Returns:
            A list of ``Player`` subclass instances.
        """
        with open(path, encoding="utf-8") as fh:
            return [Player.from_dict(d) for d in json.load(fh)]

    def _load_sample(self) -> list[Player]:
        """Load the bundled sample player dataset shipped with the application.

        Returns:
            A list of ``Player`` subclass instances from the sample file.

        Raises:
            FileNotFoundError: If the sample file is missing from the
                installation directory. This should never happen in a
                correctly packaged release.
        """
        if not self.SAMPLE_PATH.exists():
            raise FileNotFoundError(
                f"No network, no cache, and no sample data found at "
                f"{self.SAMPLE_PATH}. Run the app with an active internet "
                "connection at least once to populate the cache."
            )
        logger.info("Loading bundled sample data from %s", self.SAMPLE_PATH)
        return self._load_json(self.SAMPLE_PATH)
