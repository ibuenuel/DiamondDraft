"""In-app reference guide for baseball rules, positions, stats, and scoring.

Presents a tabbed, scrollable ``CTkToplevel`` dialog. The scoring tab
dynamically reads weights from the injected ``ScoreEngine`` data so the
displayed values are always in sync with the live scoring configuration —
the dialog does not hard-code any weights itself.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from diamond_draft.gui.app import ACCENT, DARK_BG, PANEL_BG, TEXT_PRIMARY, TEXT_SECONDARY


def open_help(parent: tk.Widget) -> None:
    """Open the Baseball Rules & Abbreviations help dialog.

    Args:
        parent: The widget that will own the modal dialog.
    """
    HelpDialog(parent)


class HelpDialog(ctk.CTkToplevel):
    """Scrollable reference guide for baseball basics, positions, stats, and scoring.

    The scoring tab accepts the ``ScoreEngine`` weights as optional constructor
    parameters so that callers can inject test doubles or alternative weight
    sets without subclassing. When omitted, the parameters default to the live
    ``ScoreEngine`` values at call time.

    Args:
        parent: The parent widget that owns this dialog.
        batting_weights: Points-per-unit mapping for batting stats.
            Defaults to ``ScoreEngine.BATTING_WEIGHTS``.
        pitching_weights: Points-per-unit mapping for pitching stats.
            Defaults to ``ScoreEngine.PITCHING_WEIGHTS``.
        era_bonus_threshold: ERA value below which the ERA bonus applies.
            Defaults to ``ScoreEngine.ERA_BONUS_THRESHOLD``.
        era_bonus: Flat bonus awarded when ERA qualifies.
            Defaults to ``ScoreEngine.ERA_BONUS``.
    """

    def __init__(
        self,
        parent: tk.Widget,
        batting_weights: dict[str, float] | None = None,
        pitching_weights: dict[str, float] | None = None,
        era_bonus_threshold: float | None = None,
        era_bonus: float | None = None,
    ) -> None:
        super().__init__(parent)

        # Deferred import keeps this module decoupled from the engine layer at
        # module load time. Defaults are resolved lazily so mock weight dicts
        # can be passed without touching ScoreEngine at all.
        from diamond_draft.engine.score_engine import ScoreEngine

        self._batting_weights     = batting_weights     or ScoreEngine.BATTING_WEIGHTS
        self._pitching_weights    = pitching_weights    or ScoreEngine.PITCHING_WEIGHTS
        self._era_bonus_threshold = era_bonus_threshold or ScoreEngine.ERA_BONUS_THRESHOLD
        self._era_bonus           = era_bonus           or ScoreEngine.ERA_BONUS

        self.title("Baseball Rules & Abbreviations")
        self.geometry("780x560")
        self.minsize(660, 460)
        self.configure(fg_color=DARK_BG)
        self.resizable(True, True)
        self.grab_set()
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the four-tab layout and populate each tab via builder methods."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        tabs = ctk.CTkTabview(
            self,
            fg_color=PANEL_BG,
            segmented_button_fg_color=DARK_BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT,
            segmented_button_unselected_color=DARK_BG,
            segmented_button_unselected_hover_color="#0f3460",
            text_color=TEXT_PRIMARY,
            corner_radius=12,
        )
        tabs.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        for name, builder in [
            ("Baseball Basics", self._build_basics),
            ("Positions",       self._build_positions),
            ("Statistics",      self._build_statistics),
            ("Scoring System",  self._build_scoring),
        ]:
            tabs.add(name)
            frame = ctk.CTkScrollableFrame(
                tabs.tab(name),
                fg_color="transparent",
                scrollbar_button_color="#2a2d3e",
                scrollbar_button_hover_color=ACCENT,
            )
            frame.pack(fill="both", expand=True)
            builder(frame)

    # ------------------------------------------------------------------
    # Tab content builders
    # ------------------------------------------------------------------

    def _build_basics(self, parent: ctk.CTkScrollableFrame) -> None:
        """Populate the Baseball Basics tab with introductory sections.

        Args:
            parent: The scrollable frame inside the tab.
        """
        sections = [
            ("What is Baseball?",
             "Baseball is a bat-and-ball sport played between two teams of nine players. "
             "Teams alternate between batting (offense) and fielding (defense) each inning."),

            ("Game Structure",
             "A game consists of 9 innings. Each inning, both teams get a turn to bat.\n"
             "The batting team scores runs; the fielding team tries to get 3 outs.\n"
             "After 9 innings, the team with the most runs wins.\n"
             "Ties go to extra innings until one team leads at the end of a full inning."),

            ("How to Score a Run",
             "A batter reaches base via a hit, walk, or error.\n"
             "Runners advance around 1st → 2nd → 3rd base → home plate.\n"
             "Touching home plate scores 1 run for the batting team.\n"
             "A Home Run (HR) sends the batter and all runners home immediately."),

            ("Getting Outs",
             "The fielding team gets outs in several ways:\n"
             "  • Strikeout (SO) — batter misses 3 pitches\n"
             "  • Fly out — batter hits the ball and a fielder catches it in the air\n"
             "  • Ground out — fielder throws to a base before the runner arrives\n"
             "  • Double play — two outs on a single play"),

            ("Pitching",
             "The pitcher throws the ball from the mound to home plate.\n"
             "Starting Pitchers (SP) open the game and aim for 5+ innings.\n"
             "Relief Pitchers (RP) take over mid-game when the starter tires.\n"
             "A Closer is a specialized RP who finishes wins — earns Saves (SV)."),

            ("What is Fantasy Baseball?",
             "You draft real MLB players to form your fantasy roster.\n"
             "Each week your players' real-world statistics are converted to fantasy points.\n"
             "Your total is compared against another team's total — highest score wins the week.\n"
             "At the end of the season, the team with the most weekly wins is the champion."),
        ]
        for title, body in sections:
            _section(parent, title, body)

    def _build_positions(self, parent: ctk.CTkScrollableFrame) -> None:
        """Populate the Positions tab with one section per roster slot.

        Args:
            parent: The scrollable frame inside the tab.
        """
        positions = [
            ("C  — Catcher",
             "Crouches behind home plate to receive pitches. Calls the game and controls the "
             "opposing running game. One of the most demanding defensive positions."),
            ("1B — First Base",
             "Guards first base and receives throws from infielders. Typically a power hitter "
             "(high HR and RBI), athletic enough to scoop low throws."),
            ("2B — Second Base",
             "Part of the middle infield. Turns double plays with the shortstop. "
             "Usually a contact hitter with good range."),
            ("3B — Third Base",
             "Known as the 'hot corner' due to hard-hit balls. Requires a strong arm to throw "
             "across the diamond. Often a balanced power and average hitter."),
            ("SS — Shortstop",
             "Premium defensive position requiring the most range, arm strength, and agility. "
             "Covers the gap between 2nd and 3rd. Often the team's best all-around player."),
            ("OF — Outfield",
             "Three positions: Left Field (LF), Center Field (CF), Right Field (RF). "
             "CF is the most demanding. Outfielders track fly balls and have strong arms."),
            ("DH — Designated Hitter",
             "Bats in place of the pitcher but does not play the field. "
             "Used in the American League. Usually a slugger focused on offense."),
            ("SP — Starting Pitcher",
             "Begins each game and aims to pitch 5–7 innings. "
             "Evaluated by Wins (W), ERA, Strikeouts (SO), and Innings Pitched (IP)."),
            ("RP — Relief Pitcher",
             "Enters the game after the starter. Closers are a type of RP who finish games "
             "and earn Saves (SV). Evaluated by ERA, SO, and SV."),
        ]
        for title, body in positions:
            _section(parent, title, body)

    def _build_statistics(self, parent: ctk.CTkScrollableFrame) -> None:
        """Populate the Statistics tab with batting and pitching stat explanations.

        Args:
            parent: The scrollable frame inside the tab.
        """
        _heading(parent, "Batting Statistics")
        batting = [
            ("HR — Home Run",
             "The batter hits the ball over the outfield fence in fair territory. "
             "All runners on base (including the batter) score immediately."),
            ("RBI — Run Batted In",
             "Credited to the batter when their plate appearance directly causes a run to score "
             "(via a hit, walk, sacrifice fly, etc.)."),
            ("R — Run",
             "Awarded to a player when they cross home plate and score a run for their team."),
            ("SB — Stolen Base",
             "When a baserunner successfully advances to the next base during a pitch "
             "without the batter hitting the ball."),
            ("H — Hit",
             "The batter safely reaches at least first base via a fair ball "
             "that is not caught on the fly. Includes singles, doubles, triples, and home runs."),
            ("SO — Strikeout (batter)",
             "The batter receives three strikes and is out. "
             "In fantasy baseball this is a negative stat for the batter."),
        ]
        for title, body in batting:
            _section(parent, title, body, indent=True)

        _heading(parent, "Pitching Statistics")
        pitching = [
            ("W — Win",
             "A starting pitcher earns a Win if they pitched at least 5 innings, left while "
             "their team was winning, and the team held that lead until the end of the game."),
            ("L — Loss",
             "The pitcher is charged with a Loss when they are the pitcher of record "
             "at the time their team falls behind for good."),
            ("SO — Strikeout (pitcher)",
             "The pitcher successfully retires a batter by getting three strikes. "
             "A positive stat for pitchers in fantasy baseball."),
            ("IP — Innings Pitched",
             "The total number of innings a pitcher throws. "
             "An out equals ⅓ of an inning (e.g. 6.2 IP = 6 innings + 2 outs)."),
            ("SV — Save",
             "A relief pitcher earns a Save when they successfully finish a win "
             "under specific conditions (e.g. entering with a lead of 3 or fewer runs)."),
            ("ERA — Earned Run Average",
             "ERA = (Earned Runs × 9) ÷ Innings Pitched. "
             "Measures how many runs a pitcher allows per 9 innings. "
             "Lower is better. An ERA under 3.00 is considered excellent."),
        ]
        for title, body in pitching:
            _section(parent, title, body, indent=True)

    def _build_scoring(self, parent: ctk.CTkScrollableFrame) -> None:
        """Populate the Scoring System tab using the injected weight data.

        Reads from ``self._batting_weights`` and ``self._pitching_weights``
        rather than importing ``ScoreEngine`` directly, so the displayed
        values always reflect whatever weights were passed at construction.

        Args:
            parent: The scrollable frame inside the tab.
        """
        _heading(parent, "How Fantasy Points are Calculated")
        _body(parent,
              "Each real-world statistic is multiplied by a weight to produce fantasy points. "
              "Your team's total is the sum of all your players' individual point contributions.")

        _heading(parent, "Batting Weights")
        _score_table(parent, ["Stat", "Points per Unit"], [
            (stat, f"{w:+.1f} pts")
            for stat, w in self._batting_weights.items()
        ])

        _heading(parent, "Pitching Weights")
        _score_table(parent, ["Stat", "Points per Unit"], [
            (stat, f"{w:+.1f} pts")
            for stat, w in self._pitching_weights.items()
        ])

        _heading(parent, "ERA Bonus")
        _body(parent,
              f"If a pitcher's ERA is below {self._era_bonus_threshold:.2f}, "
              f"they receive a bonus of +{self._era_bonus:.1f} pts on top of their other stats.\n"
              "This rewards elite pitching performance.")

        _heading(parent, "Example Calculation")
        _body(parent,
              "Aaron Judge (OF, NYY) — 2024 season:\n"
              "  58 HR  × +4.0 = +232.0 pts\n"
              "  144 RBI × +1.0 = +144.0 pts\n"
              "  133 R   × +1.0 = +133.0 pts\n"
              "  10 SB   × +2.0 =  +20.0 pts\n"
              "  162 H   × +1.0 = +162.0 pts\n"
              "  171 SO  × −1.0 = −171.0 pts\n"
              "  ─────────────────────────────\n"
              "  Total fantasy points ≈ 520.0 pts")


# ---------------------------------------------------------------------------
# Module-level rendering helpers
# ---------------------------------------------------------------------------

def _heading(parent: ctk.CTkScrollableFrame, text: str) -> None:
    """Render an accented section heading label inside *parent*.

    Args:
        parent: The scrollable container to pack the label into.
        text: The heading text to display.
    """
    ctk.CTkLabel(
        parent,
        text=text,
        font=("Segoe UI", 17, "bold"),
        text_color=ACCENT,
        anchor="w",
    ).pack(fill="x", padx=16, pady=(16, 4))


def _body(parent: ctk.CTkScrollableFrame, text: str) -> None:
    """Render a body paragraph label inside *parent*.

    Args:
        parent: The scrollable container to pack the label into.
        text: The paragraph text to display.
    """
    ctk.CTkLabel(
        parent,
        text=text,
        font=("Segoe UI", 13),
        text_color=TEXT_SECONDARY,
        anchor="w",
        justify="left",
        wraplength=640,
    ).pack(fill="x", padx=16, pady=(0, 8))


def _section(
    parent: ctk.CTkScrollableFrame,
    title: str,
    body: str,
    indent: bool = False,
) -> None:
    """Render a titled section with a heading and a body paragraph.

    Args:
        parent: The scrollable container to pack labels into.
        title: Bold section title text.
        body: Paragraph text displayed below the title.
        indent: When ``True``, adds extra left padding to indicate that this
            section is a sub-item of the surrounding content.
    """
    left = 32 if indent else 16
    ctk.CTkLabel(
        parent,
        text=title,
        font=("Segoe UI", 14, "bold"),
        text_color=TEXT_PRIMARY,
        anchor="w",
    ).pack(fill="x", padx=left, pady=(12, 2))
    ctk.CTkLabel(
        parent,
        text=body,
        font=("Segoe UI", 13),
        text_color=TEXT_SECONDARY,
        anchor="w",
        justify="left",
        wraplength=620,
    ).pack(fill="x", padx=left + 4, pady=(0, 4))


def _score_table(
    parent: ctk.CTkScrollableFrame,
    headers: list[str],
    rows: list[tuple],
) -> None:
    """Render a two-column scoring reference table.

    Args:
        parent: The scrollable container to pack the table into.
        headers: A two-element list of column header strings.
        rows: A list of ``(stat_name, pts_string)`` tuples, one per table row.
    """
    table = ctk.CTkFrame(parent, fg_color="#0f1b2d", corner_radius=8)
    table.pack(fill="x", padx=16, pady=(4, 8))
    table.grid_columnconfigure(0, weight=1)
    table.grid_columnconfigure(1, weight=1)

    for col, h in enumerate(headers):
        ctk.CTkLabel(
            table, text=h,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=col, sticky="w", padx=14, pady=(8, 4))

    for r, (stat, pts) in enumerate(rows, start=1):
        color = ACCENT if "+" in pts else "#6a6a8a"
        ctk.CTkLabel(
            table, text=stat,
            font=("Segoe UI", 13),
            text_color=TEXT_PRIMARY,
        ).grid(row=r, column=0, sticky="w", padx=14, pady=3)
        ctk.CTkLabel(
            table, text=pts,
            font=("Segoe UI", 13, "bold"),
            text_color=color,
        ).grid(row=r, column=1, sticky="w", padx=14, pady=3)

    # Visual divider at the bottom of the table.
    ctk.CTkFrame(table, height=1, fg_color="#2a2d3e", corner_radius=0).grid(
        row=len(rows) + 1, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8)
    )
