"""Entry point for ``python -m diamond_draft``.

Configures the root logger at WARNING level so that only significant events
appear in the terminal during normal gameplay, then hands control to the
CustomTkinter event loop.

Example::

    python -m diamond_draft
"""
from __future__ import annotations

import logging

from diamond_draft.gui.app import App

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

App().mainloop()
