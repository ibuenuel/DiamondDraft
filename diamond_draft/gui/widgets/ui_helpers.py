"""Reusable UI factory functions for Diamond Draft.

Provides lightweight helper functions that create styled widgets so that
screens and dialogs never inline raw styling parameters. All visual constants
(colours, radii, fonts) are sourced from ``app.py`` — changing a colour there
propagates everywhere automatically.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from diamond_draft.gui.app import (
    ACCENT,
    BUTTON_BG,
    BUTTON_HOVER,
    DARK_BG,
    PANEL_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

_RADIUS = 12


def attach_scrollbar(tree: ttk.Treeview, parent: tk.Widget) -> ttk.Scrollbar:
    """Attach a vertical scrollbar to *tree* and pack both into *parent*.

    Eliminates the four-line setup pattern that was previously duplicated
    across ``DraftScreen``, ``WaiverScreen``, ``LineupScreen``, and
    ``StandingsScreen``.

    Packing order: scrollbar first (right + fill y), then tree (fill both +
    expand True). This is the canonical Treeview + Scrollbar layout in Tk.

    Args:
        tree: Any ``ttk.Treeview`` or subclass (including ``PlayerTable``).
        parent: The container widget that already has *tree* as a child.

    Returns:
        The created and wired ``ttk.Scrollbar``, in case the caller needs
        to hold a reference to it.
    """
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True)
    return vsb


def card_frame(parent: ctk.CTkBaseClass, radius: int = _RADIUS, **kw) -> ctk.CTkFrame:
    """Return a rounded, dark-panel container — the main building block for all screens.

    Args:
        parent: The parent widget.
        radius: Corner radius in pixels. Defaults to the application standard.
        **kw: Additional keyword arguments forwarded to ``CTkFrame.__init__``.

    Returns:
        A styled ``CTkFrame`` with the panel background colour.
    """
    return ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=radius, **kw)


def accent_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command,
    width: int = 180,
    state: str = "normal",
) -> ctk.CTkButton:
    """Return a primary action button styled in the brand accent colour.

    Args:
        parent: The parent widget.
        text: Button label text.
        command: Callback invoked on click.
        width: Pixel width. Defaults to 180.
        state: ``"normal"`` or ``"disabled"``.

    Returns:
        A fully configured ``CTkButton``.
    """
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        fg_color=ACCENT,
        hover_color=BUTTON_HOVER,
        text_color="#ffffff",
        corner_radius=8,
        font=("Segoe UI", 12, "bold"),
        state=state,
    )


def secondary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command,
    width: int = 140,
    state: str = "normal",
) -> ctk.CTkButton:
    """Return a secondary navigation button styled in a muted dark-blue.

    Args:
        parent: The parent widget.
        text: Button label text.
        command: Callback invoked on click.
        width: Pixel width. Defaults to 140.
        state: ``"normal"`` or ``"disabled"``.

    Returns:
        A fully configured ``CTkButton``.
    """
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        fg_color=BUTTON_BG,
        hover_color="#1a4a7a",
        text_color=TEXT_PRIMARY,
        corner_radius=8,
        font=("Segoe UI", 11),
        state=state,
    )


def heading(
    parent: ctk.CTkBaseClass,
    text: str,
    level: int = 1,
    **kw,
) -> ctk.CTkLabel:
    """Return a hierarchical heading label.

    - **Level 1** — large accent-coloured title (screen headers).
    - **Level 2** — medium white subheading (section titles).
    - **Level 3** — small muted caption (hints / subtitles).

    Args:
        parent: The parent widget.
        text: Heading text to display.
        level: Hierarchy level (1, 2, or 3). Unknown values fall back to 2.
        **kw: Additional keyword arguments forwarded to ``CTkLabel.__init__``.

    Returns:
        A styled ``CTkLabel``.
    """
    fonts = {
        1: ("Segoe UI", 22, "bold"),
        2: ("Segoe UI", 15, "bold"),
        3: ("Segoe UI", 11),
    }
    colors = {1: ACCENT, 2: TEXT_PRIMARY, 3: TEXT_SECONDARY}
    return ctk.CTkLabel(
        parent,
        text=text,
        font=fonts.get(level, fonts[2]),
        text_color=colors.get(level, TEXT_PRIMARY),
        **kw,
    )


def body_label(
    parent: ctk.CTkBaseClass,
    text: str = "",
    textvariable=None,
    color: str = TEXT_SECONDARY,
    **kw,
) -> ctk.CTkLabel:
    """Return a standard body or status text label.

    Args:
        parent: The parent widget.
        text: Static label text. Ignored when *textvariable* is provided.
        textvariable: A ``tk.StringVar`` whose value is displayed dynamically.
        color: Text colour. Defaults to the secondary text colour.
        **kw: Additional keyword arguments forwarded to ``CTkLabel.__init__``.

    Returns:
        A styled ``CTkLabel``.
    """
    return ctk.CTkLabel(
        parent,
        text=text,
        textvariable=textvariable,
        font=("Segoe UI", 11),
        text_color=color,
        **kw,
    )


def separator(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    """Return a 1-pixel horizontal divider line.

    Args:
        parent: The parent widget.

    Returns:
        A 2-pixel-tall ``CTkFrame`` styled as a thin divider.
    """
    return ctk.CTkFrame(parent, height=2, fg_color="#2a2d3e", corner_radius=0)
