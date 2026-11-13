"""
Main entry point for Image to PDF Converter.
"""

import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from gui import MainWindow


def main():
    # Enable high-DPI scaling for crisp UI on high-resolution displays
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Image to PDF Converter")
    app.setOrganizationName("PDFTools")

    # Set icon if present
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
