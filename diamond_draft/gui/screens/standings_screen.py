from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, App
from diamond_draft.gui.widgets.player_table import PlayerTable
from diamond_draft.gui.widgets.ui_helpers import (
    card_frame,
    heading,
    secondary_button,
    separator,
)


class StandingsScreen(ctk.CTkFrame):
    """
    Full-page league standings with per-team roster detail.

    Top section: league standings table (W/L/Pts).
    Bottom section: roster view for the selected team.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._build_ui()
        self._load_standings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        heading(header, "League Standings", level=1).pack(side="left")
        secondary_button(header, "← Season", self._on_back, width=110).pack(side="right")

        separator(self).pack(fill="x", pady=(12, 0))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=16)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=0)
        content.rowconfigure(3, weight=1)

        # Standings table
        heading(content, "Standings", level=2).grid(row=0, column=0, sticky="w", pady=(0, 6))

        standings_card = card_frame(content)
        standings_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        self._tree = ttk.Treeview(
            standings_card,
            columns=("pos", "team", "w", "l", "pts"),
            show="headings",
            height=7,
            selectmode="browse",
        )
        for col, label, width, anchor in [
            ("pos",  "#",           40,  "center"),
            ("team", "Team",        200, "w"),
            ("w",    "W",           70,  "center"),
            ("l",    "L",           70,  "center"),
            ("pts",  "Fantasy Pts", 110, "center"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)
        self._tree.bind("<<TreeviewSelect>>", self._on_team_select)
        self._tree.pack(fill="x", padx=8, pady=8)

        # Roster detail
        heading(content, "Team Roster", level=2).grid(row=2, column=0, sticky="w", pady=(0, 6))

        roster_card = card_frame(content)
        roster_card.grid(row=3, column=0, sticky="nsew")

        self._roster_table = PlayerTable(roster_card)
        vsb = ttk.Scrollbar(
            roster_card, orient="vertical", command=self._roster_table.yview
        )
        self._roster_table.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._roster_table.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_standings(self) -> None:
        for row in self._app.game.league.get_standings():
            team_obj = next(
                t for t in self._app.game.teams if t.name == row["team"]
            )
            tag = "human" if team_obj.is_human else ""
            self._tree.insert(
                "",
                "end",
                iid=row["team"],
                values=("", row["team"], row["wins"], row["losses"], row["points"]),
                tags=(tag,),
            )
        self._tree.tag_configure("human", foreground=ACCENT)

        for pos, row_id in enumerate(self._tree.get_children(), start=1):
            self._tree.set(row_id, "pos", pos)

        first = self._tree.get_children()
        if first:
            self._tree.selection_set(first[0])

    def _on_team_select(self, _event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        team_name = sel[0]
        team = next(t for t in self._app.game.teams if t.name == team_name)
        self._roster_table.load(team.roster)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        self._app.nav.to_season()
