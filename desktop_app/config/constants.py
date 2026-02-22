"""
Desktop App — Tüm sabitler ve yapılandırma değerleri.
Tek bir yerden yönetim; magic number ve stringler burada toplanır.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class AppMeta:
    """Uygulama kimlik bilgileri."""
    NAME: str = "Remote Phone Control"
    VERSION: str = "1.0.0"
    WINDOW_TITLE: str = "📱 Remote Phone Control"
    MIN_WIDTH: int = 1000
    MIN_HEIGHT: int = 700
    DEFAULT_WIDTH: int = 1200
    DEFAULT_HEIGHT: int = 780


@dataclass(frozen=True)
class ServerDefaults:
    """Signaling sunucu varsayılanları."""
    DEFAULT_URL: str = "wss://connect-your-phone.onrender.com"
    PLACEHOLDER: str = "wss://connect-your-phone.onrender.com"
    TOOLTIP: str = "Signaling sunucu adresi (Sabitlendi)"
    CODE_LENGTH: int = 6


@dataclass(frozen=True)
class Network:
    """Ağ ve WebSocket sabitleri."""
    PING_INTERVAL_SEC: int = 20
    PING_TIMEOUT_SEC: int = 10
    HEARTBEAT_INTERVAL_MS: int = 30_000
    MJPEG_REQUEST_TIMEOUT_SEC: int = 10
    MJPEG_CHUNK_SIZE: int = 4096
    JPEG_MARKER_START: bytes = b"\xff\xd8"
    JPEG_MARKER_END: bytes = b"\xff\xd9"
    MJPEG_JOIN_TIMEOUT_SEC: float = 2.0


@dataclass(frozen=True)
class Ui:
    """Arayüz boyutları, renkler ve metinler."""
    # Panel
    LEFT_PANEL_WIDTH: int = 280
    SPLITTER_LEFT_SIZE: int = 280
    SPLITTER_RIGHT_SIZE: int = 720
    HEADER_HEIGHT: int = 56
    TOUCH_THRESHOLD_PX: int = 8  # Tıklama vs kaydırma ayrımı
    COORD_PRECISION: int = 4

    # Renkler (theme)
    BG_MAIN: str = "#0f0f1a"
    BG_HEADER_START: str = "#1a1a3e"
    BG_HEADER_END: str = "#0f0f1a"
    BG_INPUT: str = "#1a1a2e"
    BG_CARD: str = "#0d0d0d"
    BORDER: str = "#2a2a4a"
    BORDER_INPUT: str = "#3a3a5e"
    BORDER_FOCUS: str = "#6060cc"
    TEXT_PRIMARY: str = "#e0e0f0"
    TEXT_INPUT: str = "#e0e0ff"
    TEXT_MUTED: str = "#8080cc"
    TEXT_ERROR: str = "#dd4444"
    TEXT_SUCCESS: str = "#44cc44"
    TEXT_DISCONNECTED: str = "#555577"
    ACCENT: str = "#9090ff"
    ACCENT_GROUP: str = "#9090c0"
    BTN_CONNECT_BG: str = "#3a3acc"
    BTN_CONNECT_HOVER: str = "#5050ee"
    BTN_CONNECT_PRESSED: str = "#2828aa"
    BTN_DISCONNECT_BG: str = "#7a1a1a"
    BTN_DISCONNECT_HOVER: str = "#aa2222"
    BTN_CONTROL_BG: str = "#1e1e3a"
    BTN_CONTROL_BORDER: str = "#3a3a6a"
    BTN_CONTROL_HOVER_BG: str = "#2e2e5a"
    BTN_CONTROL_HOVER_BORDER: str = "#6060aa"
    BTN_CAM_ON_BG: str = "#1a3a1a"
    BTN_CAM_ON_BORDER: str = "#2a5a2a"
    BTN_CAM_OFF_BG: str = "#3a1a1a"
    BTN_CAM_OFF_BORDER: str = "#5a2a2a"
    STATUS_BAR_BG: str = "#0a0a15"
    SPLITTER_HANDLE_BG: str = "#2a2a4a"
    SCREEN_BORDER: str = "#2a2a3e"
    SCREEN_PLACEHOLDER_FG: str = "#555577"

    # Mesajlar
    MSG_WAITING: str = "Bağlantı bekleniyor..."
    MSG_CONNECTING: str = "Bağlanıyor..."
    MSG_SERVER_CONNECTED: str = "Sunucuya bağlandı. Telefon bekleniyor..."
    MSG_PAIRED_WS: str = "🟢 Bağlandı (WebSocket modu) | Ekran görüntüsü WebSocket üzerinden geliyor"
    MSG_DISCONNECT_TIMEOUT: str = (
        "Bağlantı kesildi — Sunucu yanıt vermiyor. "
        "Aynı bilgisayarda sunucu çalışıyorsa ws://127.0.0.1:8765 deneyin."
    )
    MSG_PEER_DISCONNECTED: str = "Telefon bağlantısı kesildi."
    MSG_STREAM_STOPPED: str = "Stream durdu."
    MSG_CAMERA_ON: str = "Kamera açıldı"
    MSG_CAMERA_OFF: str = "Kamera kapatıldı"
    MSG_SERVER_AND_CODE_REQUIRED: str = "Sunucu adresi ve kod gerekli!"
    MSG_CODE_MUST_BE_6_DIGITS: str = "Kod 6 haneli sayı olmalı!"
    PLACEHOLDER_CODE: str = "Telefon uygulamasındaki kodu girin"


@dataclass(frozen=True)
class AndroidKeyCodes:
    """Android KeyEvent sabitleri (desktop tuş kontrolleri)."""
    BACK: int = 4
    HOME: int = 3
    RECENTS: int = 187
    VOL_UP: int = 24
    VOL_DOWN: int = 25
    POWER: int = 26

    @classmethod
    def as_mapping(cls) -> Dict[str, int]:
        return {
            "key_back": cls.BACK,
            "key_home": cls.HOME,
            "key_recents": cls.RECENTS,
            "key_vol_up": cls.VOL_UP,
            "key_vol_down": cls.VOL_DOWN,
            "key_power": cls.POWER,
        }

    @classmethod
    def button_specs(cls) -> list[Tuple[str, int, int, str]]:
        """(Metin, grid_row, grid_col, key_id)."""
        return [
            ("⬅ Geri", 0, 0, "key_back"),
            ("🏠 Ana Ekran", 0, 1, "key_home"),
            ("☰ Görevler", 1, 0, "key_recents"),
            ("🔊 Vol+", 1, 1, "key_vol_up"),
            ("🔇 Vol−", 2, 0, "key_vol_down"),
            ("🔒 Ekran", 2, 1, "key_power"),
        ]
