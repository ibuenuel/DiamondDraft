"""Playoff bracket UI for Diamond Draft.

Renders the two-round knockout tournament (Semifinal → Final) as an
interactive bracket. Seeds are revealed one by one on entry, results animate
in after each simulate, and a champion celebration dialog fires at the end.

State machine (mirrors PlayoffSimulator.current_round):
    0 — Seeds shown, "Simulate Semifinal" enabled.
    1 — Semifinal results shown, winners advanced, "Simulate Final" enabled.
    2 — Champion declared, all simulate buttons disabled.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from diamond_draft.gui.app import (
    ACCENT,
    BUTTON_BG,
    DARK_BG,
    PANEL_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    App,
)
from diamond_draft.gui.widgets import dialog
from diamond_draft.gui.widgets.ui_helpers import (
    accent_button,
    body_label,
    card_frame,
    heading,
    secondary_button,
    separator,
)

# Timing constants (ms)
_SEED_REVEAL_DELAY  = 220   # gap between each seed appearing
_SCORE_TICK_MS      = 30    # counter animation tick rate
_SCORE_STEPS        = 25    # number of steps to count up to final score


class PlayoffBracketScreen(ctk.CTkFrame):
    """Playoff bracket hub — seeding reveal, simulate, results, champion.

    Args:
        parent: The root ``App`` instance that owns this screen.
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._sim = parent.game.playoff_simulator

        # StringVars for team name labels in the bracket (indexed by seed 0–3)
        self._seed_vars:   list[tk.StringVar] = [tk.StringVar(value="") for _ in range(4)]
        # StringVars for score displays per matchup slot
        self._sf1_home_score = tk.StringVar(value="")
        self._sf1_away_score = tk.StringVar(value="")
        self._sf2_home_score = tk.StringVar(value="")
        self._sf2_away_score = tk.StringVar(value="")
        self._fin_home_score = tk.StringVar(value="")
        self._fin_away_score = tk.StringVar(value="")

        # Labels that need to be re-coloured after results come in.
        self._sf1_home_lbl: ctk.CTkLabel | None = None
        self._sf1_away_lbl: ctk.CTkLabel | None = None
        self._sf2_home_lbl: ctk.CTkLabel | None = None
        self._sf2_away_lbl: ctk.CTkLabel | None = None
        self._fin_home_lbl: ctk.CTkLabel | None = None
        self._fin_away_lbl: ctk.CTkLabel | None = None
        self._final_winner_var = tk.StringVar(value="")

        self._sim_btn: ctk.CTkButton | None = None
        self._status_var = tk.StringVar(value="")

        self._build_ui()
        self._restore_or_reveal()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 0))

        heading(header, "🏆  Playoffs", level=1).pack(side="left")
        secondary_button(header, "Standings", self._on_standings, width=110).pack(side="right", padx=(6, 0))
        secondary_button(header, "Set Lineup", self._on_lineup, width=110).pack(side="right", padx=(0, 6))

        separator(self).pack(fill="x", pady=(12, 0))

        # Main body — bracket left, results right
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._bracket_panel = card_frame(body)
        self._bracket_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self._results_panel = card_frame(body)
        self._results_panel.grid(row=0, column=1, sticky="nsew")

        self._build_bracket_panel()
        self._build_results_panel()

    def _build_bracket_panel(self) -> None:
        p = self._bracket_panel

        heading(p, "Bracket", level=2).pack(anchor="w", padx=16, pady=(14, 6))

        # Outer container for the bracket layout
        outer = ctk.CTkFrame(p, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        # ── Semifinal column ───────────────────────────────────────────
        sf_col = ctk.CTkFrame(outer, fg_color="transparent")
        sf_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        body_label(sf_col, "Semifinal", color=TEXT_SECONDARY).pack(anchor="w", pady=(0, 6))

        # SF1: #1 vs #4
        sf1 = card_frame(sf_col, radius=10)
        sf1.pack(fill="x", pady=(0, 4))
        self._sf1_home_lbl = _seed_row(sf1, self._seed_vars[0], "#1 Seed", self._sf1_home_score)
        _divider(sf1)
        self._sf1_away_lbl = _seed_row(sf1, self._seed_vars[3], "#4 Seed", self._sf1_away_score)

        # SF2: #2 vs #3
        sf2 = card_frame(sf_col, radius=10)
        sf2.pack(fill="x", pady=(8, 0))
        self._sf2_home_lbl = _seed_row(sf2, self._seed_vars[1], "#2 Seed", self._sf2_home_score)
        _divider(sf2)
        self._sf2_away_lbl = _seed_row(sf2, self._seed_vars[2], "#3 Seed", self._sf2_away_score)

        # ── Final column ───────────────────────────────────────────────
        fin_col = ctk.CTkFrame(outer, fg_color="transparent")
        fin_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        body_label(fin_col, "Final", color=TEXT_SECONDARY).pack(anchor="w", pady=(0, 6))

        fin = card_frame(fin_col, radius=10)
        fin.pack(fill="x")
        self._fin_home_lbl = _seed_row(fin, tk.StringVar(value="TBD"), "Winner SF1", self._fin_home_score)
        _divider(fin)
        self._fin_away_lbl = _seed_row(fin, tk.StringVar(value="TBD"), "Winner SF2", self._fin_away_score)

        # Champion badge below the final card
        self._champion_lbl = ctk.CTkLabel(
            fin_col,
            textvariable=self._final_winner_var,
            font=("Segoe UI", 13, "bold"),
            text_color=ACCENT,
        )
        self._champion_lbl.pack(anchor="w", pady=(8, 0))

        self._fin_home_frame = fin

    def _build_results_panel(self) -> None:
        p = self._results_panel

        heading(p, "Round Results", level=2).pack(anchor="w", padx=16, pady=(14, 6))

        self._results_scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        self._results_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Placeholder text replaced once results come in
        self._results_placeholder = body_label(
            self._results_scroll,
            "Simulate a round to see detailed results here.",
        )
        self._results_placeholder.pack(anchor="w", padx=8, pady=12)

        # Footer with simulate button + status
        footer = ctk.CTkFrame(p, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 12))

        self._sim_btn = accent_button(
            footer,
            self._next_btn_label(),
            self._on_simulate,
            width=210,
        )
        self._sim_btn.pack(side="left")

        body_label(footer, textvariable=self._status_var).pack(side="left", padx=12)

    # ------------------------------------------------------------------
    # Seed reveal animation
    # ------------------------------------------------------------------

    def _restore_or_reveal(self) -> None:
        """Restore full state if playoffs are already in progress; else animate reveal."""
        if self._sim.current_round > 0:
            self._reveal_all_seeds_immediately()
            self._restore_results()
        else:
            self._animate_seed_reveal(0)

    def _animate_seed_reveal(self, index: int) -> None:
        """Reveal seeds one by one with a short delay between each."""
        names = [t.name for t in self._sim.seeds]
        if index < len(names):
            self._seed_vars[index].set(names[index])
            self.after(_SEED_REVEAL_DELAY, self._animate_seed_reveal, index + 1)
        else:
            self._status_var.set("Set your lineup, then simulate the Semifinal!")

    def _reveal_all_seeds_immediately(self) -> None:
        for i, team in enumerate(self._sim.seeds):
            self._seed_vars[i].set(team.name)

    # ------------------------------------------------------------------
    # Restore state from an already-in-progress playoff
    # ------------------------------------------------------------------

    def _restore_results(self) -> None:
        if self._sim.semifinal_results:
            self._display_semifinal_results(self._sim.semifinal_results, animate=False)
        if self._sim.final_result:
            self._display_final_result(self._sim.final_result, animate=False)
        if self._sim.is_complete:
            self._sim_btn.configure(state="disabled")
            self._status_var.set(f"Champion: {self._sim.champion.name}!")
        else:
            self._sim_btn.configure(text=self._next_btn_label())
            self._status_var.set("Set your lineup, then simulate the Final!")

    # ------------------------------------------------------------------
    # Simulate handler
    # ------------------------------------------------------------------

    def _on_simulate(self) -> None:
        self._sim_btn.configure(state="disabled")
        self._status_var.set("Simulating…")
        self.update_idletasks()

        results = self._sim.simulate_round()

        if self._sim.injury_report:
            report = "\n".join(self._sim.injury_report)
            dialog.show_warning(self, "Injury Report", f"Players injured this round:\n\n{report}")

        if self._sim.current_round == 1:
            # Just finished semis
            self._display_semifinal_results(results, animate=True)
            self._sim_btn.configure(text=self._next_btn_label(), state="normal")
            self._status_var.set("Set your lineup, then simulate the Final!")
        else:
            # Just finished the final
            self._display_final_result(results[0], animate=True)
            self._sim_btn.configure(state="disabled")
            self._status_var.set(f"Champion: {self._sim.champion.name}!")
            self.after(600, self._show_champion_dialog)

        self._save_playoff_state()

    # ------------------------------------------------------------------
    # Results display
    # ------------------------------------------------------------------

    def _display_semifinal_results(self, results, *, animate: bool) -> None:
        r1, r2 = results[0], results[1]

        # Update bracket winner highlights
        sf1_winner = r1.winner.name
        sf2_winner = r2.winner.name

        # SF1 colours
        if self._sf1_home_lbl:
            col = ACCENT if r1.home.name == sf1_winner else TEXT_SECONDARY
            self._sf1_home_lbl.configure(text_color=col)
        if self._sf1_away_lbl:
            col = ACCENT if r1.away.name == sf1_winner else TEXT_SECONDARY
            self._sf1_away_lbl.configure(text_color=col)

        # SF2 colours
        if self._sf2_home_lbl:
            col = ACCENT if r2.home.name == sf2_winner else TEXT_SECONDARY
            self._sf2_home_lbl.configure(text_color=col)
        if self._sf2_away_lbl:
            col = ACCENT if r2.away.name == sf2_winner else TEXT_SECONDARY
            self._sf2_away_lbl.configure(text_color=col)

        # Advance winners to the Final column labels
        for child in self._fin_home_frame.winfo_children():
            child.destroy()
        self._fin_home_lbl = _seed_row(self._fin_home_frame, tk.StringVar(value=sf1_winner), "SF1 Winner", self._fin_home_score)
        _divider(self._fin_home_frame)
        self._fin_away_lbl = _seed_row(self._fin_home_frame, tk.StringVar(value=sf2_winner), "SF2 Winner", self._fin_away_score)

        # Score reveals
        if animate:
            self._animate_score(self._sf1_home_score, r1.home_points)
            self._animate_score(self._sf1_away_score, r1.away_points)
            self._animate_score(self._sf2_home_score, r2.home_points)
            self._animate_score(self._sf2_away_score, r2.away_points)
        else:
            self._sf1_home_score.set(f"{r1.home_points:.1f}")
            self._sf1_away_score.set(f"{r1.away_points:.1f}")
            self._sf2_home_score.set(f"{r2.home_points:.1f}")
            self._sf2_away_score.set(f"{r2.away_points:.1f}")

        # Detailed results in the right panel
        self._clear_results_panel()
        self._add_result_card(r1, "Semifinal 1")
        self._add_result_card(r2, "Semifinal 2")

    def _display_final_result(self, result, *, animate: bool) -> None:
        # Highlight bracket Final row
        winner_name = result.winner.name
        if self._fin_home_lbl:
            col = ACCENT if result.home.name == winner_name else TEXT_SECONDARY
            self._fin_home_lbl.configure(text_color=col)
        if self._fin_away_lbl:
            col = ACCENT if result.away.name == winner_name else TEXT_SECONDARY
            self._fin_away_lbl.configure(text_color=col)

        self._final_winner_var.set(f"🏆  {winner_name}")

        if animate:
            self._animate_score(self._fin_home_score, result.home_points)
            self._animate_score(self._fin_away_score, result.away_points)
        else:
            self._fin_home_score.set(f"{result.home_points:.1f}")
            self._fin_away_score.set(f"{result.away_points:.1f}")

        self._clear_results_panel()
        self._add_result_card(result, "Final")

    def _clear_results_panel(self) -> None:
        if self._results_placeholder:
            try:
                self._results_placeholder.destroy()
            except Exception:
                pass
            self._results_placeholder = None
        for w in self._results_scroll.winfo_children():
            w.destroy()

    def _add_result_card(self, result, label: str) -> None:
        card = card_frame(self._results_scroll, radius=10)
        card.pack(fill="x", pady=6, padx=4)

        heading(card, label, level=3).pack(anchor="w", padx=12, pady=(10, 4))

        winner_name = result.winner.name
        for team, pts in ((result.home, result.home_points), (result.away, result.away_points)):
            is_winner = team.name == winner_name
            color = ACCENT if is_winner else TEXT_PRIMARY
            glyph = "🏆 " if is_winner else "    "
            ctk.CTkLabel(
                card,
                text=f"{glyph}{team.name:<20}  {pts:>7.1f} pts",
                font=("Courier New", 11),
                text_color=color,
                anchor="w",
            ).pack(anchor="w", padx=14, pady=2)

        ctk.CTkLabel(
            card,
            text=f"Winner: {winner_name}",
            font=("Segoe UI", 11, "bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=12, pady=(4, 10))

    # ------------------------------------------------------------------
    # Score counter animation
    # ------------------------------------------------------------------

    def _animate_score(self, var: tk.StringVar, target: float, step: int = 0) -> None:
        """Count up from 0 to *target* over ``_SCORE_STEPS`` ticks."""
        if step >= _SCORE_STEPS:
            var.set(f"{target:.1f}")
            return
        current = target * (step / _SCORE_STEPS)
        var.set(f"{current:.1f}")
        self.after(_SCORE_TICK_MS, self._animate_score, var, target, step + 1)

    # ------------------------------------------------------------------
    # Champion celebration
    # ------------------------------------------------------------------

    def _show_champion_dialog(self) -> None:
        champion = self._sim.champion
        dialog.show_success(
            self,
            "Champion!",
            f"🏆  {champion.name} wins the Diamond Draft Championship!\n\n"
            f"Congratulations — view the final standings to review the season.",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_btn_label(self) -> str:
        if self._sim.current_round == 0:
            return "Simulate Semifinal"
        if self._sim.current_round == 1:
            return "Simulate Final"
        return "Playoffs Complete"

    def _save_playoff_state(self) -> None:
        """Persist the current game + playoff state."""
        sm = self._app.game.save_manager
        if sm:
            sm.save(
                teams=self._app.game.teams,
                league=self._app.game.league,
                simulator=self._app.game.simulator,
                playoff_simulator=self._app.game.playoff_simulator,
                slot="autosave",
            )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_standings(self) -> None:
        self._app.nav.to_standings()

    def _on_lineup(self) -> None:
        self._app.nav.to_lineup()


# ---------------------------------------------------------------------------
# Module-level widget helpers
# ---------------------------------------------------------------------------

def _seed_row(
    parent: ctk.CTkFrame,
    name_var: tk.StringVar,
    placeholder: str,
    score_var: tk.StringVar,
) -> ctk.CTkLabel:
    """Add a team-name row to a bracket card and return the name label."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=10, pady=6)
    row.columnconfigure(0, weight=1)

    lbl = ctk.CTkLabel(
        row,
        textvariable=name_var,
        font=("Segoe UI", 12, "bold"),
        text_color=TEXT_PRIMARY,
        anchor="w",
    )
    lbl.grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        row,
        textvariable=score_var,
        font=("Segoe UI", 11),
        text_color=TEXT_SECONDARY,
        anchor="e",
        width=70,
    ).grid(row=0, column=1, sticky="e")

    return lbl


def _divider(parent: ctk.CTkFrame) -> None:
    ctk.CTkFrame(parent, height=1, fg_color="#2a2d3e", corner_radius=0).pack(fill="x", padx=10)
