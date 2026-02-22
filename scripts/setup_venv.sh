#!/usr/bin/env bash
# Remote Phone Control - Linux/macOS sanal ortam kurulumu
# Proje kök dizininde çalıştırın: ./scripts/setup_venv.sh

set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/bin/activate" ]; then
    echo ".venv zaten mevcut."
    echo "Etkinleştirmek için: source .venv/bin/activate"
    exit 0
fi

echo "Python sanal ortamı oluşturuluyor: .venv"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Kurulum tamamlandı."
echo "Sanal ortamı etkinleştirmek için:  source .venv/bin/activate"
echo "Desktop uygulama:                  python desktop_app/main.py"
echo "Signaling sunucu:                  python signaling_server/server.py"
