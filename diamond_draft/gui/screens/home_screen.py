from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

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
        self._start_loading()

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

        self._status_var = tk.StringVar(value="Loading player data…")
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
            state=tk.DISABLED,
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

    def _start_loading(self) -> None:
        threading.Thread(target=self._load_data, daemon=True).start()

    def _load_data(self) -> None:
        try:
            players = DataLoader(use_cache=True).load()
            self.after(0, lambda: self._on_load_done(players))
        except Exception as exc:
            self.after(0, lambda: self._on_load_error(exc))

    def _on_load_done(self, players: list) -> None:
        self._app.players = players
        self._app.save_manager = SaveManager()
        self._status_var.set(f"{len(players)} players loaded — ready!")
        self._new_btn.configure(state=tk.NORMAL)

    def _on_load_error(self, exc: Exception) -> None:
        self._status_var.set("Failed to load player data.")
        messagebox.showerror("Data Load Error", str(exc))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_new_game(self) -> None:
        from diamond_draft.gui.screens.draft_screen import DraftScreen

        self._app.show_screen(DraftScreen)

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
