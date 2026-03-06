import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from alembic.config import Config
from alembic import command

import mcubin.config as config
from mcubin.ui.theme import CUSTOM_STYLESHEET
from mcubin.ui.main_window import MainWindow


def run_migrations():
    alembic_cfg = Config(Path(__file__).parent.parent / "alembic.ini")
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).parent.parent / "alembic")
    )
    command.upgrade(alembic_cfg, "head")


def apply_theme(app: QApplication, theme: str) -> None:
    from qt_material import apply_stylesheet
    apply_stylesheet(app, theme=theme)
    app.setStyleSheet(app.styleSheet() + CUSTOM_STYLESHEET)


def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger("mcubin").setLevel(logging.DEBUG)

    run_migrations()

    app = QApplication(sys.argv)
    app.setApplicationName("mcubin")

    theme = config.get("theme") or "dark_blue.xml"
    apply_theme(app, theme)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
