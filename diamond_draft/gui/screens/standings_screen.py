from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from diamond_draft.gui.app import DARK_BG, PANEL_BG, TEXT_PRIMARY, App
from diamond_draft.gui.widgets.player_table import PlayerTable


class StandingsScreen(tk.Frame):
    """
    Full-page league standings with per-team roster detail.

    Top section: league standings table (W/L/Pts).
    Bottom section: roster view for the selected team.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, bg=DARK_BG)
        self._app = parent
        self._build_ui()
        self._load_standings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=DARK_BG, pady=12)
        header.pack(fill=tk.X, padx=20)

        ttk.Label(header, text="League Standings", style="Title.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Button(
            header, text="← Season", command=self._on_back
        ).pack(side=tk.RIGHT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        content = tk.Frame(self, bg=DARK_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        # Standings table
        ttk.Label(content, text="Standings", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )

        self._tree = ttk.Treeview(
            content,
            columns=("pos", "team", "w", "l", "pts"),
            show="headings",
            height=7,
            selectmode="browse",
        )
        for col, label, width in [
            ("pos", "#", 40),
            ("team", "Team", 160),
            ("w", "W", 60),
            ("l", "L", 60),
            ("pts", "Fantasy Pts", 100),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=tk.CENTER)
        self._tree.column("team", anchor=tk.W)
        self._tree.bind("<<TreeviewSelect>>", self._on_team_select)
        self._tree.grid(row=1, column=0, sticky="ew", pady=(4, 16))

        # Roster detail
        ttk.Label(content, text="Team Roster", style="Subtitle.TLabel").grid(
            row=2, column=0, sticky=tk.W
        )

        roster_frame = tk.Frame(content, bg=PANEL_BG)
        roster_frame.grid(row=3, column=0, sticky="nsew", pady=(4, 0))
        content.rowconfigure(3, weight=1)

        self._roster_table = PlayerTable(roster_frame)
        vsb = ttk.Scrollbar(
            roster_frame, orient=tk.VERTICAL, command=self._roster_table.yview
        )
        self._roster_table.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._roster_table.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_standings(self) -> None:
        for row in self._app.league.get_standings():
            team_obj = next(
                t for t in self._app.teams if t.name == row["team"]
            )
            tag = "human" if team_obj.is_human else ""
            self._tree.insert(
                "",
                tk.END,
                iid=row["team"],
                values=("", row["team"], row["wins"], row["losses"], row["points"]),
                tags=(tag,),
            )
        # Highlight human team
        self._tree.tag_configure("human", foreground="#e94560")

        # Number the rows
        for pos, row_id in enumerate(self._tree.get_children(), start=1):
            self._tree.set(row_id, "pos", pos)

        # Auto-select first row
        first = self._tree.get_children()
        if first:
            self._tree.selection_set(first[0])

    def _on_team_select(self, _event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        team_name = sel[0]
        team = next(t for t in self._app.teams if t.name == team_name)
        self._roster_table.load(team.roster)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        from diamond_draft.gui.screens.season_screen import SeasonScreen

        self._app.show_screen(SeasonScreen)
