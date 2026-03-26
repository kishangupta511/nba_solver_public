"""Application entry point: creates QApplication, applies theme, launches MainWindow."""

import os
import sys


def launch_app():
    """Create and run the NBA Fantasy Optimizer GUI.

    The working directory is set to the project root (public_solver/)
    so that relative paths like 'data/' and 'solver_settings.json' resolve
    correctly regardless of where the script is invoked from.
    """
    # Ensure working directory is <project>/public_solver/
    src_dir = os.path.dirname(os.path.abspath(__file__))  # gui/
    project_src = os.path.dirname(src_dir)                 # src/
    project_root = os.path.dirname(project_src)            # public_solver/
    os.chdir(project_root)

    # Add src/ to sys.path so 'from solve import ...' works
    if project_src not in sys.path:
        sys.path.insert(0, project_src)

    from PySide6.QtWidgets import QApplication
    from gui.utils.constants import APP_STYLESHEET

    app = QApplication.instance() or QApplication(sys.argv)

    # Self-contained theme -- no qt-material dependency
    app.setStyleSheet(APP_STYLESHEET)

    from gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch_app()
