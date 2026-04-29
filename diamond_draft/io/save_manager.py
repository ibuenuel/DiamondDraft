from __future__ import annotations

import json
import logging
from pathlib import Path

from diamond_draft.engine.season_simulator import SeasonSimulator
from diamond_draft.models.league import League
from diamond_draft.models.team import Team

logger = logging.getLogger(__name__)

_SAVE_VERSION = "1.0"


class SaveManager:
    """
    Persists and restores the full game state as a JSON file.

    Save format:
      {
        "version": "1.0",
        "teams":   [...],      # Team.to_dict() for each team
        "schedule": [...],     # week -> [Matchup.to_dict(), ...]
        "current_week": 3
      }
    """

    SAVE_DIR = Path("saves")

    def __init__(self, save_dir: Path = SAVE_DIR) -> None:
        self._save_dir = save_dir
        self._save_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        teams: list[Team],
        league: League,
        simulator: SeasonSimulator,
        slot: str = "autosave",
    ) -> Path:
        state = {
            "version": _SAVE_VERSION,
            "teams": [t.to_dict() for t in teams],
            "schedule": [
                [m.to_dict() for m in week]
                for week in league.schedule
            ],
            "current_week": simulator.current_week,
        }
        path = self._slot_path(slot)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        logger.info("Game saved to %s", path)
        return path

    def load(self, slot: str = "autosave") -> tuple[list[Team], League, int]:
        """
        Returns (teams, league, current_week).
        Caller is responsible for passing current_week to SeasonSimulator.restore_week().
        """
        path = self._slot_path(slot)
        if not path.exists():
            raise FileNotFoundError(f"No save file found at {path}.")

        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)

        self._check_version(state.get("version"))

        teams = [Team.from_dict(d) for d in state["teams"]]
        league = League.from_dict(state, teams)
        current_week = int(state["current_week"])

        logger.info("Game loaded from %s (week %d)", path, current_week)
        return teams, league, current_week

    def list_saves(self) -> list[str]:
        """Return available save slot names (without .json extension)."""
        return [p.stem for p in sorted(self._save_dir.glob("*.json"))]

    def delete(self, slot: str) -> None:
        path = self._slot_path(slot)
        if path.exists():
            path.unlink()
            logger.info("Deleted save slot: %s", slot)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _slot_path(self, slot: str) -> Path:
        return self._save_dir / f"{slot}.json"

    def _check_version(self, version: str | None) -> None:
        if version != _SAVE_VERSION:
            logger.warning(
                "Save file version mismatch: expected %s, got %s. "
                "Loading anyway — some data may be lost.",
                _SAVE_VERSION,
                version,
            )
