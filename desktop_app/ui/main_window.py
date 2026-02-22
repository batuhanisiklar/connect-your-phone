"""
Ana Pencere — Remote Phone Control
=====================================
PyQt6 ile hazırlanmış, AnyDesk benzeri telefon kontrol arayüzü.
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFrame, QStatusBar,
    QSplitter, QGroupBox, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPixmap

from desktop_app.config import AppMeta, ServerDefaults, Network, Ui, AndroidKeyCodes
from desktop_app.ui.screen_widget import ScreenWidget
from desktop_app.network.ws_client import WsClient
from desktop_app.network.mjpeg_receiver import MjpegReceiver

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Ana uygulama penceresi."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(AppMeta.WINDOW_TITLE)
        self.setMinimumSize(AppMeta.MIN_WIDTH, AppMeta.MIN_HEIGHT)
        self.resize(AppMeta.DEFAULT_WIDTH, AppMeta.DEFAULT_HEIGHT)

        self._ws_client = WsClient()
        self._mjpeg = MjpegReceiver()
        self._connected = False
        self._camera_active = False

        self._setup_style()
        self._build_ui()
        self._connect_signals()

        self._heartbeat = QTimer(self)
        self._heartbeat.setInterval(Network.HEARTBEAT_INTERVAL_MS)
        self._heartbeat.timeout.connect(self._ws_client.send_heartbeat)

    # ─── STYLE ────────────────────────────────────────────────────────────────

    def _setup_style(self):
        u = Ui
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {u.BG_MAIN};
                color: {u.TEXT_PRIMARY};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }}
            QGroupBox {{
                border: 1px solid {u.BORDER};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: {u.ACCENT_GROUP};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            QLineEdit {{
                background-color: {u.BG_INPUT};
                border: 1px solid {u.BORDER_INPUT};
                border-radius: 6px;
                padding: 6px 10px;
                color: {u.TEXT_INPUT};
                selection-background-color: #4a4aaa;
            }}
            QLineEdit:focus {{
                border: 1px solid {u.BORDER_FOCUS};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton#btn_connect {{
                background-color: {u.BTN_CONNECT_BG};
                color: white;
                border: none;
            }}
            QPushButton#btn_connect:hover {{ background-color: {u.BTN_CONNECT_HOVER}; }}
            QPushButton#btn_connect:pressed {{ background-color: {u.BTN_CONNECT_PRESSED}; }}

            QPushButton#btn_disconnect {{
                background-color: {u.BTN_DISCONNECT_BG};
                color: white;
                border: none;
            }}
            QPushButton#btn_disconnect:hover {{ background-color: {u.BTN_DISCONNECT_HOVER}; }}

            QPushButton.control_btn {{
                background-color: {u.BTN_CONTROL_BG};
                color: #b0b0e0;
                border: 1px solid {u.BTN_CONTROL_BORDER};
                padding: 10px;
            }}
            QPushButton.control_btn:hover {{
                background-color: {u.BTN_CONTROL_HOVER_BG};
                border-color: {u.BTN_CONTROL_HOVER_BORDER};
                color: white;
            }}
            QPushButton.control_btn:pressed {{ background-color: #111130; }}

            QPushButton#btn_camera_on {{
                background-color: {u.BTN_CAM_ON_BG};
                color: #80dd80;
                border: 1px solid {u.BTN_CAM_ON_BORDER};
                padding: 10px;
                border-radius: 6px;
            }}
            QPushButton#btn_camera_on:hover {{ background-color: {u.BTN_CAM_ON_BORDER}; }}
            QPushButton#btn_camera_on:checked {{
                background-color: {u.BTN_CAM_ON_BORDER};
                border-color: #50cc50;
            }}

            QPushButton#btn_camera_off {{
                background-color: {u.BTN_CAM_OFF_BG};
                color: #dd8080;
                border: 1px solid {u.BTN_CAM_OFF_BORDER};
                padding: 10px;
                border-radius: 6px;
            }}
            QPushButton#btn_camera_off:hover {{ background-color: {u.BTN_CAM_OFF_BORDER}; }}

            QStatusBar {{
                background-color: {u.STATUS_BAR_BG};
                color: {u.TEXT_MUTED};
                border-top: 1px solid {u.BORDER};
            }}
            QSplitter::handle {{
                background-color: {u.SPLITTER_HANDLE_BG};
                width: 2px;
            }}
        """)

    # ─── UI BUILD ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(self._build_header())

        # Ana içerik (splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(12, 8, 12, 8)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_screen_area())
        splitter.setSizes([Ui.SPLITTER_LEFT_SIZE, Ui.SPLITTER_RIGHT_SIZE])
        root.addWidget(splitter, stretch=1)

        self._status_bar = QStatusBar()
        self._status_bar.showMessage(Ui.MSG_WAITING)
        self.setStatusBar(self._status_bar)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(Ui.HEADER_HEIGHT)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {Ui.BG_HEADER_START}, stop:1 {Ui.BG_HEADER_END});
                border-bottom: 1px solid {Ui.BORDER};
            }}
        """)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 0, 20, 0)

        title = QLabel(AppMeta.WINDOW_TITLE)
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Ui.ACCENT};")
        lay.addWidget(title)
        lay.addStretch()

        self._lbl_status_dot = QLabel("⬤")
        self._lbl_status_dot.setStyleSheet(f"font-size: 14px; color: {Ui.TEXT_DISCONNECTED};")
        self._lbl_status_text = QLabel("Bağlı değil")
        self._lbl_status_text.setStyleSheet(f"color: {Ui.TEXT_DISCONNECTED};")
        lay.addWidget(self._lbl_status_dot)
        lay.addWidget(self._lbl_status_text)
        return header

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(Ui.LEFT_PANEL_WIDTH)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(12)

        grp_conn = QGroupBox("Bağlantı")
        conn_lay = QVBoxLayout(grp_conn)
        conn_lay.setSpacing(8)

        conn_lay.addWidget(QLabel("Sunucu Adresi:"))
        self._inp_server = QLineEdit(ServerDefaults.DEFAULT_URL)
        self._inp_server.setReadOnly(True)
        self._inp_server.setEnabled(False)
        self._inp_server.setPlaceholderText(ServerDefaults.PLACEHOLDER)
        self._inp_server.setToolTip(ServerDefaults.TOOLTIP)
        conn_lay.addWidget(self._inp_server)

        conn_lay.addWidget(QLabel(f"Bağlantı Kodu ({ServerDefaults.CODE_LENGTH} hane):"))
        self._inp_code = QLineEdit()
        self._inp_code.setPlaceholderText(Ui.PLACEHOLDER_CODE)
        self._inp_code.setMaxLength(ServerDefaults.CODE_LENGTH)
        conn_lay.addWidget(self._inp_code)

        btn_row = QHBoxLayout()
        self._btn_connect = QPushButton("🔌 Bağlan")
        self._btn_connect.setObjectName("btn_connect")
        self._btn_disconnect = QPushButton("✖ Kes")
        self._btn_disconnect.setObjectName("btn_disconnect")
        self._btn_disconnect.setEnabled(False)
        btn_row.addWidget(self._btn_connect)
        btn_row.addWidget(self._btn_disconnect)
        conn_lay.addLayout(btn_row)
        lay.addWidget(grp_conn)

        # Kamera grubu
        grp_cam = QGroupBox("Kamera")
        cam_lay = QVBoxLayout(grp_cam)
        self._btn_cam_on = QPushButton("📷 Kamera Aç")
        self._btn_cam_on.setObjectName("btn_camera_on")
        self._btn_cam_on.setEnabled(False)
        self._btn_cam_off = QPushButton("🚫 Kamera Kapat")
        self._btn_cam_off.setObjectName("btn_camera_off")
        self._btn_cam_off.setEnabled(False)
        cam_lay.addWidget(self._btn_cam_on)
        cam_lay.addWidget(self._btn_cam_off)
        lay.addWidget(grp_cam)

        grp_keys = QGroupBox("Tuş Kontrolleri")
        keys_lay = QGridLayout(grp_keys)
        keys_lay.setSpacing(6)
        key_codes = AndroidKeyCodes.as_mapping()
        self._key_buttons = []
        for text, row, col, key_id in AndroidKeyCodes.button_specs():
            btn = QPushButton(text)
            btn.setProperty("class", "control_btn")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Ui.BTN_CONTROL_BG};
                    color: #b0b0e0;
                    border: 1px solid {Ui.BTN_CONTROL_BORDER};
                    padding: 8px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {Ui.BTN_CONTROL_HOVER_BG};
                    color: white;
                }}
                QPushButton:disabled {{ color: #444466; border-color: #222244; }}
            """)
            btn.clicked.connect(lambda _, k=key_codes[key_id]: self._ws_client.send_key_event(k))
            btn.setEnabled(False)
            self._key_buttons.append(btn)
            keys_lay.addWidget(btn, row, col)
        lay.addWidget(grp_keys)

        # Bilgi kutusu
        grp_info = QGroupBox("Nasıl Kullanılır?")
        info_lay = QVBoxLayout(grp_info)
        info_text = QLabel(
            "1. Sunucu adresini girin\n"
            "2. Telefon uygulamasındaki\n"
            "   6 haneli kodu girin\n"
            "3. 'Bağlan' butonuna tıklayın\n"
            "4. Telefon ekranı sağda görünür\n"
            "5. Ekrana tıklayarak kontrol\n"
            "   edebilirsiniz"
        )
        info_text.setStyleSheet("color: #7070a0; font-size: 11px; line-height: 160%;")
        info_text.setWordWrap(True)
        info_lay.addWidget(info_text)
        lay.addWidget(grp_info)

        lay.addStretch()
        return panel

    def _build_screen_area(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(4, 4, 4, 4)

        label = QLabel("Telefon Ekranı")
        label.setStyleSheet("color: #6060aa; font-size: 11px; margin-bottom: 4px;")
        lay.addWidget(label)

        self._screen = ScreenWidget()
        lay.addWidget(self._screen, stretch=1)

        # Koordinat göstergesi
        self._lbl_coords = QLabel("—")
        self._lbl_coords.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_coords.setStyleSheet("color: #444466; font-size: 10px;")
        lay.addWidget(self._lbl_coords)

        return container

    # ─── SIGNALS ──────────────────────────────────────────────────────────────

    def _connect_signals(self):
        # Butonlar
        self._btn_connect.clicked.connect(self._on_connect)
        self._btn_disconnect.clicked.connect(self._on_disconnect)
        self._btn_cam_on.clicked.connect(self._on_camera_on)
        self._btn_cam_off.clicked.connect(self._on_camera_off)

        # WsClient sinyalleri
        self._ws_client.connected.connect(self._on_ws_connected)
        self._ws_client.disconnected.connect(self._on_ws_disconnected)
        self._ws_client.paired.connect(self._on_paired)
        self._ws_client.peer_disconnected.connect(self._on_peer_disconnected)
        self._ws_client.error_occurred.connect(self._on_error)
        # WebSocket üzerinden gelen kamera/ekran frame'leri
        self._ws_client.frame_received.connect(self._on_frame_received)

        # MJPEG sinyalleri
        self._mjpeg.frame_ready.connect(self._screen.set_frame)
        self._mjpeg.error_occurred.connect(self._on_mjpeg_error)
        self._mjpeg.stream_stopped.connect(self._on_stream_stopped)

        # Ekran dokunma olayları
        self._screen.touch_event.connect(self._on_touch)
        self._screen.swipe_event.connect(self._on_swipe)

    # ─── SLOTS ────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_connect(self):
        server = self._inp_server.text().strip()
        code = self._inp_code.text().strip()
        if not server or not code:
            self._set_status(Ui.MSG_SERVER_AND_CODE_REQUIRED, error=True)
            return
        if len(code) != ServerDefaults.CODE_LENGTH or not code.isdigit():
            self._set_status(Ui.MSG_CODE_MUST_BE_6_DIGITS, error=True)
            return
        # URL'yi normalize et: ws:// veya wss:// yoksa ekle
        if not (server.startswith("ws://") or server.startswith("wss://")):
            server = "ws://" + server
        self._inp_server.setText(server)

        self._btn_connect.setEnabled(False)
        self._set_status(Ui.MSG_CONNECTING)
        self._ws_client.connect_to_server(server, code)

    @pyqtSlot()
    def _on_disconnect(self):
        self._mjpeg.stop()
        self._ws_client.disconnect()
        self._set_connected(False)
        self._screen.clear_frame()

    @pyqtSlot()
    def _on_ws_connected(self):
        self._set_status(Ui.MSG_SERVER_CONNECTED)
        self._btn_disconnect.setEnabled(True)

    @pyqtSlot(str)
    def _on_ws_disconnected(self, reason: str):
        self._set_connected(False)
        if "10060" in reason or "timed out" in reason.lower() or "failed to respond" in reason.lower():
            self._set_status(Ui.MSG_DISCONNECT_TIMEOUT, error=True)
        else:
            self._set_status(f"Bağlantı kesildi — {reason}", error=True)
        self._btn_connect.setEnabled(True)
        self._screen.clear_frame()

    @pyqtSlot(str)
    def _on_paired(self, stream_url: str):
        """Telefon ile eşleşildi; stream URL'si alındıysa MJPEG'i başlat."""
        self._set_connected(True)
        if stream_url and stream_url.startswith("http"):
            # Sadece geçerli HTTP URL'leri için MJPEG'i dene
            # Emülatör IP'leri (10.0.2.x) veya 0.0.0.0 erişilemez, bu yüzden atla
            if "0.0.0.0" not in stream_url and "10.0.2." not in stream_url:
                try:
                    self._mjpeg.start(stream_url)
                    self._set_status(f"🟢 Bağlandı | Stream: {stream_url}")
                except Exception as e:
                    # MJPEG başlatılamazsa WebSocket frame'lerine güven
                    self._set_status(f"🟢 Bağlandı (WebSocket modu) | HTTP stream erişilemedi: {e}")
            else:
                # Emülatör veya geçersiz IP - sadece WebSocket kullan
                self._set_status(Ui.MSG_PAIRED_WS)
        else:
            self._set_status(Ui.MSG_PAIRED_WS)

    @pyqtSlot()
    def _on_peer_disconnected(self):
        self._mjpeg.stop()
        self._screen.clear_frame()
        self._set_connected(False)
        self._set_status(Ui.MSG_PEER_DISCONNECTED, error=True)

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._set_status(f"Hata: {msg}", error=True)

    @pyqtSlot(QPixmap)
    def _on_frame_received(self, pixmap: QPixmap):
        """WebSocket üzerinden frame geldiğinde çağrılır."""
        print(f"🎯 MainWindow._on_frame_received çağrıldı: {pixmap.width()}x{pixmap.height()}")
        logger.debug(f"Frame alındı: {pixmap.width()}x{pixmap.height()}")
        self._screen.set_frame(pixmap)

    @pyqtSlot(str)
    def _on_mjpeg_error(self, error_msg: str):
        """MJPEG stream hatası - WebSocket aktifse sadece bilgilendir."""
        if self._connected:
            # WebSocket bağlantısı aktifse, MJPEG hatası kritik değil
            # Sadece bilgilendirme mesajı göster, hata olarak gösterme
            self._set_status(f"🟢 Bağlandı (WebSocket modu) | HTTP stream erişilemedi")
        else:
            # WebSocket de kapalıysa gerçek bir hata
            self._set_status(f"Stream hatası: {error_msg}", error=True)

    @pyqtSlot()
    def _on_stream_stopped(self):
        # MJPEG stream durdu ama WebSocket hala aktif olabilir
        # Ekranı temizleme - WebSocket frame'leri gelmeye devam edebilir
        # Sadece durumu güncelle, hata olarak gösterme
        if self._connected:
            self._set_status("🟢 Bağlandı (WebSocket modu) | HTTP stream durdu, WebSocket aktif")
        else:
            self._screen.clear_frame()
            self._set_status(Ui.MSG_STREAM_STOPPED, error=True)

    @pyqtSlot()
    def _on_camera_on(self):
        self._ws_client.send_camera_on()
        self._camera_active = True
        self._set_status(Ui.MSG_CAMERA_ON)

    @pyqtSlot()
    def _on_camera_off(self):
        self._ws_client.send_camera_off()
        self._camera_active = False
        self._set_status(Ui.MSG_CAMERA_OFF)

    @pyqtSlot(float, float)
    def _on_touch(self, x: float, y: float):
        self._ws_client.send_touch(x, y)
        self._lbl_coords.setText(f"Dokunma: ({x:.3f}, {y:.3f})")

    @pyqtSlot(float, float, float, float)
    def _on_swipe(self, x1, y1, x2, y2):
        self._ws_client.send_swipe(x1, y1, x2, y2)
        self._lbl_coords.setText(f"Kaydırma: ({x1:.2f},{y1:.2f}) → ({x2:.2f},{y2:.2f})")

    # ─── HELPER ───────────────────────────────────────────────────────────────

    def _set_connected(self, connected: bool):
        self._connected = connected
        color = Ui.TEXT_SUCCESS if connected else Ui.TEXT_DISCONNECTED
        text = "Bağlandı" if connected else "Bağlı değil"
        self._lbl_status_dot.setStyleSheet(f"font-size: 14px; color: {color};")
        self._lbl_status_text.setStyleSheet(f"color: {color};")
        self._lbl_status_text.setText(text)

        for btn in [self._btn_cam_on, self._btn_cam_off, *self._key_buttons]:
            btn.setEnabled(connected)
        self._btn_connect.setEnabled(not connected)
        self._btn_disconnect.setEnabled(connected)

        if connected:
            self._heartbeat.start()
        else:
            self._heartbeat.stop()

    def _set_status(self, msg: str, error: bool = False):
        color = Ui.TEXT_ERROR if error else Ui.TEXT_MUTED
        self._status_bar.setStyleSheet(f"color: {color};")
        self._status_bar.showMessage(msg)

    def closeEvent(self, event):
        self._mjpeg.stop()
        self._ws_client.disconnect()
        super().closeEvent(event)
