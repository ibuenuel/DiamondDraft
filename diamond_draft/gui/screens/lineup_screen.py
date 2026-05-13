from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_SECONDARY, App
from diamond_draft.gui.widgets import dialog
from diamond_draft.gui.widgets.ui_helpers import (
    accent_button,
    attach_scrollbar,
    body_label,
    card_frame,
    heading,
    secondary_button,
    separator,
)
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


class LineupScreen(ctk.CTkFrame):
    """Weekly lineup manager for the human team.

    Allows the user to move players between the active lineup (11 players who
    score this week) and the bench (3 players who sit out).

    Interaction model:
    - Click a player in the Active list to select them.
    - Click a player in the Bench list to select them.
    - When one player from each list is selected, click "Swap" or click the
      opposing player to execute the swap immediately.
    - Confirm saves the lineup to the team and returns to SeasonScreen.

    Args:
        parent: The root ``App`` instance that owns this screen.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._team: Team = parent.game.teams[0]

        self._active: list[Player] = list(self._team.active_players())
        self._bench: list[Player] = list(self._team.bench_players())

        self._selected_active: Player | None = None
        self._selected_bench: Player | None = None

        self._build_ui()
        self._refresh_tables()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        sim = self._app.game.simulator
        week_label = f"Week {sim.current_week + 1}" if sim else "Lineup"
        heading(header, f"Set Lineup — {week_label}", level=1).pack(side="left")
        secondary_button(header, "Back", self._on_back, width=80).pack(side="right")

        separator(self).pack(fill="x", pady=(12, 0))

        body_label(
            self,
            "Click a player in one panel, then click a player in the other panel to swap them.",
            color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=24, pady=(8, 0))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=12)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        # Active lineup panel
        left = card_frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._active_title = ctk.StringVar()
        ctk.CTkLabel(
            left,
            textvariable=self._active_title,
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=12, pady=(12, 2))
        body_label(left, "These players score this week").pack(anchor="w", padx=12, pady=(0, 8))

        inner_left = ctk.CTkFrame(left, fg_color="transparent")
        inner_left.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._active_tree = ttk.Treeview(
            inner_left,
            columns=("pos", "name", "pts", "status"),
            show="headings",
            selectmode="browse",
        )
        for col, label, width, anchor in [
            ("pos",    "Pos",    50,  "center"),
            ("name",   "Player", 175, "w"),
            ("pts",    "Pts",    65,  "center"),
            ("status", "",       60,  "center"),
        ]:
            self._active_tree.heading(col, text=label)
            self._active_tree.column(col, width=width, anchor=anchor, stretch=col == "name")

        attach_scrollbar(self._active_tree, inner_left)
        self._active_tree.bind("<<TreeviewSelect>>", self._on_active_select)

        # Bench panel
        right = card_frame(content)
        right.grid(row=0, column=1, sticky="nsew")

        self._bench_title = ctk.StringVar()
        ctk.CTkLabel(
            right,
            textvariable=self._bench_title,
            font=("Segoe UI", 14, "bold"),
            text_color="#4caf50",
        ).pack(anchor="w", padx=12, pady=(12, 2))
        body_label(right, "These players sit out this week").pack(anchor="w", padx=12, pady=(0, 8))

        inner_right = ctk.CTkFrame(right, fg_color="transparent")
        inner_right.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._bench_tree = ttk.Treeview(
            inner_right,
            columns=("pos", "name", "pts", "status"),
            show="headings",
            selectmode="browse",
        )
        for col, label, width, anchor in [
            ("pos",    "Pos",    50,  "center"),
            ("name",   "Player", 175, "w"),
            ("pts",    "Pts",    65,  "center"),
            ("status", "",       60,  "center"),
        ]:
            self._bench_tree.heading(col, text=label)
            self._bench_tree.column(col, width=width, anchor=anchor, stretch=col == "name")

        attach_scrollbar(self._bench_tree, inner_right)
        self._bench_tree.bind("<<TreeviewSelect>>", self._on_bench_select)

        # Action bar
        action = ctk.CTkFrame(self, fg_color="transparent")
        action.pack(fill="x", padx=24, pady=(0, 16))

        self._swap_var = tk.StringVar(value="Select a player from each panel to swap")
        body_label(action, textvariable=self._swap_var, color=TEXT_SECONDARY).pack(side="left")

        accent_button(action, "Confirm Lineup", self._on_confirm, width=160).pack(side="right")

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _refresh_tables(self) -> None:
        self._active_title.set(f"Active Lineup  ({len(self._active)}/{Team.ACTIVE_SIZE})")
        self._bench_title.set(f"Bench  ({len(self._bench)}/{Team.BENCH_SPOTS})")

        self._active_tree.delete(*self._active_tree.get_children())
        for p in self._active:
            self._active_tree.insert(
                "", "end", iid=p.name,
                values=(p.position, p.name, f"{p.calculate_fantasy_points():.1f}", self._status(p)),
            )

        self._bench_tree.delete(*self._bench_tree.get_children())
        for p in self._bench:
            self._bench_tree.insert(
                "", "end", iid=p.name,
                values=(p.position, p.name, f"{p.calculate_fantasy_points():.1f}", self._status(p)),
            )

        self._selected_active = None
        self._selected_bench = None
        self._swap_var.set("Select a player from each panel to swap")

    @staticmethod
    def _status(player: Player) -> str:
        if player.injured_weeks_remaining > 0:
            return "[INJ]"
        if player.weekly_factor >= 1.15:
            return "Hot"
        if player.weekly_factor <= 0.85 and player.weekly_factor > 0:
            return "Cold"
        return ""

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_active_select(self, _event) -> None:
        sel = self._active_tree.selection()
        if not sel:
            return
        player = next((p for p in self._active if p.name == sel[0]), None)
        if player is None:
            return
        self._selected_active = player
        self._update_swap_label()
        if self._selected_bench is not None:
            self._do_swap()

    def _on_bench_select(self, _event) -> None:
        sel = self._bench_tree.selection()
        if not sel:
            return
        player = next((p for p in self._bench if p.name == sel[0]), None)
        if player is None:
            return
        self._selected_bench = player
        self._update_swap_label()
        if self._selected_active is not None:
            self._do_swap()

    def _update_swap_label(self) -> None:
        active_name = self._selected_active.name if self._selected_active else "?"
        bench_name = self._selected_bench.name if self._selected_bench else "?"
        if self._selected_active and self._selected_bench:
            self._swap_var.set(f"Swapping: {active_name} ↔ {bench_name}")
        elif self._selected_active:
            self._swap_var.set(f"Selected: {active_name} — now pick a bench player")
        else:
            self._swap_var.set(f"Selected: {bench_name} — now pick an active player")

    def _do_swap(self) -> None:
        a = self._selected_active
        b = self._selected_bench
        if a is None or b is None:
            return
        self._active.remove(a)
        self._active.append(b)
        self._bench.remove(b)
        self._bench.append(a)
        self._refresh_tables()

    def _on_confirm(self) -> None:
        if len(self._active) != Team.ACTIVE_SIZE:
            dialog.show_error(
                self,
                "Invalid Lineup",
                f"Active lineup must have exactly {Team.ACTIVE_SIZE} players.",
            )
            return
        self._team.active_lineup = list(self._active)
        dialog.show_success(self, "Lineup Set", "Your lineup has been saved for this week.")
        self._app.nav.to_season()

    def _on_back(self) -> None:
        if self._app.game.playoff_simulator is not None:
            self._app.nav.to_playoff_bracket()
        else:
            self._app.nav.to_season()
