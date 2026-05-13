from __future__ import annotations

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY, App
from diamond_draft.gui.widgets.ui_helpers import (
    card_frame,
    heading,
    secondary_button,
    separator,
)
from diamond_draft.models.matchup import Matchup
from diamond_draft.models.team import Team


class MatchupScreen(ctk.CTkFrame):
    """Detailed weekly matchup results.

    Renders each matchup as a side-by-side card showing each team's active
    players, their individual fantasy point scores, team totals, and the
    winning team highlighted in the accent colour.

    Args:
        parent: The root ``App`` instance that owns this screen.
        matchups: The list of ``Matchup`` objects for the week to display.
            Typically three matchups (one per pair of teams).
    """

    def __init__(self, parent: App, matchups: list[Matchup]) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._matchups = matchups
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        week = self._matchups[0].week if self._matchups else "?"
        heading(header, f"Week {week} Results", level=1).pack(side="left")
        secondary_button(header, "← Season", self._on_back, width=110).pack(side="right")

        separator(self).pack(fill="x", pady=(12, 0))

        # Scrollable area for matchup cards
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=16)

        for matchup in self._matchups:
            self._add_matchup_card(scroll, matchup)

    def _add_matchup_card(self, parent: ctk.CTkScrollableFrame, matchup: Matchup) -> None:
        summary = matchup.summary()
        winner_name = summary["winner"]

        card = card_frame(parent, radius=14)
        card.pack(fill="x", pady=10)
        card.columnconfigure(0, weight=1)
        card.columnconfigure(2, weight=1)

        # Home team
        home_win = matchup.home.name == winner_name
        self._add_team_column(card, matchup.home, is_winner=home_win, column=0)

        # VS
        ctk.CTkLabel(
            card,
            text="VS",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=1, rowspan=2, padx=20)

        # Away team
        away_win = matchup.away.name == winner_name
        self._add_team_column(card, matchup.away, is_winner=away_win, column=2)

        # Winner banner
        if winner_name != "Tie":
            banner_color = ACCENT
            banner_text = f"🏆  {winner_name} wins!"
        else:
            banner_color = TEXT_SECONDARY
            banner_text = "Tie"

        ctk.CTkLabel(
            card,
            text=banner_text,
            font=("Segoe UI", 12, "bold"),
            text_color=banner_color,
        ).grid(row=2, column=0, columnspan=3, pady=(12, 12))

    def _add_team_column(
        self,
        parent: ctk.CTkFrame,
        team: Team,
        is_winner: bool,
        column: int,
    ) -> None:
        total = team.total_points()
        name_color = ACCENT if is_winner else TEXT_PRIMARY
        anchor = "w" if column == 0 else "e"

        ctk.CTkLabel(
            parent,
            text=team.name,
            font=("Segoe UI", 14, "bold"),
            text_color=name_color,
        ).grid(row=0, column=column, sticky=anchor, padx=16, pady=(14, 0))

        ctk.CTkLabel(
            parent,
            text=f"{total:.1f} pts",
            font=("Segoe UI", 12),
            text_color=name_color,
        ).grid(row=1, column=column, sticky=anchor, padx=16)

        # Per-player detail in a nested frame
        detail = ctk.CTkFrame(parent, fg_color="transparent")
        detail.grid(row=0, column=column, rowspan=2, sticky="n" + anchor, padx=16, pady=(44, 0))

        for player in sorted(team.roster, key=lambda p: p.calculate_fantasy_points(), reverse=True):
            pts = player.calculate_fantasy_points()
            line = f"{player.position:<4} {player.name:<22} {pts:>7.1f} pts"
            ctk.CTkLabel(
                detail,
                text=line,
                font=("Courier New", 9),
                text_color=TEXT_PRIMARY if pts >= 0 else ACCENT,
                anchor=anchor,
            ).pack(anchor=anchor)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_back(self) -> None:
        self._app.nav.to_season()
