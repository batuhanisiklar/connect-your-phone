"""
WebSocket Signaling İstemcisi
==============================
Signaling sunucusuna bağlanır, oturum eşleşmesini yönetir ve
telefona komut (kamera aç/kapat, touch, swipe) gönderir.

Kullanım:
    client = WsClient()
    client.paired.connect(on_paired)
    client.command_received.connect(on_command)
    client.connect_to_server("wss://your-server.onrender.com", "123456")
"""

import json
import threading
import base64
import logging
import websocket
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage

from desktop_app.config import Network

logger = logging.getLogger(__name__)


class WsClient(QObject):
    """Signaling sunucusuyla ve (relay üzerinden) telefonla WebSocket haberleşmesi."""

    connected = pyqtSignal()                    # Sunucuya bağlandı
    disconnected = pyqtSignal(str)              # Bağlantı kesildi (sebep)
    paired = pyqtSignal(str)                    # Telefon ile eşleşildi (stream URL)
    peer_disconnected = pyqtSignal()            # Telefon bağlantısı kesildi
    command_received = pyqtSignal(dict)         # Telefondan komut geldi
    error_occurred = pyqtSignal(str)            # Hata mesajı
    frame_received = pyqtSignal(QPixmap)        # WebSocket üzerinden JPEG frame

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._session_code: str = ""

    # ─── PUBLIC API ────────────────────────────────────────────────────────────

    def connect_to_server(self, url: str, code: str):
        """
        Signaling sunucusuna bağlan ve verilen kod ile join isteği gönder.

        :param url:  wss://... veya ws://...
        :param code: Telefon uygulamasının gösterdiği 6 haneli kod
        """
        self._session_code = code
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(
            target=self._ws.run_forever,
            kwargs={
                "ping_interval": Network.PING_INTERVAL_SEC,
                "ping_timeout": Network.PING_TIMEOUT_SEC,
                "skip_utf8_validation": True,
            },
            daemon=True,
        )
        self._thread.start()

    def disconnect(self):
        """Bağlantıyı kapat."""
        if self._ws:
            self._ws.close()
        self._ws = None

    def send_command(self, cmd: dict):
        """Telefona komut gönder (relay üzerinden)."""
        if self._ws:
            payload = {"type": "command", **cmd}
            self._ws.send(json.dumps(payload))

    def send_touch(self, x: float, y: float):
        """Dokunma koordinatını gönder (0.0–1.0 arası normalize)."""
        self.send_command({"action": "touch", "x": x, "y": y})

    def send_swipe(self, x1: float, y1: float, x2: float, y2: float):
        """Kaydırma olayı gönder."""
        self.send_command({"action": "swipe", "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    def send_camera_on(self):
        """Kamerayı aç komutu."""
        self.send_command({"action": "camera_on"})

    def send_camera_off(self):
        """Kamerayı kapat komutu."""
        self.send_command({"action": "camera_off"})

    def send_key_event(self, key_code: int):
        """Android KeyEvent gönder."""
        self.send_command({"action": "key_event", "key_code": key_code})

    def send_heartbeat(self):
        """Keep-alive ping."""
        if self._ws:
            self._ws.send(json.dumps({"type": "heartbeat"}))

    # ─── WEBSOCKET CALLBACKS ───────────────────────────────────────────────────

    def _on_open(self, ws):
        self.connected.emit()
        # PC olarak join isteği gönder
        ws.send(json.dumps({
            "type": "join",
            "code": self._session_code,
            "role": "pc"
        }))

    def _on_message(self, ws, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            print(f"⚠️ JSON decode hatası: {raw[:100]}...")
            return

        msg_type = msg.get("type")
        if msg_type == "frame":
            print(f"📨 WebSocket mesajı alındı: type={msg_type}")
        elif msg_type:
            print(f"📨 WebSocket mesajı: type={msg_type}")

        if msg_type == "paired":
            # Telefon bağlantısı gerçekleşti; stream URL'sini relay'den alacağız
            self.paired.emit(msg.get("stream_url", ""))

        elif msg_type == "stream_info":
            # Telefon stream başlayınca URL'sini iletir
            self.paired.emit(msg.get("url", ""))

        elif msg_type == "frame":
            # Telefon WebSocket üzerinden JPEG frame gönderdi
            print(f"📥 Frame mesajı alındı!")
            try:
                data_str = msg.get("data", "")
                if not data_str:
                    print("⚠️ Frame mesajı boş data içeriyor")
                    logger.warning("Frame mesajı boş data içeriyor")
                    return
                print(f"📥 Base64 data uzunluğu: {len(data_str)} karakter")
                jpeg_bytes = base64.b64decode(data_str)
                print(f"📥 Decode edildi: {len(jpeg_bytes)} bytes JPEG")
                img = QImage()
                if img.loadFromData(jpeg_bytes, "JPEG"):
                    print(f"✅ JPEG decode başarılı: {img.width()}x{img.height()}")
                    pixmap = QPixmap.fromImage(img)
                    if pixmap.isNull():
                        print("⚠️ Pixmap null!")
                    else:
                        print(f"✅ Pixmap oluşturuldu, emit ediliyor...")
                        self.frame_received.emit(pixmap)
                        logger.debug(f"Frame alındı ve gönderildi: {len(jpeg_bytes)} bytes")
                else:
                    print("❌ JPEG decode başarısız - loadFromData False döndü")
                    logger.warning("JPEG decode başarısız")
            except Exception as e:
                print(f"❌ Frame decode hatası: {e}")
                logger.error(f"Frame decode hatası: {e}", exc_info=True)

        elif msg_type == "peer_disconnected":
            self.peer_disconnected.emit()

        elif msg_type == "command":
            self.command_received.emit(msg)

        elif msg_type == "error":
            self.error_occurred.emit(msg.get("message", "Bilinmeyen hata"))

    def _on_error(self, ws, error):
        self.error_occurred.emit(str(error))

    def _on_close(self, ws, code, msg):
        self.disconnected.emit(f"code={code}, msg={msg}")
