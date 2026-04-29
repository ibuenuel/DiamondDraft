from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from diamond_draft.gui.app import DARK_BG, PANEL_BG, TEXT_SECONDARY, App
from diamond_draft.models.matchup import Matchup


class SeasonScreen(tk.Frame):
    """
    Main hub for the regular season.

    Shows the current week, the week's matchups (once simulated), and
    navigation to Standings.  The "Simulate Week" button runs one week;
    results open MatchupScreen for detail.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, bg=DARK_BG)
        self._app = parent
        self._last_matchups: list[Matchup] = []
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=DARK_BG, pady=12)
        header.pack(fill=tk.X, padx=20)

        self._title_var = tk.StringVar()
        ttk.Label(header, textvariable=self._title_var, style="Title.TLabel").pack(
            side=tk.LEFT
        )

        ttk.Button(
            header, text="Standings", command=self._on_standings
        ).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(
            header, text="Save Game", command=self._on_save
        ).pack(side=tk.RIGHT, padx=(0, 8))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Content
        content = tk.Frame(self, bg=DARK_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        # Matchup summary panel
        ttk.Label(content, text="This Week's Matchups", style="Subtitle.TLabel").pack(
            anchor=tk.W
        )
        self._matchup_frame = ttk.Frame(content, style="Panel.TFrame")
        self._matchup_frame.pack(fill=tk.X, pady=(4, 16))

        # Standings mini-table
        ttk.Label(content, text="Current Standings", style="Subtitle.TLabel").pack(
            anchor=tk.W
        )
        self._standings_tree = ttk.Treeview(
            content,
            columns=("pos", "team", "w", "l", "pts"),
            show="headings",
            height=6,
            selectmode="none",
        )
        for col, label, width in [
            ("pos", "#", 40),
            ("team", "Team", 160),
            ("w", "W", 50),
            ("l", "L", 50),
            ("pts", "Pts", 80),
        ]:
            self._standings_tree.heading(col, text=label)
            self._standings_tree.column(col, width=width, anchor=tk.CENTER)
        self._standings_tree.column("team", anchor=tk.W)
        self._standings_tree.pack(fill=tk.X)

        # Footer buttons
        footer = tk.Frame(self, bg=DARK_BG, pady=12)
        footer.pack(fill=tk.X, padx=20)

        self._sim_btn = ttk.Button(
            footer, text="Simulate Next Week", command=self._on_simulate
        )
        self._sim_btn.pack(side=tk.LEFT)

        self._result_btn = ttk.Button(
            footer,
            text="View Week Results",
            command=self._on_view_results,
            state=tk.DISABLED,
        )
        self._result_btn.pack(side=tk.LEFT, padx=(12, 0))

        self._status_var = tk.StringVar()
        ttk.Label(footer, textvariable=self._status_var, style="Subtitle.TLabel").pack(
            side=tk.LEFT, padx=16
        )

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        sim = self._app.simulator
        week = sim.current_week
        remaining = sim.weeks_remaining

        if sim.is_complete:
            self._title_var.set("Season Complete!")
            self._sim_btn.configure(state=tk.DISABLED)
            self._status_var.set("The season is over. Check the final standings!")
        else:
            self._title_var.set(f"Season — Week {week + 1} of {sim._league.WEEKS}")
            self._status_var.set(f"{remaining} week(s) remaining")

        self._refresh_standings()
        self._refresh_matchup_preview()

    def _refresh_standings(self) -> None:
        self._standings_tree.delete(*self._standings_tree.get_children())
        for pos, row in enumerate(self._app.league.get_standings(), start=1):
            self._standings_tree.insert(
                "",
                tk.END,
                values=(pos, row["team"], row["wins"], row["losses"], row["points"]),
            )

    def _refresh_matchup_preview(self) -> None:
        for widget in self._matchup_frame.winfo_children():
            widget.destroy()

        if not self._last_matchups:
            ttk.Label(
                self._matchup_frame,
                text="Simulate a week to see matchup results here.",
                style="Subtitle.TLabel",
            ).pack(anchor=tk.W, padx=8, pady=8)
            return

        for m in self._last_matchups:
            s = m.summary()
            line = (
                f"  {s['home']}  {s['home_points']:.1f}  vs  "
                f"{s['away_points']:.1f}  {s['away']}   —  Winner: {s['winner']}"
            )
            ttk.Label(self._matchup_frame, text=line, style="Subtitle.TLabel").pack(
                anchor=tk.W, padx=8, pady=2
            )

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_simulate(self) -> None:
        sim = self._app.simulator
        if sim.is_complete:
            return
        self._last_matchups = sim.simulate_week()
        self._result_btn.configure(state=tk.NORMAL)
        self._refresh()

    def _on_view_results(self) -> None:
        if not self._last_matchups:
            return
        from diamond_draft.gui.screens.matchup_screen import MatchupScreen

        self._app.show_screen(MatchupScreen, matchups=self._last_matchups)

    def _on_standings(self) -> None:
        from diamond_draft.gui.screens.standings_screen import StandingsScreen

        self._app.show_screen(StandingsScreen)

    def _on_save(self) -> None:
        sm = self._app.save_manager
        path = sm.save(
            teams=self._app.teams,
            league=self._app.league,
            simulator=self._app.simulator,
            slot="autosave",
        )
        messagebox.showinfo("Saved", f"Game saved to {path.name}")
