from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from diamond_draft.gui.app import (
    ACCENT,
    DARK_BG,
    PANEL_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    App,
)
from diamond_draft.io.data_loader import DataLoader
from diamond_draft.io.save_manager import SaveManager


class HomeScreen(tk.Frame):
    """
    Start screen: New Game, Load Game, Quit.

    Data loading runs in a background thread to keep the UI responsive.
    Results are passed back to the main thread via after().
    """

    def __init__(self, parent: App) -> None:
        super().__init__(parent, bg=DARK_BG)
        self._app = parent
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        title_frame = tk.Frame(self, bg=DARK_BG)
        title_frame.pack(pady=(80, 10))

        ttk.Label(title_frame, text="Diamond Draft", style="Title.TLabel").pack()
        ttk.Label(
            title_frame,
            text="MLB Fantasy League Simulator",
            style="Subtitle.TLabel",
        ).pack(pady=(4, 0))

        self._status_var = tk.StringVar(value="Select a season to get started.")
        ttk.Label(
            self, textvariable=self._status_var, style="Subtitle.TLabel"
        ).pack(pady=(30, 0))

        btn_frame = tk.Frame(self, bg=DARK_BG)
        btn_frame.pack(pady=40)

        self._new_btn = ttk.Button(
            btn_frame,
            text="New Game",
            command=self._on_new_game,
            width=18,
        )
        self._new_btn.pack(pady=8)

        self._load_btn = ttk.Button(
            btn_frame,
            text="Load Game",
            command=self._on_load_game,
            width=18,
        )
        self._load_btn.pack(pady=8)

        ttk.Button(
            btn_frame,
            text="Quit",
            command=self._app.destroy,
            width=18,
        ).pack(pady=8)

    # ------------------------------------------------------------------
    # Data loading (background thread)
    # ------------------------------------------------------------------

    def _start_loading(self, year: int | None = None) -> None:
        if year is None:
            year = self._app.current_year
        self._new_btn.configure(state=tk.DISABLED)
        self._status_var.set(f"Loading {year} player data…")
        threading.Thread(target=self._load_data, args=(year,), daemon=True).start()

    def _load_data(self, year: int) -> None:
        try:
            players = DataLoader(year=year, use_cache=True).load()
            self.after(0, lambda: self._on_load_done(players, year))
        except Exception as exc:
            self.after(0, lambda: self._on_load_error(exc))

    def _on_load_done(self, players: list, year: int) -> None:
        self._app.players = players
        self._app.current_year = year
        self._app.loaded_year = year
        self._app.save_manager = SaveManager()
        self._status_var.set(f"{len(players)} players loaded ({year}) — ready!")
        self._new_btn.configure(state=tk.NORMAL)

    def _on_load_error(self, exc: Exception) -> None:
        self._status_var.set("Failed to load player data.")
        messagebox.showerror("Data Load Error", str(exc))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new_game(self) -> None:
        year = _pick_year(self._app, self._app.current_year)
        if year is None:
            return

        def _start():
            from diamond_draft.gui.screens.draft_screen import DraftScreen
            self._app.show_screen(DraftScreen)

        if self._app.loaded_year == year:
            _start()
        else:
            self._start_loading(year)
            self._wait_then_start(_start)

    def _wait_then_start(self, callback) -> None:
        """Poll every 200 ms until the background load finishes, then invoke callback."""
        if self._app.loaded_year == self._app.current_year:
            callback()
        else:
            self.after(200, lambda: self._wait_then_start(callback))

    def _on_load_game(self) -> None:
        sm = SaveManager()
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
        from diamond_draft.gui.screens.season_screen import SeasonScreen

        self._app.teams = teams
        self._app.league = league
        self._app.simulator = SeasonSimulator(league=league)
        self._app.simulator.restore_week(week)
        self._app.show_screen(SeasonScreen)


_AVAILABLE_YEARS = [2022, 2023, 2024, 2025]


def _pick_year(parent: tk.Tk, current_year: int) -> int | None:
    """Modal dialog for choosing an MLB season year."""
    dialog = tk.Toplevel(parent)
    dialog.title("Select Season")
    dialog.geometry("280x220")
    dialog.configure(bg="#1a1a2e")
    dialog.resizable(False, False)
    dialog.grab_set()

    ttk.Label(dialog, text="Choose an MLB season:").pack(pady=(20, 8))

    selected = tk.IntVar(value=current_year)
    for year in _AVAILABLE_YEARS:
        ttk.Radiobutton(dialog, text=str(year), variable=selected, value=year).pack(
            anchor=tk.W, padx=60
        )

    result: list[int] = []

    def _confirm():
        result.append(selected.get())
        dialog.destroy()

    def _cancel():
        dialog.destroy()

    btn_row = tk.Frame(dialog, bg="#1a1a2e")
    btn_row.pack(pady=(16, 0))
    ttk.Button(btn_row, text="Start", command=_confirm).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_row, text="Cancel", command=_cancel).pack(side=tk.LEFT, padx=6)

    parent.wait_window(dialog)
    return result[0] if result else None


def _pick_save_slot(parent: tk.Tk, saves: list[str]) -> str | None:
    """Simple modal dialog to choose a save slot from a list."""
    dialog = tk.Toplevel(parent)
    dialog.title("Load Game")
    dialog.geometry("300x200")
    dialog.configure(bg="#1a1a2e")
    dialog.grab_set()

    ttk.Label(dialog, text="Select a save slot:").pack(pady=(20, 8))
    listbox = tk.Listbox(
        dialog, bg="#16213e", fg="#eaeaea", selectbackground="#e94560", height=6
    )
    for s in saves:
        listbox.insert(tk.END, s)
    listbox.pack(fill=tk.BOTH, padx=20)
    listbox.selection_set(0)

    result: list[str] = []

    def _confirm():
        sel = listbox.curselection()
        if sel:
            result.append(saves[sel[0]])
        dialog.destroy()

    ttk.Button(dialog, text="Load", command=_confirm).pack(pady=10)
    parent.wait_window(dialog)
    return result[0] if result else None
