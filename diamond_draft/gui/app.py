from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import font as tkfont, ttk
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from diamond_draft.engine.season_simulator import SeasonSimulator
    from diamond_draft.io.save_manager import SaveManager
    from diamond_draft.models.league import League
    from diamond_draft.models.player import Player
    from diamond_draft.models.team import Team

# Colour palette
DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT = "#e94560"
TEXT_PRIMARY = "#eaeaea"
TEXT_SECONDARY = "#a0a0b0"
BUTTON_BG = "#0f3460"
BUTTON_HOVER = "#e94560"


@dataclass
class GameState:
    """Holds all mutable game data. Owned by App; injected into screens via App."""

    players: list[Player] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    league: League | None = None
    simulator: SeasonSimulator | None = None
    save_manager: SaveManager | None = None
    current_year: int = 2024
    loaded_year: int | None = None
    team_name: str = "Your Team"


class App(tk.Tk):
    """
    Root window and screen router.

    Acts as the composition root: it holds shared engine/IO objects and
    injects them into screens on demand.  Screens are plain tk.Frame
    subclasses; show_screen() swaps the active frame.
    """

    TITLE = "Diamond Draft"
    GEOMETRY = "1100x720"
    MIN_SIZE = (900, 600)

    def __init__(self) -> None:
        super().__init__()
        self.title(self.TITLE)
        self.geometry(self.GEOMETRY)
        self.minsize(*self.MIN_SIZE)
        self.configure(bg=DARK_BG)

        self._apply_theme()

        self.state = GameState()

        self._current_frame: tk.Frame | None = None

        # Initialise SaveManager at startup so all screens can use self.state.save_manager
        from diamond_draft.io.save_manager import SaveManager as SM
        self.state.save_manager = SM()

        # Navigator is created after the deferred imports to avoid circular imports
        self.nav: Any = None

        # Delay the first screen import to avoid circular import at module level
        self.after(0, self._boot)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(self, screen_cls: type[tk.Frame], **kwargs: Any) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        self._current_frame = screen_cls(self, **kwargs)
        self._current_frame.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _boot(self) -> None:
        from diamond_draft.gui.navigation import ScreenNavigator
        from diamond_draft.gui.screens.home_screen import HomeScreen

        self.nav = ScreenNavigator(self)
        self.show_screen(HomeScreen)

    def _apply_theme(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        # Treeview
        style.configure(
            "Treeview",
            background=PANEL_BG,
            foreground=TEXT_PRIMARY,
            fieldbackground=PANEL_BG,
            rowheight=26,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=BUTTON_BG,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", ACCENT)])

        # Button
        style.configure(
            "TButton",
            background=BUTTON_BG,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 10),
            padding=(10, 6),
            relief=tk.FLAT,
        )
        style.map("TButton", background=[("active", BUTTON_HOVER)])

        # Label
        style.configure(
            "TLabel",
            background=DARK_BG,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Title.TLabel",
            background=DARK_BG,
            foreground=ACCENT,
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=DARK_BG,
            foreground=TEXT_SECONDARY,
            font=("Segoe UI", 11),
        )

        # Frame
        style.configure("TFrame", background=DARK_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)

        # Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=BUTTON_BG,
            troughcolor=DARK_BG,
            arrowcolor=TEXT_PRIMARY,
        )
