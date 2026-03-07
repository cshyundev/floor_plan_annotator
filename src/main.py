import sys
import open3d as o3d
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.core.config import apply_theme

def main():
    app = QApplication(sys.argv)
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.setOrganizationName("FloorPlanAnnotator")
    QCoreApplication.setApplicationName("FloorPlanAnnotator")
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
