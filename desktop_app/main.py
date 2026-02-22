"""
Remote Phone Control — Desktop App Giriş Noktası
"""

import sys
import os
import logging

# desktop_app/ içinden python main.py ile çalıştırıldığında
# parent dizini (bitirme/) path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from desktop_app.ui.main_window import MainWindow
from desktop_app.config import AppMeta

# Logging yapılandırması
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(AppMeta.NAME)
    app.setApplicationVersion(AppMeta.VERSION)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
