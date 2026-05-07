# Project S.A.R.A.

Synthetic Adaptive Responsive Assistant

Project S.A.R.A. is a Python-based virtual assistant with artificial intelligence features, speech recognition, text-to-speech, local memory, and basic system actions.

This project was developed with AI assistance and may contain errors, limitations, or unexpected behavior. Review the code before using it in important environments or publishing new releases.

Portuguese documentation is available in [README_ptbr.md](README_ptbr.md).

## Features

- Text chat with local conversation history.
- Voice commands through a microphone.
- Spoken responses with text-to-speech.
- Piper TTS as the default local speech provider, with Edge TTS as fallback.
- Groq integration for AI responses.
- Simple mood analysis based on the conversation.
- Local memory for preferences, notes, and conversations.
- System actions such as showing time/date, opening applications, searching the web, and playing music.
- Graphical interface with a visualizer/HUD.

## Requirements

- Python 3.9 or later.
- Microphone, for voice commands.
- Groq API key, for AI responses.
- Piper TTS installed locally, for offline speech generation.

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd Project-S.A.R.A/sara_assistant
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure your API key and local TTS.

Copy `.env.example` to `.env` and add your key:

```env
GROQ_API_KEY=your_key_here
TTS_PROVIDER=piper
PIPER_TTS_COMMAND=piper
PIPER_TTS_MODEL=path/to/your/piper-model.onnx
PIPER_TTS_CONFIG=path/to/your/piper-model.onnx.json
```

Or set it as an environment variable:

Windows PowerShell:

```powershell
$env:GROQ_API_KEY = "your_key_here"
$env:TTS_PROVIDER = "piper"
$env:PIPER_TTS_MODEL = "path\to\your\piper-model.onnx"
$env:PIPER_TTS_CONFIG = "path\to\your\piper-model.onnx.json"
```

Linux/macOS:

```bash
export GROQ_API_KEY="your_key_here"
export TTS_PROVIDER="piper"
export PIPER_TTS_MODEL="path/to/your/piper-model.onnx"
export PIPER_TTS_CONFIG="path/to/your/piper-model.onnx.json"
```

5. Run the application:

```bash
python main.py
```

## Usage

### Text Commands

Type a message in the input field and press Enter or use the send button.

### Voice Commands

Use the microphone button, speak your command, and wait for processing.

### Command Examples

| Command | Example |
| --- | --- |
| Show time | "What time is it?" |
| Show date | "What day is today?" |
| Open app | "Open Notepad" |
| Search | "Search for Python" |
| Music | "Play a Queen song" |

## Project Structure

```text
sara_assistant/
|-- main.py                  # Main entry point
|-- config.py                # General configuration
|-- pet_gui.py               # Graphical interface
|-- hud_visualizer.py        # Visualizer/HUD
|-- hud_config.py            # HUD configuration
|-- requirements.txt         # Dependencies
|-- modules/
|   |-- ai_assistant.py      # Groq integration
|   |-- memory.py            # Local memory
|   |-- mood_analyzer.py     # Mood analysis
|   |-- notifications.py     # Notifications
|   |-- proactive.py         # Proactive behavior
|   |-- speech_to_text.py    # Speech recognition
|   |-- system_actions.py    # System actions
|   |-- system_monitor.py    # System monitoring
|   `-- text_to_speech.py    # Text-to-speech
|-- assets/                  # Visual assets
`-- data/                    # Local runtime data
```

## Build an Executable

To create a standalone executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="Project-SARA" main.py
```

The executable will be created in the `dist/` directory.

## Docker

This project is not distributed with Docker by default.

Project S.A.R.A. is a desktop assistant that interacts directly with the operating system. It may use a graphical interface, microphone input, audio output, browser access, local applications, keyboard/mouse events, and Windows-specific APIs. Inside a Docker container, this type of access is limited, complex, or unavailable, which would reduce the assistant's core functionality.

Docker may be useful in the future for separated components, such as a local API, memory services, databases, background processing, or integrations that do not depend on the user's desktop. The main application should run natively on the operating system to keep proper access to local resources.

## Configuration

Edit `config.py` to customize:

- `PET_CONFIG`: name, colors, and visual parameters kept for internal compatibility.
- `VOICE_CONFIG`: speech speed, volume, and voice.
- `AI_CONFIG`: AI model and parameters.
- `MOOD_COLORS`: colors used for mood states.

## Security

Do not commit `.env` files, local histories, personal memories, or API keys to GitHub. Before publishing, confirm that `GROQ_API_KEY` and other secrets do not appear in versioned files.

## Troubleshooting

### Microphone Does Not Work

- Check whether PyAudio is installed correctly.
- On Windows, Visual C++ Build Tools may be required.
- Confirm that the operating system has granted microphone access.

### API Error

- Check whether `GROQ_API_KEY` is configured.
- Confirm that the key is active in the Groq dashboard.

### No Sound

- Check the system audio settings.
- Try another voice or output device.

## License

MIT License. See the repository license file, if available.

## Contributions

Contributions are welcome through issues and pull requests.
