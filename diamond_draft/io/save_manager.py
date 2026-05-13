"""Game state persistence for Diamond Draft.

Saves and restores the full game state (teams, schedule, current week) as
a single JSON file on disk. A ``version`` field in every save file enables
forward-compatible loading and clear warnings when version mismatches occur.

Save file schema::

    {
        "version":      "1.0",
        "teams":        [...],      # Team.to_dict() for each of the 6 teams
        "schedule":     [...],      # [[Matchup.to_dict(), ...], ...]
        "current_week": 3
    }
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from diamond_draft.engine.playoff_simulator import PlayoffSimulator
from diamond_draft.engine.season_simulator import SeasonSimulator
from diamond_draft.models.league import League
from diamond_draft.models.team import Team

logger = logging.getLogger(__name__)

_SAVE_VERSION = "1.0"
"""Version tag written to every save file. Increment when the schema changes."""


class SaveManager:
    """Persist and restore the full game state as a JSON file.

    Each save occupies one file under ``save_dir``. The file name is the slot
    name with a ``.json`` extension. The default slot is ``"autosave"``, which
    is used when the user saves via the Season screen without specifying a name.

    Args:
        save_dir: Directory where save files are stored. Created automatically
            if it does not exist. Defaults to ``saves/`` in the working
            directory. Pass a custom path in tests to avoid polluting the
            project's ``saves/`` folder.
    """

    SAVE_DIR: Path = Path("saves")
    """Default save directory, relative to the current working directory."""

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
        playoff_simulator: PlayoffSimulator | None = None,
        slot: str = "autosave",
    ) -> Path:
        """Serialise the current game state and write it to *slot*.

        Args:
            teams: All six teams in the league.
            league: The current ``League`` instance (provides the schedule).
            simulator: The running ``SeasonSimulator`` (provides the week cursor).
            slot: Save slot name (file stem, no extension). Defaults to
                ``"autosave"``. Overwrites an existing file in the same slot.

        Returns:
            The absolute ``Path`` of the written save file.
        """
        state = {
            "version":      _SAVE_VERSION,
            "teams":        [t.to_dict() for t in teams],
            "schedule":     [
                [m.to_dict() for m in week]
                for week in league.schedule
            ],
            "current_week": simulator.current_week,
            "playoff":      playoff_simulator.to_dict() if playoff_simulator else None,
        }
        path = self._slot_path(slot)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        logger.info("Game saved to %s", path)
        return path

    def load(
        self, slot: str = "autosave"
    ) -> tuple[list[Team], League, int, PlayoffSimulator | None]:
        """Load a previously saved game state from *slot*.

        The caller is responsible for passing ``current_week`` to
        ``SeasonSimulator.restore_week()`` after constructing a new simulator.

        Args:
            slot: Save slot name to load. Defaults to ``"autosave"``.

        Returns:
            A 4-tuple of ``(teams, league, current_week, playoff_simulator)``.
            ``playoff_simulator`` is ``None`` when the save pre-dates playoff
            support or when no playoffs have started yet.

        Raises:
            FileNotFoundError: If no save file exists for *slot*.
        """
        path = self._slot_path(slot)
        if not path.exists():
            raise FileNotFoundError(f"No save file found at {path}.")

        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)

        self._check_version(state.get("version"))

        teams        = [Team.from_dict(d) for d in state["teams"]]
        league       = League.from_dict(state, teams)
        current_week = int(state["current_week"])

        playoff_data = state.get("playoff")
        playoff_sim: PlayoffSimulator | None = None
        if playoff_data:
            team_map   = {t.name: t for t in teams}
            playoff_sim = PlayoffSimulator.from_dict(playoff_data, team_map)

        logger.info("Game loaded from %s (week %d)", path, current_week)
        return teams, league, current_week, playoff_sim

    def list_saves(self) -> list[str]:
        """Return the names of all available save slots.

        Returns:
            Sorted list of slot name strings (file stems without ``.json``).
            Empty list when no saves exist.
        """
        return [p.stem for p in sorted(self._save_dir.glob("*.json"))]

    def delete(self, slot: str) -> None:
        """Delete the save file for *slot* if it exists.

        Args:
            slot: The save slot name to delete.
        """
        path = self._slot_path(slot)
        if path.exists():
            path.unlink()
            logger.info("Deleted save slot: %s", slot)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _slot_path(self, slot: str) -> Path:
        """Return the absolute ``Path`` for the given *slot* name.

        Args:
            slot: Save slot identifier (no extension).

        Returns:
            Path to ``<save_dir>/<slot>.json``.
        """
        return self._save_dir / f"{slot}.json"

    def _check_version(self, version: str | None) -> None:
        """Warn when the save file's version does not match the current schema.

        Loading continues after the warning — minor schema differences are
        handled by optional dict keys (``dict.get`` with defaults). A hard
        error is only raised when data is truly unreadable.

        Args:
            version: The ``"version"`` string read from the save file, or
                ``None`` if the key was absent.
        """
        if version != _SAVE_VERSION:
            logger.warning(
                "Save file version mismatch: expected %s, got %s. "
                "Loading anyway — some data may be missing.",
                _SAVE_VERSION,
                version,
            )
