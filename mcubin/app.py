import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from alembic.config import Config
from alembic import command

from mcubin.ui.theme import STYLESHEET
from mcubin.ui.main_window import MainWindow


def run_migrations():
    alembic_cfg = Config(Path(__file__).parent.parent / "alembic.ini")
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).parent.parent / "alembic")
    )
    command.upgrade(alembic_cfg, "head")


def main():
    run_migrations()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger("mcubin").setLevel(logging.DEBUG)
    logging.getLogger("mcubin").debug("logging initialised")

    app = QApplication(sys.argv)
    app.setApplicationName("mcubin")
    app.setStyleSheet(STYLESHEET)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
