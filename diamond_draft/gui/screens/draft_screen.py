from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from diamond_draft.engine.draft_system import DraftSystem
from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.gui.app import (
    ACCENT,
    DARK_BG,
    PANEL_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    App,
)
from diamond_draft.gui.widgets.player_table import PlayerTable
from diamond_draft.models.league import League
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


class DraftScreen(tk.Frame):
    """
    Interactive snake draft UI.

    Layout:
    ┌─────────────────────────────────────────────────────┐
    │  Header: pick counter + current team                │
    ├────────────────────────┬────────────────────────────┤
    │  Available players     │  Your roster / CPU log     │
    │  (PlayerTable)         │                            │
    ├────────────────────────┴────────────────────────────┤
    │  [Draft Selected Player]  button                    │
    └─────────────────────────────────────────────────────┘
    """

    _TEAM_NAMES = [
        "Your Team",
        "Yankees",
        "Red Sox",
        "Dodgers",
        "Cubs",
        "Cardinals",
    ]

    def __init__(self, parent: App) -> None:
        super().__init__(parent, bg=DARK_BG)
        self._app = parent
        self._selected_player: Player | None = None
        self._draft = self._init_draft()
        self._build_ui()
        self._refresh_header()
        self._advance_cpu_if_needed()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_draft(self) -> DraftSystem:
        teams = [
            Team(name=name, is_human=(i == 0))
            for i, name in enumerate(self._TEAM_NAMES)
        ]
        self._app.teams = teams
        return DraftSystem(teams=teams, player_pool=self._app.players)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # --- Header ---
        header = tk.Frame(self, bg=DARK_BG, pady=10)
        header.pack(fill=tk.X, padx=20)

        self._header_var = tk.StringVar()
        ttk.Label(header, textvariable=self._header_var, style="Title.TLabel").pack(
            side=tk.LEFT
        )

        ttk.Button(
            header, text="← Back", command=self._on_back
        ).pack(side=tk.RIGHT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # --- Main content ---
        content = tk.Frame(self, bg=DARK_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # Left: available players
        left = ttk.Frame(content, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(left, text="Available Players", style="Subtitle.TLabel").pack(
            anchor=tk.W, padx=8, pady=(8, 4)
        )

        table_frame = tk.Frame(left, bg=PANEL_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._table = PlayerTable(
            table_frame,
            on_select=self._on_player_selected,
        )
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._table.yview)
        self._table.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._table.pack(fill=tk.BOTH, expand=True)

        # Right panel: your roster + CPU log
        right = ttk.Frame(content, style="Panel.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Label(right, text="Your Roster", style="Subtitle.TLabel").pack(
            anchor=tk.W, padx=8, pady=(8, 4)
        )

        self._roster_text = tk.Text(
            right,
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI", 9),
            state=tk.DISABLED,
            height=12,
            relief=tk.FLAT,
            padx=6,
            pady=4,
        )
        self._roster_text.pack(fill=tk.BOTH, expand=True, padx=4)

        ttk.Label(right, text="Draft Log", style="Subtitle.TLabel").pack(
            anchor=tk.W, padx=8, pady=(8, 4)
        )

        self._log_text = tk.Text(
            right,
            bg=PANEL_BG,
            fg=TEXT_SECONDARY,
            font=("Segoe UI", 9),
            state=tk.DISABLED,
            height=10,
            relief=tk.FLAT,
            padx=6,
            pady=4,
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # --- Footer ---
        footer = tk.Frame(self, bg=DARK_BG, pady=8)
        footer.pack(fill=tk.X, padx=20)

        self._pick_btn = ttk.Button(
            footer,
            text="Draft Selected Player",
            command=self._on_pick,
            state=tk.DISABLED,
        )
        self._pick_btn.pack(side=tk.LEFT)

        self._selection_var = tk.StringVar(value="Select a player from the list above.")
        ttk.Label(footer, textvariable=self._selection_var, style="Subtitle.TLabel").pack(
            side=tk.LEFT, padx=16
        )

        self._refresh_table()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_player_selected(self, player: Player) -> None:
        self._selected_player = player
        team = self._draft.current_team
        can_pick = team.needs_position(player.position)
        self._selection_var.set(
            f"{player.name}  ({player.position}, {player.mlb_team})  "
            f"— {ScoreEngine.score(player):.1f} pts"
            + ("" if can_pick else "  ✗ slot full")
        )
        self._pick_btn.configure(state=tk.NORMAL if can_pick else tk.DISABLED)

    def _on_pick(self) -> None:
        if self._selected_player is None:
            return
        try:
            self._draft.make_pick(self._selected_player)
        except ValueError as exc:
            messagebox.showwarning("Invalid Pick", str(exc))
            return

        self._log(f"[You] drafted {self._selected_player.name} ({self._selected_player.position})")
        self._selected_player = None
        self._pick_btn.configure(state=tk.DISABLED)
        self._selection_var.set("Select a player from the list above.")
        self._refresh_after_pick()
        self._advance_cpu_if_needed()

    def _on_back(self) -> None:
        from diamond_draft.gui.screens.home_screen import HomeScreen

        if messagebox.askyesno("Leave Draft", "Return to the main menu? Draft progress will be lost."):
            self._app.show_screen(HomeScreen)

    # ------------------------------------------------------------------
    # CPU automation
    # ------------------------------------------------------------------

    def _advance_cpu_if_needed(self) -> None:
        if self._draft.is_complete:
            self._finish_draft()
            return
        if not self._draft.current_team.is_human:
            cpu_picks = self._draft.advance_cpu_turns()
            for p in cpu_picks:
                team_name = next(
                    t.name for t in self._app.teams
                    if any(r.name == p.name for r in t.roster)
                )
                self._log(f"[{team_name}] drafted {p.name} ({p.position})")
            self._refresh_after_pick()
            if self._draft.is_complete:
                self._finish_draft()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _finish_draft(self) -> None:
        from diamond_draft.engine.season_simulator import SeasonSimulator
        from diamond_draft.gui.screens.season_screen import SeasonScreen

        league = League(teams=self._app.teams)
        league.generate_schedule()
        self._app.league = league
        self._app.simulator = SeasonSimulator(league=league)
        messagebox.showinfo("Draft Complete!", "All teams have been filled. The season begins!")
        self._app.show_screen(SeasonScreen)

    def _refresh_header(self) -> None:
        if self._draft.is_complete:
            return
        team = self._draft.current_team
        pick = self._draft.current_pick_number
        total = self._draft.total_picks
        self._header_var.set(f"Pick {pick}/{total} — {team.name}")

    def _refresh_table(self) -> None:
        self._table.load(self._draft.available_players())

    def _refresh_roster(self) -> None:
        human_team = self._app.teams[0]
        lines = []
        for pos, needed in Team.SLOT_REQUIREMENTS.items():
            slot_players = [p for p in human_team.roster if p.position == pos]
            for p in slot_players:
                lines.append(f"  {pos:<4}  {p.name}")
            remaining = needed - len(slot_players)
            for _ in range(remaining):
                lines.append(f"  {pos:<4}  —")
        self._set_text(self._roster_text, "\n".join(lines))

    def _refresh_after_pick(self) -> None:
        self._refresh_header()
        self._refresh_table()
        self._refresh_roster()

    def _log(self, message: str) -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, message + "\n")
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)
