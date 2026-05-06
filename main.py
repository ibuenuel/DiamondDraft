import logging

from diamond_draft.gui.app import App

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

if __name__ == "__main__":
    App().mainloop()
