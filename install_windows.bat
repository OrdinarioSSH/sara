@echo off
echo ========================================
echo   Pet Assistant - Instalador Windows
echo ========================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale Python 3.9+ de python.org
    pause
    exit /b 1
)

echo [1/4] Criando ambiente virtual...
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/4] Atualizando pip...
python -m pip install --upgrade pip

echo.
echo [3/4] Instalando dependencias...
pip install customtkinter pillow anthropic SpeechRecognition pyttsx3 python-dotenv pyinstaller

echo.
echo [4/4] Instalando PyAudio (pode precisar de Visual C++)...
pip install pyaudio

echo.
echo ========================================
echo   Instalacao concluida!
echo ========================================
echo.
echo Para iniciar o Pet Assistant:
echo   1. Ative o ambiente: venv\Scripts\activate
echo   2. Configure sua API key no arquivo .env
echo   3. Execute: python main.py
echo.
echo Para criar executavel:
echo   pyinstaller --onefile --windowed --name="PetAssistant" main.py
echo.
pause
