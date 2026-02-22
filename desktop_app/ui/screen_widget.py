"""
Ekran Görüntüsü Widget'ı
=========================
MJPEG stream'inden gelen frame'leri gösterir.
Tıklama ve sürükleme olaylarını normalize koordinatlar olarak
sinyal ile yayar (touch/swipe simülasyonu için).
"""

from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

from desktop_app.config import Ui


class ScreenWidget(QLabel):
    """
    MJPEG stream frame'lerini gösteren ve dokunma olaylarını yakalayan widget.
    
    Sinyaller:
        touch_event(x, y)           - Normalize [0,1] koordinatlarda tıklama
        swipe_event(x1,y1,x2,y2)   - Normalize koordinatlarda kaydırma
    """

    touch_event = pyqtSignal(float, float)
    swipe_event = pyqtSignal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(280, 500)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {Ui.BG_CARD};
                border: 2px solid {Ui.SCREEN_BORDER};
                border-radius: 12px;
            }}
        """)

        self._current_pixmap: QPixmap | None = None
        self._drag_start: QPoint | None = None
        self._is_streaming = False

        self._show_placeholder()

    # ─── PUBLIC ────────────────────────────────────────────────────────────────

    def set_frame(self, pixmap: QPixmap):
        """Yeni bir frame göster."""
        if pixmap is None or pixmap.isNull():
            print("⚠️ ScreenWidget.set_frame: Null veya geçersiz pixmap!")
            return
        self._current_pixmap = pixmap
        self._is_streaming = True
        self._render()
        print(f"✅ Frame gösterildi: {pixmap.width()}x{pixmap.height()}")

    def clear_frame(self):
        """Stream durduğunda placeholder göster."""
        self._current_pixmap = None
        self._is_streaming = False
        self._show_placeholder()

    # ─── MOUSE EVENTS ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start:
            end = event.pos()
            start = self._drag_start
            self._drag_start = None

            dx = abs(end.x() - start.x())
            dy = abs(end.y() - start.y())

            if dx < Ui.TOUCH_THRESHOLD_PX and dy < Ui.TOUCH_THRESHOLD_PX:
                # Tıklama
                nx, ny = self._normalize(end.x(), end.y())
                self.touch_event.emit(nx, ny)
            else:
                # Kaydırma
                nx1, ny1 = self._normalize(start.x(), start.y())
                nx2, ny2 = self._normalize(end.x(), end.y())
                self.swipe_event.emit(nx1, ny1, nx2, ny2)

    # ─── INTERNAL ──────────────────────────────────────────────────────────────

    def _normalize(self, x: int, y: int) -> tuple[float, float]:
        """Widget koordinatlarını [0,1] aralığına normalize et."""
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        p = Ui.COORD_PRECISION
        return round(x / w, p), round(y / h, p)

    def _render(self):
        """Mevcut pixmap'i widget boyutuna uyarla."""
        if self._current_pixmap:
            scaled = self._current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pixmap:
            self._render()

    def _show_placeholder(self):
        """Bağlantı bekleme ekranı."""
        ph = QPixmap(self.minimumSize())
        ph.fill(QColor(Ui.BG_CARD))
        painter = QPainter(ph)
        painter.setPen(QColor(Ui.SCREEN_PLACEHOLDER_FG))
        font = QFont("Segoe UI", 11)
        painter.setFont(font)
        painter.drawText(
            ph.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "📱 Telefon bağlantısı bekleniyor..."
        )
        painter.end()
        self.setPixmap(ph)
