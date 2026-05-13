"""Root window, colour palette, and mutable game state for Diamond Draft.

This module is the composition root of the application. It defines:

- **Colour palette constants** — imported by every screen and widget.
- **GameState** — a plain dataclass that holds all mutable runtime data.
  Owned by ``App`` and passed to screens by reference.
- **App** — the ``CTk`` root window that owns ``GameState``,
  ``ScreenNavigator``, and ``SaveManager``. Responsible for screen routing
  and the fade-in transition.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import TYPE_CHECKING, Any

import customtkinter as ctk

if TYPE_CHECKING:
    from diamond_draft.engine.playoff_simulator import PlayoffSimulator
    from diamond_draft.engine.season_simulator import SeasonSimulator
    from diamond_draft.io.save_manager import SaveManager
    from diamond_draft.models.league import League
    from diamond_draft.models.player import Player
    from diamond_draft.models.team import Team

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ---------------------------------------------------------------------------
# Application colour palette
# All screens and widgets import these constants rather than hard-coding hex
# values, so the entire theme can be updated by changing these six lines.
# ---------------------------------------------------------------------------

DARK_BG        = "#1a1a2e"
"""Deepest background colour — used for the root window and screen backgrounds."""

PANEL_BG       = "#16213e"
"""Panel / card background — slightly lighter than DARK_BG for contrast."""

ACCENT         = "#e94560"
"""Brand accent colour — used for headings, selection highlights, and CTA buttons."""

TEXT_PRIMARY   = "#eaeaea"
"""Primary text colour — used for labels, headings, and readable body text."""

TEXT_SECONDARY = "#a0a0b0"
"""Secondary / muted text colour — used for hints, subtitles, and less important labels."""

BUTTON_BG      = "#0f3460"
"""Default button background — secondary / navigation buttons."""

BUTTON_HOVER   = "#c73652"
"""Hover colour for primary (accent) buttons."""


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Mutable runtime data for the current game session.

    Owned exclusively by ``App`` and passed to screens as ``self._app.game``.
    Screens read and write fields directly; no accessor methods are needed
    because ``GameState`` has no invariants to enforce.

    Attributes:
        players: The full pool of draftable ``Player`` objects loaded by
            ``DataLoader``. Populated before the draft screen is shown.
        teams: All six ``Team`` objects created at the start of the draft.
        league: The current ``League`` instance. ``None`` before the draft.
        simulator: The running ``SeasonSimulator``. ``None`` before the draft.
        save_manager: The ``SaveManager`` instance. Set during ``App.__init__``.
        current_year: The MLB season year currently selected by the user.
        loaded_year: The season year whose player data is currently in memory.
            ``None`` until the first successful data load.
        team_name: The display name the user chose for their team.
        waiver_available: ``True`` between weeks (after a simulated week and
            before the next), indicating the waiver wire is open.
    """

    players:           list[Player]            = field(default_factory=list)
    teams:             list[Team]              = field(default_factory=list)
    league:            League | None           = None
    simulator:         SeasonSimulator | None  = None
    playoff_simulator: PlayoffSimulator | None = None
    save_manager:      SaveManager | None      = None
    current_year:      int                     = 2024
    loaded_year:       int | None              = None
    team_name:         str                     = "Your Team"
    waiver_available:  bool                    = False


# ---------------------------------------------------------------------------
# Root window
# ---------------------------------------------------------------------------

class App(ctk.CTk):
    """Root CustomTkinter window and screen router.

    Acts as the composition root: it instantiates ``GameState``,
    ``SaveManager``, and ``ScreenNavigator``, then injects itself into every
    screen so they can access shared state via ``self._app.game``.

    Screens are ``CTkFrame`` subclasses. ``show_screen`` destroys the current
    frame, constructs the new one, and fades in via a short opacity animation.

    Attributes:
        game: The single ``GameState`` instance shared by all screens.
        nav: The ``ScreenNavigator`` instance. Set during ``_boot``.
    """

    TITLE:    str        = "Diamond Draft"
    GEOMETRY: str        = "1100x720"
    MIN_SIZE: tuple[int, int] = (900, 600)

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
        # Defer boot to the first idle cycle so the window is fully initialised
        # before the first screen is constructed.
        self.after(0, self._boot)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(self, screen_cls: type[ctk.CTkFrame], **kwargs: Any) -> None:
        """Destroy the current screen, construct *screen_cls*, and fade in.

        Args:
            screen_cls: The ``CTkFrame`` subclass to instantiate.
            **kwargs: Additional keyword arguments forwarded to *screen_cls*.
        """
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
        """Incrementally raise window opacity from *alpha* to 1.0.

        Steps the opacity by 0.1 every 16 ms (~60 fps) for a smooth entrance.

        Args:
            alpha: Current opacity level (0.0–1.0).
        """
        alpha = min(alpha + 0.1, 1.0)
        self.attributes("-alpha", alpha)
        if alpha < 1.0:
            self.after(16, self._fade_in, alpha)

    def _boot(self) -> None:
        """Initialise the navigator and show the home screen.

        Deferred from ``__init__`` via ``after(0, ...)`` to ensure the Tk
        event loop is running before any screen widgets are constructed.
        """
        from diamond_draft.gui.navigation import ScreenNavigator
        from diamond_draft.gui.screens.home_screen import HomeScreen

        self.nav = ScreenNavigator(self)
        self.show_screen(HomeScreen)

    def _apply_theme(self) -> None:
        """Configure the global ``ttk.Style`` for Treeview and Scrollbar widgets.

        Called once during ``__init__``. Applies the dark colour palette to
        all ``ttk.Treeview`` and ``ttk.Scrollbar`` instances throughout the
        application, providing a consistent look without repeating style calls
        in every screen.
        """
        style = ttk.Style(self)
        style.theme_use("clam")

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

        style.configure(
            "Vertical.TScrollbar",
            background=BUTTON_BG,
            troughcolor="#0a0d1a",
            arrowcolor=TEXT_SECONDARY,
            borderwidth=0,
            relief="flat",
        )
        style.map("Vertical.TScrollbar", background=[("active", ACCENT)])
