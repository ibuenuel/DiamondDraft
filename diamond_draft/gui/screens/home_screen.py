from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY, App
from diamond_draft.gui.widgets.ui_helpers import (
    accent_button,
    body_label,
    card_frame,
    heading,
    secondary_button,
    separator,
)
from diamond_draft.io.data_loader import DataLoader


class HomeScreen(ctk.CTkFrame):
    """
    Start screen: New Game, Load Game, Quit.

    Data loading runs in a background thread to keep the UI responsive.
    Results are passed back to the main thread via after().
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, fg_color=DARK_BG, corner_radius=0)
        self._app = parent
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Vertical centering spacer
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=1, column=0)

        # Logo / title
        heading(center, "⚾  Diamond Draft", level=1).pack(pady=(0, 4))
        heading(center, "MLB Fantasy League Simulator", level=3).pack()

        sep = separator(center)
        sep.pack(fill="x", pady=24)

        # Status / progress
        self._status_var = tk.StringVar(value="Select a season to get started.")
        body_label(center, textvariable=self._status_var).pack()

        self._progress = ctk.CTkProgressBar(
            center,
            mode="indeterminate",
            width=300,
            height=6,
            corner_radius=3,
            fg_color="#2a2d3e",
            progress_color=ACCENT,
        )
        self._progress.pack(pady=(6, 0))
        self._progress.set(0)
        self._progress.pack_forget()

        # Buttons card
        btn_card = card_frame(center, radius=16)
        btn_card.pack(pady=32, padx=40, fill="x")

        self._new_btn = accent_button(btn_card, "New Game", self._on_new_game, width=220)
        self._new_btn.pack(pady=(24, 8))

        secondary_button(btn_card, "Load Game", self._on_load_game, width=220).pack(pady=8)
        secondary_button(btn_card, "Baseball Rules & Abbreviations", self._on_help, width=220).pack(pady=8)
        secondary_button(btn_card, "Quit", self._app.destroy, width=220).pack(pady=(8, 24))

    # ------------------------------------------------------------------
    # Data loading (background thread)
    # ------------------------------------------------------------------

    def _start_loading(self, year: int | None = None) -> None:
        if year is None:
            year = self._app.game.current_year
        self._new_btn.configure(state="disabled")
        self._status_var.set(f"Loading {year} player data…")
        self._progress.pack(pady=(6, 0))
        self._progress.start()
        threading.Thread(target=self._load_data, args=(year,), daemon=True).start()

    def _load_data(self, year: int) -> None:
        try:
            players, source = DataLoader(year=year, use_cache=True).load()
            self.after(0, lambda: self._on_load_done(players, year, source))
        except Exception as exc:
            self.after(0, lambda: self._on_load_error(exc))

    def _on_load_done(self, players: list, year: int, source: str) -> None:
        self._app.game.players = players
        self._app.game.current_year = year
        self._app.game.loaded_year = year
        self._progress.stop()
        self._progress.pack_forget()
        self._status_var.set(f"{len(players)} players loaded ({year}, {source}) — ready!")
        self._new_btn.configure(state="normal")

    def _on_load_error(self, exc: Exception) -> None:
        self._progress.stop()
        self._progress.pack_forget()
        self._status_var.set("Failed to load player data.")
        messagebox.showerror("Data Load Error", str(exc))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new_game(self) -> None:
        year = _pick_year(self._app, self._app.game.current_year)
        if year is None:
            return

        team_name = _pick_team_name(self._app)
        if team_name is None:
            return
        self._app.game.team_name = team_name

        def _start():
            self._app.nav.to_draft()

        if self._app.game.loaded_year == year:
            _start()
        else:
            self._start_loading(year)
            self._wait_then_start(_start)

    def _wait_then_start(self, callback) -> None:
        if self._app.game.loaded_year == self._app.game.current_year:
            callback()
        else:
            self.after(200, lambda: self._wait_then_start(callback))

    def _on_help(self) -> None:
        from diamond_draft.gui.widgets.help_dialog import open_help
        open_help(self._app)

    def _on_load_game(self) -> None:
        sm = self._app.game.save_manager
        saves = sm.list_saves()
        if not saves:
            messagebox.showinfo("Load Game", "No saved games found.")
            return

        slot = _pick_save_slot(self._app, saves)
        if not slot:
            return

        try:
            teams, league, week = sm.load(slot=slot)
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))
            return

        from diamond_draft.engine.season_simulator import SeasonSimulator

        self._app.game.teams = teams
        self._app.game.league = league
        self._app.game.simulator = SeasonSimulator(league=league)
        self._app.game.simulator.restore_week(week)
        self._app.nav.to_season()


_AVAILABLE_YEARS = [2022, 2023, 2024, 2025]


def _pick_year(parent: ctk.CTk, current_year: int) -> int | None:
    """Modal dialog for choosing an MLB season year."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Select Season")
    dialog.geometry("300x260")
    dialog.resizable(False, False)
    dialog.grab_set()

    heading(dialog, "Choose a season", level=2).pack(pady=(24, 16))

    selected = tk.IntVar(value=current_year)
    for year in _AVAILABLE_YEARS:
        ctk.CTkRadioButton(
            dialog,
            text=str(year),
            variable=selected,
            value=year,
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT,
        ).pack(anchor="w", padx=60, pady=3)

    result: list[int] = []

    def _confirm():
        result.append(selected.get())
        dialog.destroy()

    btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_row.pack(pady=(20, 0))
    accent_button(btn_row, "Start", _confirm, width=100).pack(side="left", padx=6)
    secondary_button(btn_row, "Cancel", dialog.destroy, width=100).pack(side="left", padx=6)

    parent.wait_window(dialog)
    return result[0] if result else None


def _pick_team_name(parent: ctk.CTk) -> str | None:
    """Modal dialog for the player to choose their team name."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Your Team")
    dialog.geometry("340x200")
    dialog.resizable(False, False)
    dialog.grab_set()

    heading(dialog, "Enter your team name", level=2).pack(pady=(24, 10))

    name_var = tk.StringVar()
    entry = ctk.CTkEntry(
        dialog,
        textvariable=name_var,
        width=260,
        font=("Segoe UI", 12),
        fg_color=PANEL_BG,
        border_color=ACCENT,
        text_color=TEXT_PRIMARY,
    )
    entry.pack(pady=(0, 4))
    entry.focus_set()

    body_label(dialog, 'Leave blank to use "Your Team"').pack()

    result: list[str] = []

    def _confirm():
        name = name_var.get().strip() or "Your Team"
        result.append(name)
        dialog.destroy()

    entry.bind("<Return>", lambda _: _confirm())

    btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_row.pack(pady=(14, 0))
    accent_button(btn_row, "Confirm", _confirm, width=110).pack(side="left", padx=6)
    secondary_button(btn_row, "Cancel", dialog.destroy, width=110).pack(side="left", padx=6)

    parent.wait_window(dialog)
    return result[0] if result else None


def _pick_save_slot(parent: ctk.CTk, saves: list[str]) -> str | None:
    """Simple modal dialog to choose a save slot from a list."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Load Game")
    dialog.geometry("320x220")
    dialog.grab_set()

    heading(dialog, "Select a save slot", level=2).pack(pady=(20, 10))

    # Scrollable list of save slots as radio buttons
    scroll = ctk.CTkScrollableFrame(dialog, fg_color=PANEL_BG, height=100)
    scroll.pack(fill="x", padx=20)

    selected = tk.StringVar(value=saves[0] if saves else "")
    for s in saves:
        ctk.CTkRadioButton(
            scroll,
            text=s,
            variable=selected,
            value=s,
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT,
            hover_color=ACCENT,
        ).pack(anchor="w", pady=3)

    result: list[str] = []

    def _confirm():
        if selected.get():
            result.append(selected.get())
        dialog.destroy()

    accent_button(dialog, "Load", _confirm, width=120).pack(pady=12)
    parent.wait_window(dialog)
    return result[0] if result else None
