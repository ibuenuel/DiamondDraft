"""Screen navigation coordinator for Diamond Draft.

Centralises all screen transitions so that individual screens never import
each other directly. This eliminates cross-screen coupling and prevents
circular-import errors — all screen class imports are deferred inside each
``to_*`` method and executed only at call time.

Usage::

    self._app.nav.to_season()
    self._app.nav.to_matchups(week_matchups)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diamond_draft.gui.app import App
    from diamond_draft.models.matchup import Matchup


class ScreenNavigator:
    """Centralise all screen transitions for the application.

    Every screen calls ``self._app.nav.to_X()`` rather than importing a
    sibling screen class directly. ``App.show_screen`` handles frame
    construction, destruction, and the fade-in animation.

    Args:
        app: The root ``App`` instance that owns the navigator.
    """

    def __init__(self, app: App) -> None:
        self._app = app

    def to_home(self) -> None:
        """Navigate to the ``HomeScreen`` (start menu)."""
        from diamond_draft.gui.screens.home_screen import HomeScreen
        self._app.show_screen(HomeScreen)

    def to_draft(self) -> None:
        """Navigate to the ``DraftScreen`` (snake draft UI)."""
        from diamond_draft.gui.screens.draft_screen import DraftScreen
        self._app.show_screen(DraftScreen)

    def to_season(self) -> None:
        """Navigate to the ``SeasonScreen`` (main season hub)."""
        from diamond_draft.gui.screens.season_screen import SeasonScreen
        self._app.show_screen(SeasonScreen)

    def to_standings(self) -> None:
        """Navigate to the ``StandingsScreen`` (league standings overview)."""
        from diamond_draft.gui.screens.standings_screen import StandingsScreen
        self._app.show_screen(StandingsScreen)

    def to_matchups(self, matchups: list[Matchup]) -> None:
        """Navigate to the ``MatchupScreen`` for the given list of matchups.

        Args:
            matchups: The list of ``Matchup`` objects for the week to display.
        """
        from diamond_draft.gui.screens.matchup_screen import MatchupScreen
        self._app.show_screen(MatchupScreen, matchups=matchups)

    def to_waiver(self) -> None:
        """Navigate to the ``WaiverScreen`` (drop / add players)."""
        from diamond_draft.gui.screens.waiver_screen import WaiverScreen
        self._app.show_screen(WaiverScreen)

    def to_lineup(self) -> None:
        """Navigate to the ``LineupScreen`` (active / bench swap)."""
        from diamond_draft.gui.screens.lineup_screen import LineupScreen
        self._app.show_screen(LineupScreen)
