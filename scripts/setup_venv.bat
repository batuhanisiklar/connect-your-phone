@echo off
REM Remote Phone Control - Windows sanal ortam kurulumu
REM Proje kök dizininde çalıştırın: scripts\setup_venv.bat

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" (
    echo .venv zaten mevcut.
    echo Etkinlestirmek icin: .venv\Scripts\activate
    exit /b 0
)

echo Python sanal ortami olusturuluyor: .venv
python -m venv .venv
if errorlevel 1 (
    echo HATA: venv olusturulamadi. Python yuklu oldugundan emin olun.
    exit /b 1
)

echo Bagimliliklari yukleniyor...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo HATA: pip install basarisiz.
    exit /b 1
)

echo.
echo Kurulum tamamlandi.
echo Sanal ortami etkinlestirmek icin:  .venv\Scripts\activate
echo Desktop uygulama:                  python desktop_app\main.py
echo Signaling sunucu:                 python signaling_server\server.py
exit /b 0
