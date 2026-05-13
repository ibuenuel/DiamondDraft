"""Themed modal dialogs that match the DiamondDraft dark UI.

Replaces all ``tkinter.messagebox`` calls so that every dialog renders inside
the app's own colour palette instead of the OS-native chrome.

Public API mirrors the four ``messagebox`` functions used across the codebase:

- :func:`show_info`    — informational message with an OK button
- :func:`show_error`   — error message with an OK button
- :func:`show_warning` — warning message with an OK button
- :func:`ask_yes_no`   — confirmation prompt, returns ``True`` / ``False``
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Colour palette (duplicated from app.py to avoid circular imports)
# ---------------------------------------------------------------------------
_DARK_BG      = "#1a1a2e"
_PANEL_BG     = "#16213e"
_BORDER       = "#2a2a4a"
_ACCENT       = "#e94560"
_TEXT_PRIMARY  = "#eaeaea"
_TEXT_SECONDARY = "#a0a0b0"

# Icon glyph + colour per dialog type
_ICON_INFO    = ("ℹ",  "#4a9eff")
_ICON_SUCCESS = ("✓",  "#4caf50")
_ICON_WARNING = ("⚠",  "#f0a500")
_ICON_ERROR   = ("✕",  _ACCENT)


class _Dialog(ctk.CTkToplevel):
    """Internal base class for all themed modal dialogs.

    Builds a self-contained popup with an icon badge, title, body message,
    and one or two action buttons.  Blocks the parent event loop via
    ``grab_set`` + ``wait_window`` so callers can treat the dialog as
    synchronous (same contract as ``tkinter.messagebox``).

    Args:
        parent:  The owning widget (used for centering and grab scope).
        title:   Window title and bold heading shown inside the dialog.
        message: Body text shown below the heading.
        icon:    ``(glyph, colour)`` tuple that defines the badge.
        buttons: Sequence of ``(label, value)`` pairs.  The value for the
                 clicked button is stored in ``self.result``.
    """

    _WIDTH  = 420
    _HEIGHT = 210

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        message: str,
        icon: tuple[str, str],
        buttons: list[tuple[str, any]],
    ) -> None:
        super().__init__(parent, fg_color=_DARK_BG)
        self.title("")
        self.resizable(False, False)
        self.overrideredirect(False)

        self.result: any = None
        self._buttons_cfg = buttons

        self._build(title, message, icon, buttons)
        self._center(parent)

        self.grab_set()
        self.focus_force()
        self.wait_window()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(
        self,
        title: str,
        message: str,
        icon: tuple[str, str],
        buttons: list[tuple[str, any]],
    ) -> None:
        glyph, colour = icon

        # Outer padding container
        outer = ctk.CTkFrame(self, fg_color=_DARK_BG)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        # ── Top section: icon + text ─────────────────────────────────
        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(24, 12))

        # Icon badge
        badge = ctk.CTkFrame(
            top,
            width=48,
            height=48,
            corner_radius=24,
            fg_color=_PANEL_BG,
            border_width=2,
            border_color=colour,
        )
        badge.pack_propagate(False)
        badge.pack(side="left", padx=(0, 18))

        ctk.CTkLabel(
            badge,
            text=glyph,
            font=("Segoe UI", 20, "bold"),
            text_color=colour,
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Title + message
        text_col = ctk.CTkFrame(top, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            text_col,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=_TEXT_PRIMARY,
            anchor="w",
            justify="left",
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_col,
            text=message,
            font=("Segoe UI", 12),
            text_color=_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=self._WIDTH - 120,
        ).pack(anchor="w", pady=(4, 0))

        # ── Divider ──────────────────────────────────────────────────
        ctk.CTkFrame(outer, height=1, fg_color=_BORDER).pack(fill="x", padx=0)

        # ── Button row ───────────────────────────────────────────────
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=16)

        # Primary button always on the right; secondary (No/Cancel) on left
        for i, (label, value) in enumerate(reversed(buttons)):
            is_primary = (i == 0)
            btn = ctk.CTkButton(
                btn_row,
                text=label,
                width=100,
                height=34,
                corner_radius=8,
                fg_color=_ACCENT if is_primary else _PANEL_BG,
                hover_color="#c73652" if is_primary else "#1e2a50",
                text_color=_TEXT_PRIMARY,
                font=("Segoe UI", 12, "bold" if is_primary else "normal"),
                command=lambda v=value: self._close(v),
            )
            btn.pack(side="right", padx=(8, 0))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _close(self, value: any) -> None:
        self.result = value
        self.grab_release()
        self.destroy()

    def _center(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
        except tk.TclError:
            px, py, pw, ph = 200, 200, 800, 600

        x = px + (pw - self._WIDTH) // 2
        y = py + (ph - self._HEIGHT) // 2
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}+{x}+{y}")


# ---------------------------------------------------------------------------
# Public convenience functions
# ---------------------------------------------------------------------------

def show_info(parent: tk.Widget, title: str, message: str) -> None:
    """Display a themed informational dialog and wait for the user to dismiss it.

    Args:
        parent:  Owning widget; the dialog is centered over it.
        title:   Bold heading displayed inside the dialog.
        message: Body text with additional detail.
    """
    _Dialog(parent, title, message, _ICON_INFO, [("OK", True)])


def show_success(parent: tk.Widget, title: str, message: str) -> None:
    """Display a themed success dialog and wait for the user to dismiss it.

    Args:
        parent:  Owning widget; the dialog is centered over it.
        title:   Bold heading displayed inside the dialog.
        message: Body text with additional detail.
    """
    _Dialog(parent, title, message, _ICON_SUCCESS, [("OK", True)])


def show_error(parent: tk.Widget, title: str, message: str) -> None:
    """Display a themed error dialog and wait for the user to dismiss it.

    Args:
        parent:  Owning widget; the dialog is centered over it.
        title:   Bold heading displayed inside the dialog.
        message: Body text with additional detail.
    """
    _Dialog(parent, title, message, _ICON_ERROR, [("OK", True)])


def show_warning(parent: tk.Widget, title: str, message: str) -> None:
    """Display a themed warning dialog and wait for the user to dismiss it.

    Args:
        parent:  Owning widget; the dialog is centered over it.
        title:   Bold heading displayed inside the dialog.
        message: Body text with additional detail.
    """
    _Dialog(parent, title, message, _ICON_WARNING, [("OK", True)])


def ask_yes_no(parent: tk.Widget, title: str, message: str) -> bool:
    """Display a themed yes/no confirmation dialog and return the user's choice.

    Args:
        parent:  Owning widget; the dialog is centered over it.
        title:   Bold heading displayed inside the dialog.
        message: Body text describing what the user is confirming.

    Returns:
        ``True`` if the user clicked **Yes**, ``False`` if they clicked **No**.
    """
    dlg = _Dialog(parent, title, message, _ICON_WARNING, [("No", False), ("Yes", True)])
    return bool(dlg.result)
