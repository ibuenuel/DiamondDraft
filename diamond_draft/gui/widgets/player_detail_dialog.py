"""Player detail popup widget for Diamond Draft.

Displays a player's full statistics, headshot, team logo, and a fantasy-point
bar chart inside a modal ``CTkToplevel`` window.

Three private helpers separate concerns inside this module:

- ``_circular_ctk_image`` — pure image transformation utility.
- ``_StatRowBuilder``      — computes the stats table rows and chart data.
- ``_PlayerImageFetcher``  — fetches headshot and logo in a background thread.

``PlayerDetailDialog`` itself only handles UI construction and wires the
helpers together, keeping it focused on a single responsibility.
"""
from __future__ import annotations

import io
import logging
import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable
from urllib.parse import quote

import customtkinter as ctk

from diamond_draft import config
from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY
from diamond_draft.models.player import Batter, Pitcher

if TYPE_CHECKING:
    from diamond_draft.models.player import Player

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image utility
# ---------------------------------------------------------------------------

def _circular_ctk_image(pil_img, size: int) -> ctk.CTkImage:
    """Crop a PIL image into a circle and wrap it in a CTkImage.

    Args:
        pil_img: Any PIL ``Image`` object; need not already be square.
        size: Output diameter in pixels. The image is scaled to this size
            before cropping.

    Returns:
        A ``CTkImage`` of dimensions ``(size, size)`` with a circular mask
        applied, suitable for direct use in ``CTkLabel``.
    """
    from PIL import Image, ImageDraw

    img  = pil_img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    circular = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular.paste(img, (0, 0), mask=mask)
    return ctk.CTkImage(light_image=circular, dark_image=circular, size=(size, size))


# ---------------------------------------------------------------------------
# Private helper: stat row / chart computation
# ---------------------------------------------------------------------------

class _StatRowBuilder:
    """Build stats table rows and bar-chart data for a single player.

    Reads scoring weights from ``ScoreEngine`` and human-readable labels from
    ``config`` so that both sources remain the authoritative owners of their
    respective data — the builder does not duplicate either.

    Args:
        player: The player whose stats are to be presented.
    """

    def __init__(self, player: Player) -> None:
        self._player = player

    def build(self) -> tuple[list[tuple], float, list[tuple[str, float]]]:
        """Compute display rows, cumulative total, and chart data.

        Returns:
            A 3-tuple of:
            - *rows*: list of ``(label, value_str, weight_str, pts_str)`` tuples
              ready for insertion into a ``ttk.Treeview``.
            - *total*: cumulative fantasy-point contribution as a ``float``.
            - *chart_data*: list of ``(label, contribution)`` pairs for the
              horizontal bar chart. Negative contributions are included.
        """
        if isinstance(self._player, Batter):
            return self._build_batter_rows()
        return self._build_pitcher_rows()

    def _build_batter_rows(self) -> tuple[list[tuple], float, list[tuple[str, float]]]:
        rows:  list[tuple]             = []
        chart: list[tuple[str, float]] = []
        total  = 0.0

        for stat, weight in ScoreEngine.BATTING_WEIGHTS.items():
            val    = self._player.stats.get(stat, 0.0)
            contrib = val * weight
            total  += contrib
            label  = config.BATTING_STAT_LABELS.get(stat, stat)
            rows.append((label, f"{val:.0f}", f"{weight:+.1f}", f"{contrib:+.1f}"))
            chart.append((label, contrib))

        return rows, total, chart

    def _build_pitcher_rows(self) -> tuple[list[tuple], float, list[tuple[str, float]]]:
        rows:  list[tuple]             = []
        chart: list[tuple[str, float]] = []
        total  = 0.0

        for stat, weight in ScoreEngine.PITCHING_WEIGHTS.items():
            val    = self._player.stats.get(stat, 0.0)
            contrib = val * weight
            total  += contrib
            label  = config.PITCHING_STAT_LABELS.get(stat, stat)
            rows.append((label, f"{val:.0f}", f"{weight:+.1f}", f"{contrib:+.1f}"))
            chart.append((label, contrib))

        # ERA bonus row — only shown when the pitcher qualifies.
        era = self._player.stats.get("ERA", 99.0)
        if era < ScoreEngine.ERA_BONUS_THRESHOLD:
            bonus  = ScoreEngine.ERA_BONUS
            total += bonus
            rows.append(("ERA Bonus (<3.00)", f"{era:.2f}", "", f"+{bonus:.1f}"))
            chart.append(("ERA Bonus", bonus))

        return rows, total, chart


# ---------------------------------------------------------------------------
# Private helper: async image fetcher
# ---------------------------------------------------------------------------

class _PlayerImageFetcher:
    """Fetch player headshot and team logo images in a background thread.

    Encapsulates all network I/O and PIL manipulation so ``PlayerDetailDialog``
    is not responsible for image acquisition. Results are delivered via
    callbacks that are marshalled back to the Tk main thread via *schedule*.

    Args:
        player: The player whose images are to be fetched.
        on_headshot: Callback invoked with a ``CTkImage`` on headshot success.
        on_logo:     Callback invoked with a ``CTkImage`` on logo success.
        on_no_photo: Callback invoked with no arguments when no headshot
            could be loaded (shows the "No Photo" fallback label).
        schedule:    Callable equivalent to ``widget.after(0, fn)`` — used to
            marshal results back onto the Tk main thread safely.
    """

    def __init__(
        self,
        player: Player,
        on_headshot: Callable[[ctk.CTkImage], None],
        on_logo: Callable[[ctk.CTkImage], None],
        on_no_photo: Callable[[], None],
        schedule: Callable[[Callable[[], None]], None],
    ) -> None:
        self._player     = player
        self._on_headshot = on_headshot
        self._on_logo    = on_logo
        self._on_no_photo = on_no_photo
        self._schedule   = schedule

    def start(self) -> None:
        """Launch a daemon background thread that fetches both images.

        The thread is a daemon so it does not prevent the process from
        exiting if the dialog is closed before the fetch completes.
        """
        threading.Thread(target=self._run, daemon=True).start()

    # ------------------------------------------------------------------
    # Private — runs on the background thread
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Fetch headshot and logo sequentially on the background thread."""
        self._fetch_headshot()
        self._fetch_logo()

    def _fetch_headshot(self) -> None:
        """Attempt to load the player headshot from the MLB CDN.

        Tries each URL template in ``config.HEADSHOT_URL_TEMPLATES`` in order,
        falling back to a name-based MLB ID lookup when ``mlb_id`` is absent.
        Calls ``on_no_photo`` on any irrecoverable failure.
        """
        try:
            import requests
            from PIL import Image

            mlb_id = self._player.mlb_id
            if mlb_id is None:
                mlb_id = _PlayerImageFetcher._lookup_mlb_id(self._player.name)

            if mlb_id is None:
                self._schedule(self._on_no_photo)
                return

            img_data = None
            for url_tpl in config.HEADSHOT_URL_TEMPLATES:
                try:
                    r = requests.get(url_tpl.format(mlb_id), timeout=8)
                    if r.status_code == 200:
                        img_data = r.content
                        break
                except (requests.RequestException, OSError):
                    continue

            if img_data is None:
                self._schedule(self._on_no_photo)
                return

            pil_img = Image.open(io.BytesIO(img_data))
            photo   = _circular_ctk_image(pil_img, 110)
            self._schedule(lambda p=photo: self._on_headshot(p))

        except (requests.RequestException, OSError, ValueError) as exc:
            logger.debug("Headshot fetch failed for '%s': %s", self._player.name, exc)
            self._schedule(self._on_no_photo)

    def _fetch_logo(self) -> None:
        """Attempt to load the team logo from the ESPN CDN.

        Silently skips teams not present in ``config.TEAM_ESPN_ABBREV`` (e.g.
        CPU teams created during the draft that are not real MLB franchises).
        """
        try:
            import requests
            from PIL import Image

            abbrev = config.TEAM_ESPN_ABBREV.get(self._player.mlb_team)
            if not abbrev:
                return

            r = requests.get(config.TEAM_LOGO_URL_TEMPLATE.format(abbrev), timeout=8)
            if r.status_code != 200:
                return

            pil_img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            logo    = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
            self._schedule(lambda lg=logo: self._on_logo(lg))

        except (requests.RequestException, OSError, ValueError) as exc:
            logger.debug(
                "Logo fetch failed for team '%s': %s", self._player.mlb_team, exc
            )

    @staticmethod
    def _lookup_mlb_id(name: str) -> int | None:
        """Query the MLB People Search API to resolve a player's numeric ID.

        Used as a fallback when ``player.mlb_id`` is ``None`` (common for
        players loaded from the bundled sample dataset).

        Args:
            name: Full player name as displayed in the application.

        Returns:
            The integer MLB person ID of the first search result, or ``None``
            if the lookup fails or returns no matches.
        """
        try:
            import requests

            r = requests.get(
                config.MLB_PEOPLE_SEARCH_URL.format(quote(name)), timeout=8
            )
            r.raise_for_status()
            people = r.json().get("people", [])
            if people:
                return int(people[0]["id"])
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.debug("MLB ID lookup failed for '%s': %s", name, exc)
        return None


# ---------------------------------------------------------------------------
# Public widget
# ---------------------------------------------------------------------------

class PlayerDetailDialog(ctk.CTkToplevel):
    """Modal popup showing full stats, headshot, team logo, and bar chart.

    Opens on double-click in ``PlayerTable``. Construction is synchronous;
    image fetching is deferred to a background thread via ``_PlayerImageFetcher``
    so the dialog opens instantly regardless of network latency.

    Args:
        parent: The parent widget that owns this toplevel window.
        player: The player whose details are to be displayed.
    """

    def __init__(self, parent: tk.Widget, player: Player) -> None:
        super().__init__(parent)
        self._player = player

        # CTkImage refs are stored on self to prevent garbage collection
        # before the label has rendered — Tk images are not reference-counted.
        self._photo_image: ctk.CTkImage | None = None
        self._logo_image:  ctk.CTkImage | None = None

        self.title(player.name)
        self.geometry("900x720")
        self.minsize(750, 600)
        self.configure(fg_color=DARK_BG)
        self.resizable(True, True)
        self.grab_set()

        # Compute stat data once; both the table and chart consume the same result.
        self._stat_rows, self._stat_total, self._chart_data = (
            _StatRowBuilder(player).build()
        )

        self._build_ui()

        # Start image fetching after the window is visible to avoid blocking
        # the Tk event loop during the initial render pass.
        _PlayerImageFetcher(
            player      = player,
            on_headshot = self._set_headshot,
            on_logo     = self._set_logo,
            on_no_photo = lambda: self._photo_label.configure(text="No\nPhoto"),
            schedule    = lambda fn: self.after(0, fn),
        ).start()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Lay out the top-level grid and delegate to section builders."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        """Build the header card with headshot, player name, badges, and score."""
        header = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        # Circular headshot placeholder — replaced asynchronously.
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

        ctk.CTkLabel(
            header,
            text=self._player.name,
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(18, 4))

        # Badge row: position chip + team logo + full team name.
        badge_row = ctk.CTkFrame(header, fg_color="transparent")
        badge_row.grid(row=1, column=1, sticky="w", pady=4)

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

        # Logo placeholder — replaced asynchronously.
        self._logo_label = ctk.CTkLabel(
            badge_row, text="", width=40, height=40, fg_color="transparent"
        )
        self._logo_label.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            badge_row,
            text=self._player.mlb_team,
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        score = self._player.calculate_fantasy_points()
        ctk.CTkLabel(
            header,
            text=f"Fantasy Points: {score:.1f} pts",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT,
            anchor="w",
        ).grid(row=2, column=1, sticky="w", pady=(4, 18))

    def _build_body(self) -> None:
        """Build the body area containing the stats table and bar chart."""
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._build_stats_table(body)
        self._build_bar_chart(body)

    def _build_stats_table(self, parent: ctk.CTkFrame) -> None:
        """Build the statistics breakdown Treeview inside *parent*.

        Args:
            parent: The container frame that receives the table card.
        """
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

        columns    = ("stat", "value", "weight", "pts")
        col_config = {
            "stat":   ("Statistic",        150, tk.W),
            "value":  ("Value",             90, tk.CENTER),
            "weight": ("Weight",            90, tk.CENTER),
            "pts":    ("Pts Contribution", 120, tk.CENTER),
        }
        tree = ttk.Treeview(table_card, columns=columns, show="headings", height=8)
        for col, (label, width, anchor) in col_config.items():
            tree.heading(col, text=label)
            tree.column(col, width=width, anchor=anchor, stretch=col == "stat")

        for row in self._stat_rows:
            tree.insert("", tk.END, values=row)
        tree.insert("", tk.END, values=("─" * 16, "─" * 7, "─" * 7, "─" * 12))
        tree.insert("", tk.END, values=("Total", "", "", f"{self._stat_total:+.1f}"))
        tree.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

    def _build_bar_chart(self, parent: ctk.CTkFrame) -> None:
        """Build the canvas-based horizontal bar chart inside *parent*.

        Args:
            parent: The container frame that receives the chart card.
        """
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
        # Redraw on every resize so bars fill the available width correctly.
        self._canvas.bind("<Configure>", self._draw_chart)

    def _draw_chart(self, _event=None) -> None:
        """Redraw the horizontal bar chart when the canvas size changes.

        Each bar's length is proportional to its absolute contribution
        relative to the largest absolute contribution in the dataset. Positive
        contributions use the accent colour; negative ones use a muted tone.
        """
        canvas = self._canvas
        canvas.delete("all")

        contributions = self._chart_data
        if not contributions:
            return

        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return

        margin_left  = 150
        margin_right = 70
        bar_area_w   = w - margin_left - margin_right
        n            = len(contributions)
        row_h        = (h - 20) // max(n, 1)
        bar_height   = min(24, row_h - 8)
        max_abs      = max(abs(c) for _, c in contributions) or 1.0

        for i, (label, contrib) in enumerate(contributions):
            y_center = 14 + i * row_h + row_h // 2
            y_top    = y_center - bar_height // 2
            y_bot    = y_center + bar_height // 2

            canvas.create_text(
                margin_left - 10, y_center,
                text=label, anchor="e",
                fill=TEXT_PRIMARY, font=("Segoe UI", 10),
            )
            bar_len = int(abs(contrib) / max_abs * bar_area_w * 0.85)
            color   = ACCENT if contrib >= 0 else "#4a4a6a"
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
    # Image callbacks (called on the Tk main thread via schedule)
    # ------------------------------------------------------------------

    def _set_headshot(self, photo: ctk.CTkImage) -> None:
        """Apply the loaded headshot image to the photo label.

        Checks ``winfo_exists`` first to guard against the dialog being
        closed before the background thread delivers its result.

        Args:
            photo: The circular CTkImage to display.
        """
        if self.winfo_exists():
            self._photo_image = photo
            self._photo_label.configure(image=photo, text="", fg_color="transparent")

    def _set_logo(self, logo: ctk.CTkImage) -> None:
        """Apply the loaded team logo image to the logo label.

        Args:
            logo: The team logo CTkImage to display.
        """
        if self.winfo_exists():
            self._logo_image = logo
            self._logo_label.configure(image=logo)
