from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

if TYPE_CHECKING:
    from diamond_draft.engine.season_simulator import SeasonSimulator
    from diamond_draft.io.save_manager import SaveManager
    from diamond_draft.models.league import League
    from diamond_draft.models.player import Player
    from diamond_draft.models.team import Team

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Colour palette — used across all screens
DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
ACCENT = "#e94560"
TEXT_PRIMARY = "#eaeaea"
TEXT_SECONDARY = "#a0a0b0"
BUTTON_BG = "#0f3460"
BUTTON_HOVER = "#c73652"


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
    waiver_available: bool = False


class App(ctk.CTk):
    """
    Root window and screen router.

    Acts as the composition root: it holds shared engine/IO objects and
    injects them into screens on demand.  Screens are CTkFrame subclasses;
    show_screen() swaps the active frame with a fade-in transition.
    """

    TITLE = "Diamond Draft"
    GEOMETRY = "1100x720"
    MIN_SIZE = (900, 600)

    def __init__(self) -> None:
        super().__init__()
        self.title(self.TITLE)
        self.geometry(self.GEOMETRY)
        self.minsize(*self.MIN_SIZE)
        self.configure(fg_color=DARK_BG)

        self._apply_theme()

        self.game = GameState()
        self._current_frame: ctk.CTkFrame | None = None

        from diamond_draft.io.save_manager import SaveManager as SM
        self.game.save_manager = SM()

        self.nav: Any = None
        self.after(0, self._boot)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(self, screen_cls: type[ctk.CTkFrame], **kwargs: Any) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        self.attributes("-alpha", 0.0)
        self._current_frame = screen_cls(self, **kwargs)
        self._current_frame.pack(fill="both", expand=True)
        self._fade_in(0.0)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fade_in(self, alpha: float) -> None:
        alpha = min(alpha + 0.1, 1.0)
        self.attributes("-alpha", alpha)
        if alpha < 1.0:
            self.after(16, self._fade_in, alpha)

    def _boot(self) -> None:
        from diamond_draft.gui.navigation import ScreenNavigator
        from diamond_draft.gui.screens.home_screen import HomeScreen

        self.nav = ScreenNavigator(self)
        self.show_screen(HomeScreen)

    def _apply_theme(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        # Treeview — used across multiple screens for data tables
        style.configure(
            "Treeview",
            background=PANEL_BG,
            foreground=TEXT_PRIMARY,
            fieldbackground=PANEL_BG,
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=BUTTON_BG,
            foreground=ACCENT,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#ffffff")],
        )
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        # Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=BUTTON_BG,
            troughcolor="#0a0d1a",
            arrowcolor=TEXT_SECONDARY,
            borderwidth=0,
            relief="flat",
        )
        style.map("Vertical.TScrollbar", background=[("active", ACCENT)])
