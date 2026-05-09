from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY, App
from diamond_draft.gui.widgets.player_table import PlayerTable
from diamond_draft.gui.widgets.ui_helpers import (
    accent_button,
    body_label,
    card_frame,
    heading,
    secondary_button,
    separator,
)
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


class WaiverScreen(ctk.CTkFrame):
    """
    Waiver Wire screen — lets the human team drop one roster player and
    pick up one free-agent replacement after each simulated week.

    Rules enforced:
    - Available players are filtered to the same position as the dropped player.
    - Exactly one drop + one add per visit (or the user skips with no changes).
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._human_team: Team = parent.game.teams[0]
        self._waiver_pool: list[Player] = self._compute_waiver_pool()

        self._drop_player: Player | None = None
        self._add_player: Player | None = None

        self._build_ui()
        self._load_roster()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        sim = self._app.game.simulator
        week_label = f"Week {sim.current_week}" if sim else "Waiver Wire"
        heading(header, f"Waiver Wire — {week_label}", level=1).pack(side="left")
        secondary_button(header, "Skip (No Changes)", self._on_skip, width=160).pack(side="right")

        separator(self).pack(fill="x", pady=(12, 0))

        # Main content — two panels side by side
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=12)
        content.columnconfigure(0, weight=2)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        # Left: your roster
        left = card_frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        heading(left, "Your Roster", level=2).pack(anchor="w", padx=12, pady=(12, 2))
        body_label(left, "Select a player to DROP").pack(anchor="w", padx=12, pady=(0, 8))

        roster_inner = ctk.CTkFrame(left, fg_color="transparent")
        roster_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._roster_tree = ttk.Treeview(
            roster_inner,
            columns=("pos", "name", "pts"),
            show="headings",
            selectmode="browse",
        )
        self._roster_tree.heading("pos",  text="Pos")
        self._roster_tree.heading("name", text="Player")
        self._roster_tree.heading("pts",  text="Pts")
        self._roster_tree.column("pos",  width=50,  anchor="center", stretch=False)
        self._roster_tree.column("name", width=180, anchor="w")
        self._roster_tree.column("pts",  width=65,  anchor="center", stretch=False)

        vsb_left = ttk.Scrollbar(roster_inner, orient="vertical", command=self._roster_tree.yview)
        self._roster_tree.configure(yscrollcommand=vsb_left.set)
        vsb_left.pack(side="right", fill="y")
        self._roster_tree.pack(fill="both", expand=True)
        self._roster_tree.bind("<<TreeviewSelect>>", self._on_roster_select)

        # Right: available waiver players
        right = card_frame(content)
        right.grid(row=0, column=1, sticky="nsew")

        heading(right, "Available Players", level=2).pack(anchor="w", padx=12, pady=(12, 2))
        self._avail_label = body_label(right, "Select a player to DROP first")
        self._avail_label.pack(anchor="w", padx=12, pady=(0, 8))

        table_inner = ctk.CTkFrame(right, fg_color="transparent")
        table_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._waiver_table = PlayerTable(table_inner, on_select=self._on_waiver_select)
        vsb_right = ttk.Scrollbar(table_inner, orient="vertical", command=self._waiver_table.yview)
        self._waiver_table.configure(yscrollcommand=vsb_right.set)
        vsb_right.pack(side="right", fill="y")
        self._waiver_table.pack(fill="both", expand=True)

        # Action bar
        action = ctk.CTkFrame(self, fg_color="transparent")
        action.pack(fill="x", padx=24, pady=(0, 16))

        self._drop_var = tk.StringVar(value="Drop:  —")
        self._add_var  = tk.StringVar(value="Add:  —")

        body_label(action, textvariable=self._drop_var, color=ACCENT).pack(side="left")
        body_label(action, " → ").pack(side="left")
        body_label(action, textvariable=self._add_var, color="#4caf50").pack(side="left")

        self._confirm_btn = accent_button(
            action, "Confirm Trade", self._on_confirm, width=150
        )
        self._confirm_btn.configure(state="disabled")
        self._confirm_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _compute_waiver_pool(self) -> list[Player]:
        rostered = {p.name for team in self._app.game.teams for p in team.roster}
        return [p for p in self._app.game.players if p.name not in rostered]

    def _load_roster(self) -> None:
        self._roster_tree.delete(*self._roster_tree.get_children())
        for player in sorted(
            self._human_team.roster,
            key=lambda p: p.calculate_fantasy_points(),
            reverse=True,
        ):
            pts = f"{player.calculate_fantasy_points():.1f}"
            inj_suffix = " [INJ]" if player.injured_weeks_remaining > 0 else ""
            self._roster_tree.insert(
                "", "end", iid=player.name,
                values=(player.position, player.name + inj_suffix, pts),
            )

    def _filter_waiver_by_position(self, position: str) -> None:
        filtered = [p for p in self._waiver_pool if p.position == position]
        self._waiver_table.load(filtered)
        self._avail_label.configure(
            text=f"Position: {position}  —  {len(filtered)} available"
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_roster_select(self, _event) -> None:
        sel = self._roster_tree.selection()
        if not sel:
            return
        player_name = sel[0]
        player = next((p for p in self._human_team.roster if p.name == player_name), None)
        if player is None:
            return

        self._drop_player = player
        self._add_player = None
        self._drop_var.set(f"Drop:  {player.name}  ({player.position})")
        self._add_var.set("Add:  —")
        self._confirm_btn.configure(state="disabled")

        self._roster_tree.tag_configure("drop", foreground=ACCENT)
        for iid in self._roster_tree.get_children():
            self._roster_tree.item(iid, tags=())
        self._roster_tree.item(player.name, tags=("drop",))

        self._filter_waiver_by_position(player.position)

    def _on_waiver_select(self, player: Player) -> None:
        if self._drop_player is None:
            return
        self._add_player = player
        self._add_var.set(f"Add:  {player.name}  ({player.position})")
        self._confirm_btn.configure(state="normal")

    def _on_confirm(self) -> None:
        if self._drop_player is None or self._add_player is None:
            return

        self._human_team.roster.remove(self._drop_player)
        self._human_team.roster.append(self._add_player)
        self._app.game.waiver_available = False

        messagebox.showinfo(
            "Trade Complete",
            f"Dropped  {self._drop_player.name}\n"
            f"Added    {self._add_player.name}",
        )
        self._app.nav.to_season()

    def _on_skip(self) -> None:
        self._app.game.waiver_available = False
        self._app.nav.to_season()
