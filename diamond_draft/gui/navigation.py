from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diamond_draft.gui.app import App
    from diamond_draft.models.matchup import Matchup


class ScreenNavigator:
    """
    Centralises all screen transitions for the application.

    Screens call self._app.nav.to_X() instead of importing other screen
    classes directly, which eliminates cross-screen coupling and circular-
    import risk. All screen imports remain deferred to avoid module-level
    circular dependencies.
    """

    def __init__(self, app: App) -> None:
        self._app = app

    def to_home(self) -> None:
        from diamond_draft.gui.screens.home_screen import HomeScreen
        self._app.show_screen(HomeScreen)

    def to_draft(self) -> None:
        from diamond_draft.gui.screens.draft_screen import DraftScreen
        self._app.show_screen(DraftScreen)

    def to_season(self) -> None:
        from diamond_draft.gui.screens.season_screen import SeasonScreen
        self._app.show_screen(SeasonScreen)

    def to_standings(self) -> None:
        from diamond_draft.gui.screens.standings_screen import StandingsScreen
        self._app.show_screen(StandingsScreen)

    def to_matchups(self, matchups: list[Matchup]) -> None:
        from diamond_draft.gui.screens.matchup_screen import MatchupScreen
        self._app.show_screen(MatchupScreen, matchups=matchups)

    def to_waiver(self) -> None:
        from diamond_draft.gui.screens.waiver_screen import WaiverScreen
        self._app.show_screen(WaiverScreen)
