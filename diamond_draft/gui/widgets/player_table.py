from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.player import Player


class PlayerTable(ttk.Treeview):
    """
    A sortable Treeview that displays a list of Player objects.

    Columns displayed: Rank, Name, Team, Pos, Fantasy Pts, and one
    stat column per player type (auto-detected from the loaded player list).
    Clicking a column header toggles ascending/descending sort.
    """

    _BASE_COLUMNS = ("#", "name", "mlb_team", "position", "pts")
    _COLUMN_LABELS = {
        "#": "#",
        "name": "Name",
        "mlb_team": "Team",
        "position": "Pos",
        "pts": "Pts",
    }

    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[Player], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, show="headings", selectmode="browse", **kwargs)
        self._players: list[Player] = []
        self._on_select = on_select
        self._sort_col: str = "pts"
        self._sort_asc: bool = False

        self._setup_columns()
        self._setup_bindings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, players: list[Player]) -> None:
        self._players = list(players)
        self._refresh()

    def get_selected(self) -> Player | None:
        sel = self.selection()
        if not sel:
            return None
        name = self.item(sel[0], "values")[1]  # values: (#, name, team, pos, pts)
        return next((p for p in self._players if p.name == name), None)

    def clear(self) -> None:
        self.delete(*self.get_children())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _setup_columns(self) -> None:
        self["columns"] = self._BASE_COLUMNS
        col_config = {
            "#":        (40,  tk.CENTER, False),
            "name":     (180, tk.W,      True),
            "mlb_team": (70,  tk.CENTER, False),
            "position": (50,  tk.CENTER, False),
            "pts":      (70,  tk.CENTER, False),
        }
        for col in self._BASE_COLUMNS:
            width, anchor, stretch = col_config[col]
            self.heading(col, text=self._COLUMN_LABELS[col], command=lambda c=col: self._sort_by(c))
            self.column(col, anchor=anchor, width=width, stretch=stretch)

    def _setup_bindings(self) -> None:
        if self._on_select:
            self.bind("<<TreeviewSelect>>", self._on_treeview_select)

    def _on_treeview_select(self, _event) -> None:
        player = self.get_selected()
        if player and self._on_select:
            self._on_select(player)

    def _refresh(self) -> None:
        self.delete(*self.get_children())
        if self._sort_col == "pts":
            key = ScoreEngine.score
            reverse = not self._sort_asc
        else:
            key = lambda p: getattr(p, self._sort_col, "")  # noqa: E731
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
        if self._sort_col == column:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = column
            self._sort_asc = column != "pts"  # pts default desc; others default asc
        self._refresh()
