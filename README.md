# Remote Phone Control

AnyDesk benzeri, bilgisayardan Android telefonu uzaktan kontrol etme projesi.

---

## 📁 Proje Yapısı

```
bitirme/
├── requirements.txt       # Tüm Python bağımlılıkları (kök)
├── .venv/                 # Sanal ortam (scripts ile oluşturulur)
├── scripts/
│   ├── setup_venv.bat     # Windows: .venv oluşturur
│   └── setup_venv.sh      # Linux/macOS: .venv oluşturur
├── signaling_server/      # Python WebSocket sunucu
│   ├── config/            # constants.py (PORT, mesaj tipleri)
│   └── server.py
├── desktop_app/           # PyQt6 masaüstü uygulaması
│   ├── config/            # constants.py (sunucu, ağ, UI, tuş kodları)
│   ├── network/           # ws_client, mjpeg_receiver
│   ├── ui/                # main_window, screen_widget
│   ├── requirements.txt
│   └── main.py
└── mobile_app/            # Native Kotlin Android
```

---

## 🚀 Kurulum & Çalıştırma

### 0. Sanal ortam (.venv) — Önerilen

Proje kökünde tek bir sanal ortam kullanın:

**Windows:**
```powershell
scripts\setup_venv.bat
.venv\Scripts\activate
```

**Linux/macOS:**
```bash
chmod +x scripts/setup_venv.sh
./scripts/setup_venv.sh
source .venv/bin/activate
```

Bundan sonra `python desktop_app/main.py` ve `python signaling_server/server.py` aynı `.venv` ile çalışır.

### 1. Signaling Sunucusu

```powershell
# .venv aktifse doğrudan:
python signaling_server/server.py

# veya signaling_server içinden:
cd signaling_server
pip install -r requirements.txt
python server.py
```

**Cloud Deploy (Ücretsiz):**
- [Render.com](https://render.com) → New Web Service → `server.py`
- Start command: `python server.py`
- Deploy sonrası URL'yi not edin: `wss://xxx.onrender.com`

---

### 2. Desktop App (PC)

```powershell
# .venv aktifse proje kökünden:
python desktop_app/main.py

# veya desktop_app içinden:
cd desktop_app
pip install -r requirements.txt
python main.py
```

- Açılan pencerede **Sunucu Adresi** alanına Render URL'nizi yazın
- Telefon uygulamasının gösterdiği **6 haneli kodu** girin
- **Bağlan** butonuna tıklayın

---

### 3. Android App (Telefon)

1. **Android Studio**'yu açın
2. `mobile_app/` klasörünü açın (Open Project)
3. Gradle sync tamamlanmasını bekleyin
4. Telefonu USB ile bağlayın ve **Run** butonuna basın
5. Uygulamayı açın — 6 haneli kod görünür

#### İlk Kurulumda (Bir Kez):
- **Erişilebilirlik izni:** Ayarlar → Erişilebilirlik → Remote Control → Etkinleştir
- Ekran kaydı: Uygulama açılınca otomatik izin ister

---

## 🔌 Bağlantı Akışı

```
1. Telefon → Signaling Server'a bağlanır, 6 haneli kod üretir
2. PC → Sunucuya bağlanır, kodu girer → eşleşme sağlanır
3. Telefon → Ekran yayınını başlatır (MJPEG / HTTP)
4. PC → Stream URL'sini alır, ekranı gösterir
5. PC'ye tıklanınca → Sinyal → Telefon → Dokunma olayı
```

---

## ⚙️ Yapılandırma

### Sunucu URL'sini Güncelleme

**Desktop App** → `desktop_app/ui/main_window.py` → `DEFAULT_SERVER`

**Android App** → `MainActivity.kt` → `SIGNALING_URL`

---

## 📝 Özellikler

| Özellik | Durum |
|---|---|
| Ekran Yayını (MJPEG) | ✅ |
| Kamera Aç/Kapat | ✅ |
| Dokunma Kontrolü | ✅ (Erişilebilirlik gerektirir) |
| Kaydırma (Swipe) | ✅ |
| Sistem Tuşları (Back, Home, Vol) | ✅ |
| İnternet Üzerinden Bağlantı | ✅ |
| 6 Haneli Eşleştirme Kodu | ✅ |

---

## 🛠 Teknolojiler

- **Desktop:** Python 3.11+, PyQt6, websocket-client, requests
- **Mobile:** Kotlin, CameraX, MediaProjection, OkHttp, NanoHTTPD
- **Signaling:** Python asyncio + websockets
