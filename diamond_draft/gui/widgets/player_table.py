"""Sortable player list Treeview widget for Diamond Draft.

``PlayerTable`` is a ``ttk.Treeview`` subclass that displays a ranked list of
``Player`` objects with sortable columns. The scoring function is injected via
a constructor parameter so the table can be reused in contexts where a custom
or test scorer is preferred without importing ``ScoreEngine`` directly.

The dark Treeview style is applied once per process via a module-level guard
and cached so subsequent instantiations are instant.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.gui.app import ACCENT, PANEL_BG, TEXT_PRIMARY
from diamond_draft.models.player import Player

_DARK_STYLE_APPLIED = False


def _apply_dark_treeview_style() -> None:
    """Apply the dark colour scheme to all ``ttk.Treeview`` widgets.

    Uses a module-level flag so the style is registered at most once per
    process. Tk's ``ttk.Style`` is global — calling ``configure`` repeatedly
    is harmless but unnecessary.
    """
    global _DARK_STYLE_APPLIED
    if _DARK_STYLE_APPLIED:
        return
    style = ttk.Style()
    style.configure(
        "Treeview",
        background=PANEL_BG,
        foreground=TEXT_PRIMARY,
        fieldbackground=PANEL_BG,
        rowheight=26,
        font=("Segoe UI", 11),
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background="#0f3460",
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
    )
    style.map("Treeview", background=[("selected", ACCENT)])
    _DARK_STYLE_APPLIED = True


class PlayerTable(ttk.Treeview):
    """Sortable Treeview that displays a ranked list of ``Player`` objects.

    Columns displayed: rank, name, team, position, and fantasy points. Clicking
    any column header toggles ascending/descending sort order. Double-clicking a
    row opens a ``PlayerDetailDialog`` for that player.

    Args:
        parent: The parent tk widget that contains this table.
        on_select: Optional callback invoked with the selected ``Player``
            whenever the Treeview selection changes. ``None`` disables the
            selection binding entirely.
        score_func: Callable used to sort by and display fantasy points.
            Defaults to ``ScoreEngine.score`` so call sites do not need to
            import ``ScoreEngine`` separately. Pass a custom callable in tests
            to decouple from the live scoring weights.
        **kwargs: Additional keyword arguments forwarded to
            ``ttk.Treeview.__init__``.
    """

    _BASE_COLUMNS: tuple[str, ...] = ("#", "name", "mlb_team", "position", "pts")
    _COLUMN_LABELS: dict[str, str] = {
        "#":        "#",
        "name":     "Name",
        "mlb_team": "Team",
        "position": "Pos",
        "pts":      "Pts",
    }

    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[Player], None] | None = None,
        score_func: Callable[[Player], float] = ScoreEngine.score,
        **kwargs,
    ) -> None:
        super().__init__(parent, show="headings", selectmode="browse", **kwargs)
        self._players:   list[Player] = []
        self._on_select  = on_select
        self._score_func = score_func
        self._sort_col:  str  = "pts"
        self._sort_asc:  bool = False

        _apply_dark_treeview_style()
        self._setup_columns()
        self._setup_bindings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, players: list[Player]) -> None:
        """Replace the current player list and refresh the display.

        Args:
            players: The new list of players to display. The list is copied
                internally so the caller may mutate the original safely.
        """
        self._players = list(players)
        self._refresh()

    def get_selected(self) -> Player | None:
        """Return the currently selected player, or ``None`` if nothing is selected.

        Returns:
            The ``Player`` whose name matches the selected row, or ``None``
            when the selection is empty or no matching player is found.
        """
        sel = self.selection()
        if not sel:
            return None
        # Column index 1 holds the player name — used as a stable lookup key.
        name = self.item(sel[0], "values")[1]
        return next((p for p in self._players if p.name == name), None)

    def clear(self) -> None:
        """Remove all rows from the table without modifying the internal player list."""
        self.delete(*self.get_children())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_columns(self) -> None:
        """Configure column widths, anchors, and sortable headings."""
        self["columns"] = self._BASE_COLUMNS
        col_config: dict[str, tuple[int, str, bool]] = {
            "#":        (40,  tk.CENTER, False),
            "name":     (180, tk.W,      True),
            "mlb_team": (70,  tk.CENTER, False),
            "position": (50,  tk.CENTER, False),
            "pts":      (70,  tk.CENTER, False),
        }
        for col in self._BASE_COLUMNS:
            width, anchor, stretch = col_config[col]
            self.heading(
                col,
                text=self._COLUMN_LABELS[col],
                command=lambda c=col: self._sort_by(c),
            )
            self.column(col, anchor=anchor, width=width, stretch=stretch)

    def _setup_bindings(self) -> None:
        """Bind Treeview events to their handler methods."""
        if self._on_select:
            self.bind("<<TreeviewSelect>>", self._on_treeview_select)
        self.bind("<Double-Button-1>", self._on_double_click)

    def _on_treeview_select(self, _event) -> None:
        """Forward the current selection to the ``on_select`` callback."""
        player = self.get_selected()
        if player and self._on_select:
            self._on_select(player)

    def _on_double_click(self, _event) -> None:
        """Open a ``PlayerDetailDialog`` for the double-clicked player."""
        from diamond_draft.gui.widgets.player_detail_dialog import PlayerDetailDialog

        player = self.get_selected()
        if player:
            PlayerDetailDialog(self.winfo_toplevel(), player)

    def _refresh(self) -> None:
        """Clear and repopulate the table using the current sort settings."""
        self.delete(*self.get_children())
        if self._sort_col == "pts":
            key     = self._score_func
            reverse = not self._sort_asc
        else:
            key     = lambda p: getattr(p, self._sort_col, "")  # noqa: E731
            reverse = self._sort_asc
        sorted_players = sorted(self._players, key=key, reverse=reverse)

        for rank, player in enumerate(sorted_players, start=1):
            pts = f"{player.calculate_fantasy_points():.1f}"
            self.insert(
                "",
                tk.END,
                values=(rank, player.name, player.mlb_team, player.position, pts),
            )

    def _sort_by(self, column: str) -> None:
        """Toggle sort direction when clicking the same column; reset when switching.

        Args:
            column: The column identifier that was clicked.
        """
        if self._sort_col == column:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = column
            # Fantasy points default to descending (highest first);
            # all other columns default to ascending.
            self._sort_asc = column != "pts"
        self._refresh()
