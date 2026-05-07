from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_SECONDARY, App
from diamond_draft.gui.widgets.ui_helpers import (
    accent_button,
    body_label,
    card_frame,
    heading,
    secondary_button,
    separator,
)
from diamond_draft.models.matchup import Matchup


class SeasonScreen(ctk.CTkFrame):
    """
    Main hub for the regular season.

    Shows the current week, this week's matchups (once simulated), and
    navigation to Standings.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._last_matchups: list[Matchup] = []
        self._build_ui()
        self._refresh()
        self._sync_waiver_btn()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        self._title_var = tk.StringVar()
        ctk.CTkLabel(
            header,
            textvariable=self._title_var,
            font=("Segoe UI", 22, "bold"),
            text_color=ACCENT,
        ).pack(side="left")

        secondary_button(header, "Standings", self._on_standings, width=110).pack(side="right", padx=(6, 0))
        secondary_button(header, "Save Game", self._on_save, width=110).pack(side="right", padx=(0, 6))
        secondary_button(header, "Help", self._on_help, width=70).pack(side="right", padx=(0, 6))

        separator(self).pack(fill="x", pady=(12, 0))

        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=16)

        # Matchup preview card
        heading(content, "This Week's Matchups", level=2).pack(anchor="w", pady=(0, 6))
        self._matchup_card = card_frame(content)
        self._matchup_card.pack(fill="x", pady=(0, 16))

        # Standings mini-table card
        heading(content, "Current Standings", level=2).pack(anchor="w", pady=(0, 6))
        standings_card = card_frame(content)
        standings_card.pack(fill="x")

        self._standings_tree = ttk.Treeview(
            standings_card,
            columns=("pos", "team", "w", "l", "pts"),
            show="headings",
            height=6,
            selectmode="none",
        )
        for col, label, width, anchor in [
            ("pos",  "#",    40,  "center"),
            ("team", "Team", 200, "w"),
            ("w",    "W",    60,  "center"),
            ("l",    "L",    60,  "center"),
            ("pts",  "Pts",  90,  "center"),
        ]:
            self._standings_tree.heading(col, text=label)
            self._standings_tree.column(col, width=width, anchor=anchor)
        self._standings_tree.pack(fill="x", padx=8, pady=8)

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(0, 16))

        self._sim_btn = accent_button(footer, "Simulate Next Week", self._on_simulate, width=200)
        self._sim_btn.pack(side="left")

        self._result_btn = secondary_button(
            footer, "View Week Results", self._on_view_results, width=160
        )
        self._result_btn.configure(state="disabled")
        self._result_btn.pack(side="left", padx=(12, 0))

        self._waiver_btn = secondary_button(footer, "Waiver Wire", self._on_waiver, width=130)
        self._waiver_btn.configure(state="disabled")
        self._waiver_btn.pack(side="left", padx=(12, 0))

        self._status_var = tk.StringVar()
        body_label(footer, textvariable=self._status_var).pack(side="left", padx=16)

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        sim = self._app.game.simulator
        week = sim.current_week
        remaining = sim.weeks_remaining

        if sim.is_complete:
            self._title_var.set("Season Complete!")
            self._sim_btn.configure(state="disabled")
            self._status_var.set("The season is over. Check the final standings!")
        else:
            self._title_var.set(f"Season — Week {week + 1} of {sim.total_weeks}")
            self._status_var.set(f"{remaining} week(s) remaining")

        self._refresh_standings()
        self._refresh_matchup_preview()

    def _refresh_standings(self) -> None:
        self._standings_tree.delete(*self._standings_tree.get_children())
        for pos, row in enumerate(self._app.game.league.get_standings(), start=1):
            self._standings_tree.insert(
                "",
                "end",
                values=(pos, row["team"], row["wins"], row["losses"], row["points"]),
            )

    def _refresh_matchup_preview(self) -> None:
        for w in self._matchup_card.winfo_children():
            w.destroy()

        if not self._last_matchups:
            body_label(
                self._matchup_card,
                "Simulate a week to see matchup results here.",
            ).pack(anchor="w", padx=12, pady=12)
            return

        for m in self._last_matchups:
            s = m.summary()
            line = (
                f"  {s['home']}  {s['home_points']:.1f}  vs  "
                f"{s['away_points']:.1f}  {s['away']}   —  Winner: {s['winner']}"
            )
            body_label(self._matchup_card, line).pack(anchor="w", padx=12, pady=3)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_simulate(self) -> None:
        sim = self._app.game.simulator
        if sim.is_complete:
            return
        self._last_matchups = sim.simulate_week()
        self._result_btn.configure(state="normal")
        if not sim.is_complete:
            self._app.game.waiver_available = True
        self._refresh()
        self._sync_waiver_btn()

    def _on_waiver(self) -> None:
        self._app.nav.to_waiver()

    def _sync_waiver_btn(self) -> None:
        state = "normal" if self._app.game.waiver_available else "disabled"
        self._waiver_btn.configure(state=state)

    def _on_view_results(self) -> None:
        if not self._last_matchups:
            return
        self._app.nav.to_matchups(self._last_matchups)

    def _on_help(self) -> None:
        from diamond_draft.gui.widgets.help_dialog import open_help
        open_help(self._app)

    def _on_standings(self) -> None:
        self._app.nav.to_standings()

    def _on_save(self) -> None:
        sm = self._app.game.save_manager
        path = sm.save(
            teams=self._app.game.teams,
            league=self._app.game.league,
            simulator=self._app.game.simulator,
            slot="autosave",
        )
        messagebox.showinfo("Saved", f"Game saved to {path.name}")
