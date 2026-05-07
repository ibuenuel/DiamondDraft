from __future__ import annotations

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


def card_frame(parent: ctk.CTkBaseClass, radius: int = _RADIUS, **kw) -> ctk.CTkFrame:
    """A rounded, dark-panel container — the main building block for all screens."""
    return ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=radius, **kw)


def accent_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command,
    width: int = 180,
    state: str = "normal",
) -> ctk.CTkButton:
    """Primary action button in the brand accent colour."""
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
    """Secondary / navigation button in a muted dark-blue."""
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
    """
    Hierarchical heading label.
    level 1 → large accent title   (screens)
    level 2 → medium white subhead (section titles)
    level 3 → small muted caption  (hints / subtitles)
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
    """Standard body / status text label."""
    return ctk.CTkLabel(
        parent,
        text=text,
        textvariable=textvariable,
        font=("Segoe UI", 11),
        text_color=color,
        **kw,
    )


def separator(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    """1-pixel horizontal divider line."""
    return ctk.CTkFrame(parent, height=2, fg_color="#2a2d3e", corner_radius=0)
