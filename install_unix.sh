#!/bin/bash

echo "========================================"
echo "  Pet Assistant - Instalador Linux/Mac"
echo "========================================"
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python3 não encontrado!"
    echo "Instale Python 3.9+ usando seu gerenciador de pacotes"
    exit 1
fi

echo "[1/5] Instalando dependências do sistema..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    sudo apt-get update
    sudo apt-get install -y python3-dev python3-venv portaudio19-dev espeak
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew install portaudio
fi

echo ""
echo "[2/5] Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "[3/5] Atualizando pip..."
pip install --upgrade pip

echo ""
echo "[4/5] Instalando dependências Python..."
pip install customtkinter pillow anthropic SpeechRecognition pyttsx3 python-dotenv pyinstaller

echo ""
echo "[5/5] Instalando PyAudio..."
pip install pyaudio

echo ""
echo "========================================"
echo "  Instalação concluída!"
echo "========================================"
echo ""
echo "Para iniciar o Pet Assistant:"
echo "  1. Ative o ambiente: source venv/bin/activate"
echo "  2. Configure sua API key no arquivo .env"
echo "  3. Execute: python main.py"
echo ""
echo "Para criar executável:"
echo "  pyinstaller --onefile --windowed --name='PetAssistant' main.py"
echo ""
