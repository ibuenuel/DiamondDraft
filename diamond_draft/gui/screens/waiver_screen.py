from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

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
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


class WaiverScreen(tk.Frame):
    """
    Waiver Wire screen — lets the human team drop one roster player and
    pick up one free-agent replacement after each simulated week.

    Rules enforced:
    - Available players are filtered to the same position as the dropped player,
      so slot requirements are always maintained after the swap.
    - Exactly one drop + one add per visit (or the user skips with no changes).
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, bg=DARK_BG)
        self._app = parent
        self._human_team: Team = parent.state.teams[0]
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
        header = tk.Frame(self, bg=DARK_BG, pady=12)
        header.pack(fill=tk.X, padx=20)

        sim = self._app.state.simulator
        week_label = f"Week {sim.current_week}" if sim else "Waiver Wire"
        ttk.Label(
            header, text=f"Waiver Wire — {week_label}", style="Title.TLabel"
        ).pack(side=tk.LEFT)
        ttk.Button(
            header, text="Skip (No Changes)", command=self._on_skip
        ).pack(side=tk.RIGHT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Main content — two panels side by side
        content = tk.Frame(self, bg=DARK_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        content.columnconfigure(0, weight=2)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        # Left: your roster
        left = ttk.Frame(content, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(
            left, text="Your Roster  (select player to DROP)", style="Subtitle.TLabel"
        ).pack(anchor=tk.W, padx=8, pady=(8, 4))

        roster_frame = tk.Frame(left, bg=PANEL_BG)
        roster_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._roster_tree = ttk.Treeview(
            roster_frame,
            columns=("pos", "name", "pts"),
            show="headings",
            selectmode="browse",
        )
        self._roster_tree.heading("pos",  text="Pos")
        self._roster_tree.heading("name", text="Player")
        self._roster_tree.heading("pts",  text="Pts")
        self._roster_tree.column("pos",  width=45,  anchor=tk.CENTER, stretch=False)
        self._roster_tree.column("name", width=170, anchor=tk.W)
        self._roster_tree.column("pts",  width=60,  anchor=tk.CENTER, stretch=False)

        vsb_left = ttk.Scrollbar(
            roster_frame, orient=tk.VERTICAL, command=self._roster_tree.yview
        )
        self._roster_tree.configure(yscrollcommand=vsb_left.set)
        vsb_left.pack(side=tk.RIGHT, fill=tk.Y)
        self._roster_tree.pack(fill=tk.BOTH, expand=True)
        self._roster_tree.bind("<<TreeviewSelect>>", self._on_roster_select)

        # Right: available waiver players
        right = ttk.Frame(content, style="Panel.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        self._avail_label = ttk.Label(
            right,
            text="Available Players  (select player to ADD)",
            style="Subtitle.TLabel",
        )
        self._avail_label.pack(anchor=tk.W, padx=8, pady=(8, 4))

        table_frame = tk.Frame(right, bg=PANEL_BG)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._waiver_table = PlayerTable(
            table_frame, on_select=self._on_waiver_select
        )
        vsb_right = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self._waiver_table.yview
        )
        self._waiver_table.configure(yscrollcommand=vsb_right.set)
        vsb_right.pack(side=tk.RIGHT, fill=tk.Y)
        self._waiver_table.pack(fill=tk.BOTH, expand=True)

        # Action bar
        action = tk.Frame(self, bg=DARK_BG, pady=10)
        action.pack(fill=tk.X, padx=20)

        self._drop_var = tk.StringVar(value="Drop:  —")
        self._add_var  = tk.StringVar(value="Add:  —")

        ttk.Label(action, textvariable=self._drop_var, style="Subtitle.TLabel",
                  foreground=ACCENT).pack(side=tk.LEFT)
        ttk.Label(action, text=" → ", style="Subtitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(action, textvariable=self._add_var, style="Subtitle.TLabel",
                  foreground="#4caf50").pack(side=tk.LEFT)

        self._confirm_btn = ttk.Button(
            action,
            text="Confirm Trade",
            command=self._on_confirm,
            state=tk.DISABLED,
        )
        self._confirm_btn.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _compute_waiver_pool(self) -> list[Player]:
        """All loaded players not currently on any team's roster."""
        rostered = {p.name for team in self._app.state.teams for p in team.roster}
        return [p for p in self._app.state.players if p.name not in rostered]

    def _load_roster(self) -> None:
        self._roster_tree.delete(*self._roster_tree.get_children())
        for player in sorted(
            self._human_team.roster,
            key=lambda p: p.calculate_fantasy_points(),
            reverse=True,
        ):
            pts = f"{player.calculate_fantasy_points():.1f}"
            self._roster_tree.insert(
                "", tk.END, iid=player.name,
                values=(player.position, player.name, pts),
            )

    def _filter_waiver_by_position(self, position: str) -> None:
        """Reload the right panel with only waiver players at the given position."""
        filtered = [p for p in self._waiver_pool if p.position == position]
        self._waiver_table.load(filtered)
        self._avail_label.configure(
            text=f"Available Players  (position: {position})  —  {len(filtered)} found"
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
        self._confirm_btn.configure(state=tk.DISABLED)

        # Highlight the selected row in the roster tree
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
        self._confirm_btn.configure(state=tk.NORMAL)

    def _on_confirm(self) -> None:
        if self._drop_player is None or self._add_player is None:
            return

        # Perform the swap
        self._human_team.roster.remove(self._drop_player)
        self._human_team.roster.append(self._add_player)

        # Mark waiver as used so the button is hidden in SeasonScreen
        self._app.state.waiver_available = False

        messagebox.showinfo(
            "Trade Complete",
            f"Dropped  {self._drop_player.name}\n"
            f"Added    {self._add_player.name}",
        )
        self._app.nav.to_season()

    def _on_skip(self) -> None:
        self._app.state.waiver_available = False
        self._app.nav.to_season()
