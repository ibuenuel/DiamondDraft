"""Snake draft screen for Diamond Draft.

Presents the interactive draft UI where the human user selects players
while CPU teams automatically fill their picks. The draft sequence is a
standard snake format: pick order reverses every round so all teams have
equal access to high-value players regardless of their draft slot.

"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from diamond_draft import config
from diamond_draft.engine.draft_system import DraftSystem
from diamond_draft.gui.app import ACCENT, DARK_BG, TEXT_PRIMARY, TEXT_SECONDARY, App
from diamond_draft.gui.widgets.player_table import PlayerTable
from diamond_draft.gui.widgets.ui_helpers import (
    accent_button,
    attach_scrollbar,
    body_label,
    card_frame,
    heading,
    secondary_button,
    separator,
)
from diamond_draft.gui.widgets import dialog
from diamond_draft.models.league import League
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team

# Module-level private: CPU team display names sourced from config.
_cpu_team_names: list[str] = config.CPU_TEAM_NAMES


class DraftScreen(ctk.CTkFrame):
    """Interactive snake draft UI.

    Manages the full draft lifecycle: initialising teams, displaying the
    available player pool, handling human picks, auto-advancing CPU turns,
    and transitioning to ``SeasonScreen`` when the draft is complete.

    Args:
        parent: The root ``App`` instance that owns this screen.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
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
        """Create teams and initialise the DraftSystem.

        The human team takes slot 0 using the name the user chose on the
        home screen; CPU teams fill the remaining slots using names from
        ``config.CPU_TEAM_NAMES``.

        Returns:
            A fully configured ``DraftSystem`` ready for the first pick.
        """
        names = [self._app.game.team_name] + _cpu_team_names
        teams = [Team(name=name, is_human=(i == 0)) for i, name in enumerate(names)]
        self._app.game.teams = teams
        return DraftSystem(teams=teams, player_pool=self._app.game.players)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Lay out the draft screen: header, main content area, and footer."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        self._header_var = tk.StringVar()
        ctk.CTkLabel(
            header,
            textvariable=self._header_var,
            font=("Segoe UI", 22, "bold"),
            text_color=ACCENT,
        ).pack(side="left")
        secondary_button(header, "← Back", self._on_back, width=90).pack(side="right")

        separator(self).pack(fill="x", pady=(12, 0))

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=12)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # Left panel: sortable available-player table.
        left = card_frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        heading(left, "Available Players", level=2).pack(anchor="w", padx=12, pady=(12, 4))
        table_inner = ctk.CTkFrame(left, fg_color="transparent")
        table_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._table = PlayerTable(table_inner, on_select=self._on_player_selected)
        attach_scrollbar(self._table, table_inner)

        # Right panel: human roster summary + draft log.
        right = card_frame(content)
        right.grid(row=0, column=1, sticky="nsew")
        heading(right, "Your Roster", level=2).pack(anchor="w", padx=12, pady=(12, 4))
        self._roster_text = ctk.CTkTextbox(
            right,
            font=("Courier New", 10),
            fg_color="#0d1022",
            text_color=TEXT_PRIMARY,
            corner_radius=8,
            border_width=0,
            height=180,
            state="disabled",
        )
        self._roster_text.pack(fill="x", padx=8, pady=(0, 4))
        heading(right, "Draft Log", level=2).pack(anchor="w", padx=12, pady=(8, 4))
        self._log_text = ctk.CTkTextbox(
            right,
            font=("Segoe UI", 9),
            fg_color="#0d1022",
            text_color=TEXT_SECONDARY,
            corner_radius=8,
            border_width=0,
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Footer: pick button + status label.
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(0, 16))
        self._pick_btn = accent_button(
            footer, "Draft Selected Player", self._on_pick, width=200
        )
        self._pick_btn.configure(state="disabled")
        self._pick_btn.pack(side="left")
        self._selection_var = tk.StringVar(value="Select a player from the list above.")
        body_label(footer, textvariable=self._selection_var).pack(side="left", padx=16)

        self._refresh_table()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_player_selected(self, player: Player) -> None:
        """Handle selection of a player row in the PlayerTable.

        Updates the status label and enables or disables the pick button
        based on whether the human team still has an open slot for the
        selected player's position.

        Args:
            player: The player that was selected in the table.
        """
        self._selected_player = player
        team     = self._draft.current_team
        can_pick = team.needs_position(player.position)
        self._selection_var.set(
            f"{player.name}  ({player.position}, {player.mlb_team})  "
            f"— {player.calculate_fantasy_points():.1f} pts"
            + ("" if can_pick else "  ✗ slot full")
        )
        self._pick_btn.configure(state="normal" if can_pick else "disabled")

    def _on_pick(self) -> None:
        """Execute the human player's draft pick.

        Delegates to ``DraftSystem.make_pick``, logs the selection, clears
        the UI selection state, and advances CPU turns if it is their turn.
        """
        if self._selected_player is None:
            return
        try:
            self._draft.make_pick(self._selected_player)
        except ValueError as exc:
            dialog.show_warning(self, "Invalid Pick", str(exc))
            return

        self._log(
            f"[You] drafted {self._selected_player.name} "
            f"({self._selected_player.position})"
        )
        self._selected_player = None
        self._pick_btn.configure(state="disabled")
        self._selection_var.set("Select a player from the list above.")
        self._refresh_after_pick()
        self._advance_cpu_if_needed()

    def _on_back(self) -> None:
        """Prompt the user before discarding draft progress and returning home."""
        if dialog.ask_yes_no(
            self, "Leave Draft", "Return to the main menu? Draft progress will be lost."
        ):
            self._app.nav.to_home()

    # ------------------------------------------------------------------
    # CPU automation
    # ------------------------------------------------------------------

    def _advance_cpu_if_needed(self) -> None:
        """Execute all consecutive CPU picks and refresh the UI once done.

        If it is the human's turn (or the draft is complete), this is a no-op.
        Called after every human pick and at startup to handle cases where the
        human drafts last in a round.
        """
        if self._draft.is_complete:
            self._finish_draft()
            return
        if not self._draft.current_team.is_human:
            cpu_picks = self._draft.advance_cpu_turns()
            for p in cpu_picks:
                team_name = next(
                    t.name for t in self._app.game.teams
                    if any(r.name == p.name for r in t.roster)
                )
                self._log(f"[{team_name}] drafted {p.name} ({p.position})")
            self._refresh_after_pick()
            if self._draft.is_complete:
                self._finish_draft()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _finish_draft(self) -> None:
        """Create the League and SeasonSimulator, then transition to SeasonScreen.

        The ``_finishing`` guard prevents double-invocation in edge cases where
        ``_advance_cpu_if_needed`` is called from both the human pick handler
        and the CPU automation branch in the same call stack.
        """
        if getattr(self, "_finishing", False):
            return
        self._finishing = True

        from diamond_draft.engine.season_simulator import SeasonSimulator

        league = League(teams=self._app.game.teams)
        league.generate_schedule()
        self._app.game.league    = league
        self._app.game.simulator = SeasonSimulator(league=league)

        def _transition():
            dialog.show_success(self, "Draft Complete!", "All teams have been filled. The season begins!")
            self._app.nav.to_season()

        self._app.after(0, _transition)

    def _refresh_header(self) -> None:
        """Update the pick counter and current team label in the header."""
        if self._draft.is_complete:
            return
        team  = self._draft.current_team
        pick  = self._draft.current_pick_number
        total = self._draft.total_picks
        self._header_var.set(f"Pick {pick}/{total} — {team.name}")

    def _refresh_table(self) -> None:
        """Reload the available player table with the current undrafted pool."""
        self._table.load(self._draft.available_players())

    def _refresh_roster(self) -> None:
        """Rebuild the human team's roster summary in the right panel."""
        human_team = self._app.game.teams[0]
        lines: list[str] = []

        # Track which players fill a required slot (first N per position).
        active_names: set[str] = set()
        for pos, needed in Team.SLOT_REQUIREMENTS.items():
            slot_players = [p for p in human_team.roster if p.position == pos]
            for p in slot_players[:needed]:
                active_names.add(p.name)

        # Required position slots
        for pos, needed in Team.SLOT_REQUIREMENTS.items():
            slot_players = [p for p in human_team.roster if p.position == pos]
            for p in slot_players[:needed]:
                lines.append(f"  {pos:<4}  {p.name}")
            for _ in range(needed - min(len(slot_players), needed)):
                lines.append(f"  {pos:<4}  —")

        # Bench slots
        bench_players = [p for p in human_team.roster if p.name not in active_names]
        lines.append("")
        lines.append("  ── BENCH ──────────────")
        for p in bench_players:
            lines.append(f"  BCH   {p.name}  ({p.position})")
        for _ in range(Team.BENCH_SPOTS - len(bench_players)):
            lines.append("  BCH   —")

        _set_textbox(self._roster_text, "\n".join(lines))

    def _refresh_after_pick(self) -> None:
        """Refresh header, player table, and roster summary after any pick."""
        self._refresh_header()
        self._refresh_table()
        self._refresh_roster()

    def _log(self, message: str) -> None:
        """Append *message* to the draft log text box.

        Args:
            message: A single line of draft log text (no trailing newline needed).
        """
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")


def _set_textbox(widget: ctk.CTkTextbox, text: str) -> None:
    """Replace the entire content of a read-only CTkTextbox with *text*.

    Args:
        widget: The ``CTkTextbox`` to update.
        text: The new content to display.
    """
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("end", text)
    widget.configure(state="disabled")
