"""
Remote Phone Control - Signaling Server (websockets >= 12 uyumlu)
=================================================================
Her iki taraf (PC ve Android) bu sunucuya bağlanır.

Mesaj akışı:
  Android: {"type": "register", "code": "123456", "role": "phone"}
  PC:      {"type": "join",     "code": "123456", "role": "pc"}
  Eşleşince: her iki tarafa {"type": "paired"} gönderilir.
  Sonraki mesajlar relay edilir.
"""

import asyncio
import json
import logging
import sys
import os
import http
import signal

# Proje kökünü path'e ekle (signaling_server.config için)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import websockets

from signaling_server.config import ServerConfig, MessageTypes

logging.basicConfig(
    level=logging.INFO,
    format=ServerConfig.LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# Render TCP port testleri handshake'i yarıda kestiği için `websockets.server`
# modülü ERROR seviyesinde "Error in connection handler" / "EOFError" fırlatıyor.
# Sadece bu spesifik modülün (handshake loglarını basan modül) log seviyesini
# CRITICAL yaparak Render konsolunu temiz tutuyoruz. Server çalışmaya devam edecek.
logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

# code -> {"phone": ws, "pc": ws}
sessions: dict = {}


async def process_request(connection, request):
    """
    Render'ın health check (HTTP GET/HEAD /) isteklerini yakalar ve 200 OK döndürür.
    WebSocket upgrade isteklerini (Upgrade: websocket) normal akışa bırakır.
    """
    if request.path == "/":
        # WebSocket upgrade isteği ise None dön (ws akışına geçir)
        if request.headers.get("Upgrade", "").lower() == "websocket":
            return None
        return connection.respond(http.HTTPStatus.OK, "OK\n")
    return None


async def send_json(ws, data: dict):
    await ws.send(json.dumps(data))


async def handler(ws):
    peer_code = None
    peer_role = None

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                # Olası devasa bozuk frame'leri loglamak yerine ilk 100 karakteri logla
                preview = str(raw)[:100]
                logger.warning(f"Invalid JSON received. Preview: {preview}...")
                await send_json(ws, {"type": MessageTypes.ERROR, "message": "Invalid JSON payload"})
                continue

            msg_type = msg.get("type", "")
            logger.info(f"[{msg_type}] code={msg.get('code')} role={msg.get('role')}")

            # ── REGISTER (telefon) / JOIN (PC) ──────────────────────────────
            if msg_type in (MessageTypes.REGISTER, MessageTypes.JOIN):
                code = msg.get("code", "").strip()
                role = msg.get("role", "phone" if msg_type == MessageTypes.REGISTER else "pc")

                if not code:
                    await send_json(ws, {"type": MessageTypes.ERROR, "message": "code missing"})
                    continue

                if code not in sessions:
                    sessions[code] = {}

                sessions[code][role] = ws
                peer_code = code
                peer_role = role

                ack = MessageTypes.REGISTERED if msg_type == MessageTypes.REGISTER else MessageTypes.JOINED
                await send_json(ws, {"type": ack, "code": code, "role": role})
                logger.info(f"{ack}: code={code}, role={role}")

                # İki taraf da bağlandıysa eşleştir
                s = sessions.get(code, {})
                if "phone" in s and "pc" in s:
                    await _notify_paired(code, s)
                elif msg_type == MessageTypes.JOIN:
                    await send_json(ws, {
                        "type": MessageTypes.WAITING,
                        "message": "Telefon bağlanmayı bekliyor..."
                    })

            # ── RELAY ───────────────────────────────────────────────────────
            elif msg_type in MessageTypes.RELAY_TYPES:
                if not peer_code or not peer_role:
                    await send_json(ws, {"type": MessageTypes.ERROR, "message": "Not registered"})
                    continue

                s = sessions.get(peer_code, {})
                other_role = "pc" if peer_role == "phone" else "phone"
                other_ws = s.get(other_role)

                if other_ws:
                    try:
                        await other_ws.send(json.dumps(msg))
                    except Exception:
                        await send_json(ws, {
                            "type": MessageTypes.ERROR,
                            "message": "Karşı taraf bağlantısı koptu"
                        })
                else:
                    await send_json(ws, {
                        "type": MessageTypes.ERROR,
                        "message": f"{other_role} bağlı değil"
                    })

            else:
                await send_json(ws, {"type": MessageTypes.ERROR, "message": f"Unknown: {msg_type}"})

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed: code={peer_code}, role={peer_role} ({e})")
    except Exception as e:
        logger.warning(f"Handler error: {e}")
    finally:
        # Temizlik
        if peer_code and peer_role:
            s = sessions.get(peer_code, {})
            if s.get(peer_role) is ws:
                del s[peer_role]
                logger.info(f"Removed: code={peer_code}, role={peer_role}")

                other_role = "pc" if peer_role == "phone" else "phone"
                other_ws = s.get(other_role)
                if other_ws:
                    try:
                        await send_json(other_ws, {
                            "type": MessageTypes.PEER_DISCONNECTED,
                            "role": peer_role
                        })
                    except Exception:
                        pass

            if not s:
                sessions.pop(peer_code, None)


async def _notify_paired(code: str, s: dict):
    logger.info(f"✅ Paired! code={code}")
    for role, ws in s.items():
        try:
            await send_json(ws, {"type": MessageTypes.PAIRED, "code": code, "your_role": role})
        except Exception:
            pass


async def main():
    host = ServerConfig.HOST
    port = ServerConfig.PORT
    logger.info(f"Signaling server starting on ws://{host}:{port}")

    # Graceful shutdown event
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received. Closing server...")
        stop_event.set()

    # Windows'da SIGTERM/SIGINT desteği sınırlı olabilir, try-except ile koruyalım
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_running_loop().add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        # Windows environments that don't support add_signal_handler
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())


    # Ping/Pong ve Payload limitlerini ekleyerek cloud ortamında bağlantı kopmalarını
    # ve OOM tehlikesini engelliyoruz. Render gibi platformlar 100 sn idle bağlantıyı koparır.
    async with websockets.serve(
        handler, 
        host, 
        port, 
        process_request=process_request,
        ping_interval=20,     # Her 20 saniyede bir ping gönder
        ping_timeout=20,      # 20 saniye içinde pong gelmezse bağlantıyı kapat
        max_size=5 * 1024 * 1024 # 5MB maksimum payload limiti (MJPEG/Frame transferleri için yeterli)
    ) as server:
        logger.info(f"✅ Server listening on ws://{host}:{port}")
        
        # event set edilene kadar bekle
        await stop_event.wait()
        
    logger.info("Server completely shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
