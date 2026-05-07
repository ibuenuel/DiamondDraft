from __future__ import annotations

import io
import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
from urllib.parse import quote

import customtkinter as ctk

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.gui.app import (
    ACCENT,
    DARK_BG,
    PANEL_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from diamond_draft.models.player import Batter, Pitcher

if TYPE_CHECKING:
    from diamond_draft.models.player import Player

# ---------------------------------------------------------------------------
# MLB team name → ESPN abbreviation (used for logo URL)
# ---------------------------------------------------------------------------
_TEAM_ABBREV: dict[str, str] = {
    "Arizona Diamondbacks": "ari",
    "Atlanta Braves": "atl",
    "Baltimore Orioles": "bal",
    "Boston Red Sox": "bos",
    "Chicago Cubs": "chc",
    "Chicago White Sox": "cws",
    "Cincinnati Reds": "cin",
    "Cleveland Guardians": "cle",
    "Colorado Rockies": "col",
    "Detroit Tigers": "det",
    "Houston Astros": "hou",
    "Kansas City Royals": "kc",
    "Los Angeles Angels": "laa",
    "Los Angeles Dodgers": "lad",
    "Miami Marlins": "mia",
    "Milwaukee Brewers": "mil",
    "Minnesota Twins": "min",
    "New York Mets": "nym",
    "New York Yankees": "nyy",
    "Oakland Athletics": "oak",
    "Philadelphia Phillies": "phi",
    "Pittsburgh Pirates": "pit",
    "San Diego Padres": "sd",
    "San Francisco Giants": "sf",
    "Seattle Mariners": "sea",
    "St. Louis Cardinals": "stl",
    "Tampa Bay Rays": "tb",
    "Texas Rangers": "tex",
    "Toronto Blue Jays": "tor",
    "Washington Nationals": "wsh",
    "Athletics": "oak",
}

_HEADSHOT_URLS = [
    "https://securea.mlb.com/mlb/images/players/head_shot/{}.jpg",
    "https://midfield.mlbstatic.com/v1/people/{}/spots/spot-120.jpg",
]
_LOGO_URL = "https://a.espncdn.com/i/teamlogos/mlb/500/{}.png"
_MLB_PEOPLE_SEARCH = "https://statsapi.mlb.com/api/v1/people/search?names={}&sportId=1"


def _circular_ctk_image(pil_img, size: int) -> ctk.CTkImage:
    """Crop a PIL image into a circle and return a CTkImage."""
    from PIL import Image, ImageDraw

    img = pil_img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    circular = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular.paste(img, (0, 0), mask=mask)
    return ctk.CTkImage(light_image=circular, dark_image=circular, size=(size, size))


class PlayerDetailDialog(ctk.CTkToplevel):
    """
    Modal popup showing full stats, headshot, team logo, and bar chart for a player.
    Opens on double-click in PlayerTable.
    """

    def __init__(self, parent: tk.Widget, player: Player) -> None:
        super().__init__(parent)
        self._player = player
        self._photo_image = None   # CTkImage refs kept alive to prevent GC
        self._logo_image = None

        self.title(player.name)
        self.geometry("900x720")
        self.minsize(750, 600)
        self.configure(fg_color=DARK_BG)
        self.resizable(True, True)
        self.grab_set()

        # Compute once; both stats table and bar chart reuse these
        self._stat_rows, self._stat_total, self._chart_data = self._compute_stat_rows()

        self._build_ui()
        self._load_images_async()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        # ── Headshot (circular) ──────────────────────────────────────────
        self._photo_label = ctk.CTkLabel(
            header,
            text="...",
            width=110,
            height=110,
            fg_color="#2a2d3e",
            corner_radius=55,
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY,
        )
        self._photo_label.grid(row=0, column=0, rowspan=3, padx=(20, 24), pady=18)

        # ── Player name ──────────────────────────────────────────────────
        ctk.CTkLabel(
            header,
            text=self._player.name,
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(18, 4))

        # ── Badges + team logo row ───────────────────────────────────────
        badge_row = ctk.CTkFrame(header, fg_color="transparent")
        badge_row.grid(row=1, column=1, sticky="w", pady=4)

        # Position badge
        ctk.CTkLabel(
            badge_row,
            text=self._player.position,
            font=("Segoe UI", 12, "bold"),
            text_color="#ffffff",
            fg_color=ACCENT,
            corner_radius=6,
            width=44,
            height=26,
        ).pack(side="left", padx=(0, 10))

        # Team logo placeholder (replaced once image loads)
        self._logo_label = ctk.CTkLabel(
            badge_row,
            text="",
            width=40,
            height=40,
            fg_color="transparent",
        )
        self._logo_label.pack(side="left", padx=(0, 10))

        # Full team name
        ctk.CTkLabel(
            badge_row,
            text=self._player.mlb_team,
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        # ── Fantasy score ────────────────────────────────────────────────
        score = self._player.calculate_fantasy_points()
        ctk.CTkLabel(
            header,
            text=f"Fantasy Points: {score:.1f} pts",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT,
            anchor="w",
        ).grid(row=2, column=1, sticky="w", pady=(4, 18))

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._build_stats_table(body)
        self._build_bar_chart(body)

    def _build_stats_table(self, parent: ctk.CTkFrame) -> None:
        table_card = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=12)
        table_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        table_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            table_card,
            text="Statistics & Points Breakdown",
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 6))

        columns = ("stat", "value", "weight", "pts")
        tree = ttk.Treeview(table_card, columns=columns, show="headings", height=8)
        col_config = {
            "stat":   ("Statistic",       150, tk.W),
            "value":  ("Value",            90, tk.CENTER),
            "weight": ("Weight",           90, tk.CENTER),
            "pts":    ("Pts Contribution", 120, tk.CENTER),
        }
        for col, (label, width, anchor) in col_config.items():
            tree.heading(col, text=label)
            tree.column(col, width=width, anchor=anchor, stretch=col == "stat")

        for row in self._stat_rows:
            tree.insert("", tk.END, values=row)
        tree.insert("", tk.END, values=("─" * 16, "─" * 7, "─" * 7, "─" * 12))
        tree.insert("", tk.END, values=("Total", "", "", f"{self._stat_total:+.1f}"))

        tree.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

    def _compute_stat_rows(self) -> tuple[list[tuple], float, list[tuple[str, float]]]:
        player = self._player
        rows: list[tuple] = []
        chart: list[tuple[str, float]] = []
        total = 0.0

        if isinstance(player, Batter):
            weights = ScoreEngine.BATTING_WEIGHTS
            labels = {"HR": "Home Runs", "RBI": "Runs Batted In", "R": "Runs",
                      "SB": "Stolen Bases", "H": "Hits", "SO": "Strikeouts"}
            for stat, weight in weights.items():
                val = player.stats.get(stat, 0.0)
                contrib = val * weight
                total += contrib
                label = labels.get(stat, stat)
                rows.append((label, f"{val:.0f}", f"{weight:+.1f}", f"{contrib:+.1f}"))
                chart.append((label, contrib))
        else:
            weights = ScoreEngine.PITCHING_WEIGHTS
            labels = {"W": "Wins", "SO": "Strikeouts", "IP": "Innings Pitched",
                      "SV": "Saves", "L": "Losses"}
            for stat, weight in weights.items():
                val = player.stats.get(stat, 0.0)
                contrib = val * weight
                total += contrib
                label = labels.get(stat, stat)
                rows.append((label, f"{val:.0f}", f"{weight:+.1f}", f"{contrib:+.1f}"))
                chart.append((label, contrib))
            era = player.stats.get("ERA", 99.0)
            if era < ScoreEngine.ERA_BONUS_THRESHOLD:
                bonus = ScoreEngine.ERA_BONUS
                total += bonus
                rows.append(("ERA Bonus (<3.00)", f"{era:.2f}", "", f"+{bonus:.1f}"))
                chart.append(("ERA Bonus", bonus))

        return rows, total, chart

    def _build_bar_chart(self, parent: ctk.CTkFrame) -> None:
        chart_card = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=12)
        chart_card.grid(row=1, column=0, sticky="nsew")
        chart_card.grid_rowconfigure(1, weight=1)
        chart_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            chart_card,
            text="Points Contributions",
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self._canvas = tk.Canvas(chart_card, bg=PANEL_BG, highlightthickness=0)
        self._canvas.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self._canvas.bind("<Configure>", self._draw_chart)

    def _draw_chart(self, _event=None) -> None:
        canvas = self._canvas
        canvas.delete("all")

        contributions = self._chart_data
        if not contributions:
            return

        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return

        margin_left = 150
        margin_right = 70
        bar_area_width = w - margin_left - margin_right
        n = len(contributions)
        row_h = (h - 20) // max(n, 1)
        bar_height = min(24, row_h - 8)
        max_abs = max(abs(c) for _, c in contributions) or 1.0

        for i, (label, contrib) in enumerate(contributions):
            y_center = 14 + i * row_h + row_h // 2
            y_top = y_center - bar_height // 2
            y_bot = y_center + bar_height // 2

            canvas.create_text(
                margin_left - 10, y_center,
                text=label, anchor="e",
                fill=TEXT_PRIMARY, font=("Segoe UI", 10),
            )
            bar_len = int(abs(contrib) / max_abs * bar_area_width * 0.85)
            color = ACCENT if contrib >= 0 else "#4a4a6a"
            canvas.create_rectangle(
                margin_left, y_top, margin_left + bar_len, y_bot,
                fill=color, outline="",
            )
            canvas.create_text(
                margin_left + bar_len + 8, y_center,
                text=f"{contrib:+.1f}", anchor="w",
                fill=TEXT_SECONDARY, font=("Segoe UI", 10),
            )

    # ------------------------------------------------------------------
    # Async image loading (headshot + team logo)
    # ------------------------------------------------------------------

    def _load_images_async(self) -> None:
        threading.Thread(target=self._fetch_images, daemon=True).start()

    def _fetch_images(self) -> None:
        self._fetch_headshot()
        self._fetch_team_logo()

    def _fetch_headshot(self) -> None:
        try:
            import requests
            from PIL import Image

            mlb_id = self._player.mlb_id
            if mlb_id is None:
                mlb_id = self._lookup_mlb_id_by_name(self._player.name)

            if mlb_id is None:
                self.after(0, self._photo_label.configure, {"text": "No\nPhoto"})
                return

            img_data = None
            for url_tpl in _HEADSHOT_URLS:
                try:
                    r = requests.get(url_tpl.format(mlb_id), timeout=8)
                    if r.status_code == 200:
                        img_data = r.content
                        break
                except (requests.RequestException, OSError):
                    continue

            if img_data is None:
                self.after(0, self._photo_label.configure, {"text": "No\nPhoto"})
                return

            pil_img = Image.open(io.BytesIO(img_data))
            photo = _circular_ctk_image(pil_img, 110)
            self._photo_image = photo
            self.after(0, self._set_headshot, photo)
        except Exception:
            self.after(0, self._photo_label.configure, {"text": "No\nPhoto"})

    def _fetch_team_logo(self) -> None:
        try:
            import requests
            from PIL import Image

            abbrev = _TEAM_ABBREV.get(self._player.mlb_team)
            if not abbrev:
                return

            r = requests.get(_LOGO_URL.format(abbrev), timeout=8)
            if r.status_code != 200:
                return

            pil_img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            logo = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
            self._logo_image = logo
            self.after(0, self._set_logo, logo)
        except Exception:
            pass

    @staticmethod
    def _lookup_mlb_id_by_name(name: str) -> int | None:
        try:
            import requests
            r = requests.get(_MLB_PEOPLE_SEARCH.format(quote(name)), timeout=8)
            r.raise_for_status()
            people = r.json().get("people", [])
            if people:
                return int(people[0]["id"])
        except Exception:
            pass
        return None

    def _set_headshot(self, photo: ctk.CTkImage) -> None:
        if self.winfo_exists():
            self._photo_label.configure(image=photo, text="", fg_color="transparent")

    def _set_logo(self, logo: ctk.CTkImage) -> None:
        if self.winfo_exists():
            self._logo_label.configure(image=logo)
