from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY, App
from diamond_draft.models.matchup import Matchup
from diamond_draft.models.team import Team


class MatchupScreen(tk.Frame):
    """
    Detailed weekly matchup results.

    Shows each matchup as a side-by-side card with per-player scores,
    team totals, and the winner highlighted.
    """

    def __init__(self, parent: App, matchups: list[Matchup]) -> None:
        super().__init__(parent, bg=DARK_BG)
        self._app = parent
        self._matchups = matchups
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = tk.Frame(self, bg=DARK_BG, pady=12)
        header.pack(fill=tk.X, padx=20)

        week = self._matchups[0].week if self._matchups else "?"
        ttk.Label(
            header, text=f"Week {week} Results", style="Title.TLabel"
        ).pack(side=tk.LEFT)
        ttk.Button(
            header, text="← Season", command=self._on_back
        ).pack(side=tk.RIGHT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Scrollable matchup cards
        canvas = tk.Canvas(self, bg=DARK_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=DARK_BG)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

        def _on_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)

        def _on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_resize)
        inner.bind("<Configure>", _on_frame_configure)

        for matchup in self._matchups:
            self._add_matchup_card(inner, matchup)

    def _add_matchup_card(self, parent: tk.Frame, matchup: Matchup) -> None:
        summary = matchup.summary()
        winner_name = summary["winner"]

        card = tk.Frame(parent, bg=PANEL_BG, pady=12, padx=12, relief=tk.FLAT)
        card.pack(fill=tk.X, padx=20, pady=10)
        card.columnconfigure(0, weight=1)
        card.columnconfigure(2, weight=1)

        # Home team column
        home_win = matchup.home.name == winner_name
        self._add_team_column(card, matchup.home, is_winner=home_win, column=0)

        # VS label
        vs_label = tk.Label(
            card,
            text="VS",
            bg=PANEL_BG,
            fg=TEXT_SECONDARY,
            font=("Segoe UI", 14, "bold"),
        )
        vs_label.grid(row=0, column=1, rowspan=2, padx=16)

        # Away team column
        away_win = matchup.away.name == winner_name
        self._add_team_column(card, matchup.away, is_winner=away_win, column=2)

        # Winner banner
        if winner_name != "Tie":
            banner_color = ACCENT
            banner_text = f"🏆  {winner_name} wins!"
        else:
            banner_color = TEXT_SECONDARY
            banner_text = "Tie"

        banner = tk.Label(
            card,
            text=banner_text,
            bg=PANEL_BG,
            fg=banner_color,
            font=("Segoe UI", 11, "bold"),
        )
        banner.grid(row=2, column=0, columnspan=3, pady=(10, 0))

    def _add_team_column(
        self,
        parent: tk.Frame,
        team: Team,
        is_winner: bool,
        column: int,
    ) -> None:
        total = team.total_points()
        name_color = ACCENT if is_winner else TEXT_PRIMARY

        name_label = tk.Label(
            parent,
            text=team.name,
            bg=PANEL_BG,
            fg=name_color,
            font=("Segoe UI", 13, "bold"),
        )
        name_label.grid(row=0, column=column, sticky=tk.W if column == 0 else tk.E)

        pts_label = tk.Label(
            parent,
            text=f"{total:.1f} pts",
            bg=PANEL_BG,
            fg=name_color,
            font=("Segoe UI", 11),
        )
        pts_label.grid(row=1, column=column, sticky=tk.W if column == 0 else tk.E)

        # Per-player breakdown
        detail_frame = tk.Frame(parent, bg=PANEL_BG)
        detail_frame.grid(
            row=0,
            column=column,
            rowspan=2,
            sticky=tk.N + (tk.W if column == 0 else tk.E),
            pady=(30, 0),
        )

        for player in sorted(team.roster, key=lambda p: p.calculate_fantasy_points(), reverse=True):
            pts = player.calculate_fantasy_points()
            line = f"{player.position:<4} {player.name:<22} {pts:>7.1f} pts"
            tk.Label(
                detail_frame,
                text=line,
                bg=PANEL_BG,
                fg=TEXT_PRIMARY if pts >= 0 else "#e94560",
                font=("Courier New", 9),
            ).pack(anchor=tk.W)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        self._app.nav.to_season()
