"""
SARA - Sistema de Assistência e Resposta Automatizada
Interface Principal (PyQt6)
Versão 2.0 — Protocolo A.T.L.A.S.
"""
import sys
import os
import random
import base64
import time
import re
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QMenu, QDialog, QListWidget, QPushButton, QSlider,
                             QTextEdit, QLineEdit, QFileDialog, QGraphicsOpacityEffect,
                             QSystemTrayIcon, QCheckBox, QComboBox, QSpinBox, QTabWidget,
                             QGroupBox)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QTransform, QTextCursor, QIcon, QAction
from groq import Groq
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar system prompt do config
try:
    from config import ASSISTANT_SYSTEM_PROMPT
except ImportError:
    ASSISTANT_SYSTEM_PROMPT = "Você é SARA, uma assistente virtual profissional. Responda de forma concisa e direta em português brasileiro."

# --- Módulo TTS ---
try:
    import tempfile
    import uuid
    import pygame
    from modules.text_to_speech import synthesize_to_file
    pygame.mixer.init()
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    print("[SARA] TTS indisponivel. Instale: pip install dashscope edge-tts pygame")

# --- Módulo STT ---
try:
    import speech_recognition as sr
    HAS_STT = True
except ImportError:
    HAS_STT = False
    print("[SARA] STT indisponível. Instale: pip install SpeechRecognition pyaudio")

# --- Módulo Monitoramento ---
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[SARA] Monitor de sistema indisponível. Instale: pip install psutil")

# Importar configurações e módulos internos
try:
    from config import WAKE_WORD_CONFIG, PROACTIVE_CONFIG, PROACTIVE_MESSAGES
except ImportError:
    WAKE_WORD_CONFIG = {"wake_words": ["sara"], "timeout": 10}
    PROACTIVE_CONFIG = {"pause_reminder_interval": 45, "check_system_interval": 5,
                        "greeting_enabled": True, "random_tips_enabled": True, "tips_interval": 30}
    PROACTIVE_MESSAGES = {
        "pause_reminders": ["Pausa recomendada."],
        "productivity_tips": ["Dica de produtividade disponível."],
        "morning_greetings": ["Bom dia, Senhor."],
        "afternoon_greetings": ["Boa tarde, Senhor."],
        "evening_greetings": ["Boa noite, Senhor."],
        "cpu_high": ["CPU em uso elevado."],
        "memory_high": ["Memória em uso elevado."],
        "idle_messages": ["Sistemas em standby."],
        "attention_seeking": ["Alguma tarefa pendente, Senhor?"],
    }

# Importar módulos internos
try:
    from modules.memory import MemoryManager
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False
    print("[SARA] Módulo de memória indisponível.")

# Módulo de ações do sistema (controle do PC)
try:
    from modules.system_actions import SystemActions
    HAS_SYSTEM_ACTIONS = True
except ImportError:
    HAS_SYSTEM_ACTIONS = False
    print("[SARA] Módulo de ações do sistema indisponível.")

# HUD Visualizer
try:
    from hud_visualizer import HUDVisualizer
    HAS_HUD = True
except ImportError:
    HAS_HUD = False
    print("[SARA] HUD Visualizer indisponível.")


# ==================== UTILS ====================

def _clean_for_tts(text: str) -> str:
    """Remove formatação Markdown e caracteres especiais antes do TTS.
    Transforma o texto em fala natural, sem artefatos de formatação."""
    import re as _re
    # Remove tags [MEMORIZAR: ...] e [CORRIGIR: ...]
    text = _re.sub(r'\[MEMORIZAR:[^\]]*\]', '', text)
    text = _re.sub(r'\[CORRIGIR:[^\]]*\]', '', text)
    # Remove blocos de código ```...```
    text = _re.sub(r'```[\s\S]*?```', '', text)
    # Remove código inline `...`
    text = _re.sub(r'`[^`]+`', '', text)
    # Remove headers markdown (## , ### , etc.)
    text = _re.sub(r'#{1,6}\s*', '', text)
    # Remove negrito/itálico (**texto**, *texto*, __texto__, _texto_)
    text = _re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = _re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
    # Remove links markdown [texto](url) -> texto
    text = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove listas numeradas (1. item, 2. item)
    text = _re.sub(r'^\s*\d+[\.\)]\s+', '', text, flags=_re.MULTILINE)
    # Remove listas markdown (- item, * item, + item)
    text = _re.sub(r'^\s*[-*+]\s+', '', text, flags=_re.MULTILINE)
    # Remove [STATUS / PRÓXIMOS PASSOS] e similares
    text = _re.sub(r'\[STATUS[^\]]*\]', '', text, flags=_re.IGNORECASE)
    text = _re.sub(r'\[PRÓXIMOS?\s+PASSOS?\]', '', text, flags=_re.IGNORECASE)
    # Remove colchetes, chaves e caracteres especiais de formatação
    text = _re.sub(r'[\[\]{}~>|]', '', text)
    # Remove "---" ou "===" separadores
    text = _re.sub(r'[-=]{3,}', '', text)
    # Remove URLs soltas
    text = _re.sub(r'https?://\S+', '', text)
    # Converte quebras de linha em espaço (fluxo natural)
    text = _re.sub(r'\n+', ' ', text)
    # Remove múltiplos espaços e pontuação duplicada
    text = _re.sub(r'\s{2,}', ' ', text)
    text = _re.sub(r'\.{2,}', '.', text)
    text = _re.sub(r'\.\s*\.', '.', text)
    return text.strip()


def _extract_memories(text: str) -> list:
    """Extrai tags [MEMORIZAR: ...] do texto da IA."""
    import re as _re
    return _re.findall(r'\[MEMORIZAR:\s*([^\]]+)\]', text)


def _detect_user_correction(text: str) -> bool:
    """Detecta se o usuário está corrigindo a SARA."""
    text_lower = text.lower().strip()
    correction_indicators = [
        "não era isso", "nao era isso", "errado", "tá errado", "ta errado",
        "está errado", "esta errado", "não foi isso", "nao foi isso",
        "não é isso", "nao e isso", "você errou", "voce errou",
        "errou", "não entendeu", "nao entendeu", "entendeu errado",
        "não era o que", "nao era o que", "eu quis dizer", "eu disse",
        "não pedi isso", "nao pedi isso", "não era pra", "nao era pra",
        "fez errado", "fez de errado", "não é assim", "nao e assim",
        "tá incorreto", "ta incorreto", "incorreto", "tá mal", "ta mal",
        "não queria isso", "nao queria isso", "queria que",
        "era para", "era pra", "deveria ter", "deveria",
        "não assim", "nao assim", "isso não", "isso nao",
        "não, eu", "nao, eu", "não, quero", "nao, quero",
        "refaz", "refaça", "corrige", "corrija", "corrigir",
    ]
    return any(kw in text_lower for kw in correction_indicators)


def _extract_corrections(text: str) -> list:
    """Extrai tags [CORRIGIR: ...] do texto da IA."""
    import re as _re
    return _re.findall(r'\[CORRIGIR:\s*([^\]]+)\]', text)


# ==================== THREADS ====================

class TTSThread(QThread):
    """Thread para Text-to-Speech com suporte a visualizador de áudio."""
    finished = pyqtSignal()
    speaking_started = pyqtSignal(object)  # Emite AudioAmplitudeExtractor para o HUD
    speaking_stopped = pyqtSignal()

    def __init__(self, text, voice="Cherry", speed=1.0):
        super().__init__()
        self.text = _clean_for_tts(text)
        self.voice = voice
        self.speed = speed

    def run(self):
        if not HAS_TTS or not self.text:
            self.finished.emit()
            return
        try:
            temp_file = os.path.join(tempfile.gettempdir(), f"sara_speech_{uuid.uuid4().hex[:8]}.mp3")
            rate = f"+{int((self.speed - 1) * 100)}%" if self.speed >= 1 else f"{int((self.speed - 1) * 100)}%"
            synthesize_to_file(self.text, temp_file, voice=self.voice, rate=rate)

            # Usa Sound + Channel para ter acesso ao PCM raw (visualizador)
            sound = pygame.mixer.Sound(temp_file)
            try:
                from audio_analyzer import AudioAmplitudeExtractor
                raw = sound.get_raw()
                extractor = AudioAmplitudeExtractor(raw)
                self.speaking_started.emit(extractor)
            except Exception:
                self.speaking_started.emit(None)

            channel = pygame.mixer.Channel(0)
            channel.play(sound)
            while channel.get_busy():
                pygame.time.wait(30)

            self.speaking_stopped.emit()
            try:
                os.remove(temp_file)
            except:
                pass
        except Exception as e:
            print(f"Erro TTS: {e}")
        self.finished.emit()

def _transcribe_audio(audio_data, groq_client=None):
    """Transcreve áudio usando Groq Whisper (preciso) ou Google Speech (fallback).

    Args:
        audio_data: sr.AudioData capturado pelo microfone
        groq_client: instância do Groq client (se disponível)
    Returns:
        texto transcrito ou None
    """
    # Tenta Groq Whisper primeiro (whisper-large-v3-turbo — rápido e preciso)
    if groq_client:
        try:
            wav_bytes = audio_data.get_wav_data()
            import io
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "audio.wav"

            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=audio_file,
                language="pt",
                response_format="text",
            )
            text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
            if text:
                return text
        except Exception as e:
            print(f"[STT] Groq Whisper falhou, usando fallback: {e}")

    # Fallback: Google Speech
    try:
        recognizer = sr.Recognizer()
        text = recognizer.recognize_google(audio_data, language="pt-BR")
        return text.strip() if text else None
    except (sr.UnknownValueError, sr.RequestError):
        return None


class WakeWordThread(QThread):
    """Thread de escuta contínua — só responde quando "Sara" é mencionada.

    Usa Groq Whisper (whisper-large-v3-turbo) para transcrição precisa.
    Fallback para Google Speech se Groq indisponível.
    """
    wake_word_detected = pyqtSignal()
    command_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    listening_for_command = pyqtSignal()

    def __init__(self, groq_client=None):
        super().__init__()
        self.running = True
        self.wake_words = [w.lower() for w in WAKE_WORD_CONFIG.get("wake_words", ["sara"])]
        self.timeout = WAKE_WORD_CONFIG.get("timeout", 10)
        self.paused = False
        self.groq_client = groq_client

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def run(self):
        if not HAS_STT:
            return

        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        # Configuração otimizada do recognizer
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.5)

        engine = "Groq Whisper" if self.groq_client else "Google Speech"
        print(f"[STT] Motor de transcrição: {engine}")

        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue

            try:
                with mic as source:
                    self.status_changed.emit("listening")
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=15)

                self.status_changed.emit("processing")

                text = _transcribe_audio(audio, self.groq_client)
                if not text:
                    self.status_changed.emit("idle")
                    continue

                text = text.lower().strip()
                print(f"[STT] Capturado: {text}")

                # Só processa se "Sara" for mencionada em qualquer parte da frase
                wake_detected = any(wake in text for wake in self.wake_words)

                if not wake_detected:
                    self.status_changed.emit("idle")
                    continue

                # Remove wake word do texto (funciona em qualquer posição)
                command = text
                for wake in self.wake_words:
                    command = command.replace(wake, "").strip()
                command = command.strip(" ,;.!?")

                if command:
                    self.command_received.emit(command)
                else:
                    # Só wake word — aguarda comando completo
                    self.wake_word_detected.emit()
                    self.listening_for_command.emit()
                    time.sleep(0.5)

                    with mic as source:
                        audio = recognizer.listen(source, timeout=self.timeout, phrase_time_limit=30)

                    command = _transcribe_audio(audio, self.groq_client)
                    if command:
                        self.command_received.emit(command)

                self.status_changed.emit("idle")

            except sr.WaitTimeoutError:
                self.status_changed.emit("idle")
            except Exception as e:
                print(f"[STT] Erro: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False


class STTThread(QThread):
    """Thread para Speech-to-Text único (botão mic do chat). Usa Groq Whisper."""
    result = pyqtSignal(str)

    def __init__(self, groq_client=None):
        super().__init__()
        self.groq_client = groq_client

    def run(self):
        if not HAS_STT:
            self.result.emit("")
            return

        try:
            recognizer = sr.Recognizer()
            mic = sr.Microphone()
            recognizer.pause_threshold = 0.8

            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=30)

            text = _transcribe_audio(audio, self.groq_client)
            self.result.emit(text if text else "")
        except Exception as e:
            print(f"[STT] Erro: {e}")
            self.result.emit("")


class VoiceResponseThread(QThread):
    """Thread para processar comando de voz e gerar resposta com baixa latência.

    Pipeline otimizado:
    - Modelo 8B instant (4-5x mais rápido que 70B)
    - Streaming da API (começa a processar texto assim que chega)
    - TTS pipeline: 1ª frase toca sem bloquear stream, restante em bloco contínuo
    - Sound+Channel para visualizador de áudio (get_raw)
    """
    response_ready = pyqtSignal(str)
    finished_speaking = pyqtSignal()
    memory_extracted = pyqtSignal(str)
    speaking_started = pyqtSignal(object)  # AudioAmplitudeExtractor para HUD

    def __init__(self, client, command, voice="Cherry", speed=1.0, memory_manager=None):
        super().__init__()
        self.client = client
        self.command = command
        self.voice = voice
        self.speed = speed
        self.memory = memory_manager

    def run(self):
        if not self.client:
            self.response_ready.emit("API não configurada.")
            self.finished_speaking.emit()
            return

        try:
            rate = f"+{int((self.speed - 1) * 100)}%" if self.speed >= 1 else f"{int((self.speed - 1) * 100)}%"

            # Monta contexto de memórias e correções para a IA
            memory_context = ""
            if self.memory:
                memories = self.memory.get_memories()
                if memories:
                    memory_context = "\n\nMEMÓRIAS DO OPERADOR:\n"
                    for m in memories[-15:]:
                        memory_context += f"- {m['content']}\n"

                # Correções aprendidas
                corrections = self.memory.get_relevant_corrections(self.command, limit=8)
                if corrections:
                    memory_context += "\nCORREÇÕES APRENDIDAS (erros passados — NÃO repita):\n"
                    for c in corrections:
                        memory_context += f"- Pedido: \"{c['user_said']}\" → Erro: \"{c['sara_did'][:80]}\" → Correto: \"{c['correction']}\"\n"

            # Detecta se o usuário está corrigindo a SARA
            is_correction = _detect_user_correction(self.command)
            correction_context = ""
            if is_correction and self.memory:
                recent = self.memory.get_recent_conversations(4)
                if recent:
                    correction_context = "\n\nATENÇÃO: O Operador está te CORRIGINDO. Ele está insatisfeito com sua última resposta/ação. Analise o que você fez errado, reconheça o erro com elegância, e responda corretamente. Ao final, adicione uma tag [CORRIGIR: descrição breve do que você errou e o que deveria ter feito] para que você aprenda e não repita."
                    correction_context += "\nÚltimas mensagens para contexto:\n"
                    for entry in recent:
                        role = "Operador" if entry['role'] == 'user' else "SARA"
                        correction_context += f"  {role}: {entry['content'][:150]}\n"

            # Streaming da API com modelo rápido
            messages = [
                {
                    "role": "system",
                    "content": ASSISTANT_SYSTEM_PROMPT + memory_context + correction_context + "\n\nIMPORTANTE: Esta é uma interação por VOZ. Responda de forma CURTA e DIRETA (máximo 2-3 frases). Fale naturalmente como uma pessoa falaria, sem listas, sem marcadores, sem formatação."
                },
                {"role": "user", "content": self.command}
            ]

            stream = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                stream=True,
            )

            # Pipeline:
            # 1. Detecta primeira frase → gera áudio → toca (NÃO bloqueia stream)
            # 2. Continua recebendo tokens enquanto fala
            # 3. Ao final, junta restante em UM bloco de TTS (sem pausas artificiais)
            full_response = ""
            sentence_buffer = ""
            remaining_sentences = []
            first_sound = None
            first_channel = None
            first_temp = None
            first_sentence_playing = False

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    token = delta.content
                    full_response += token
                    sentence_buffer += token

                    if any(sentence_buffer.rstrip().endswith(p) for p in [".", "!", "?", ";"]):
                        sentence = sentence_buffer.strip()
                        if sentence:
                            clean = _clean_for_tts(sentence)
                            if clean and not first_sentence_playing and HAS_TTS:
                                first_temp = self._generate_audio_file(clean, rate)
                                first_sound = pygame.mixer.Sound(first_temp)
                                # Emite dados para o HUD visualizer
                                self._emit_audio_data(first_sound)
                                first_channel = pygame.mixer.Channel(0)
                                first_channel.play(first_sound)
                                first_sentence_playing = True
                                self.response_ready.emit(full_response)
                            elif clean:
                                remaining_sentences.append(clean)
                        sentence_buffer = ""

            # Texto restante no buffer
            leftover = sentence_buffer.strip()
            if leftover:
                clean = _clean_for_tts(leftover)
                if clean:
                    remaining_sentences.append(clean)

            # Emite resposta completa na UI
            print(f"[SARA] Resposta: {full_response}")
            self.response_ready.emit(full_response)

            # Extrai e salva memórias
            mems = _extract_memories(full_response)
            for mem in mems:
                print(f"[SARA] Memória salva: {mem}")
                if self.memory:
                    self.memory.add_memory(mem, source="voz")
                self.memory_extracted.emit(mem)

            # Extrai e salva correções aprendidas
            corrs = _extract_corrections(full_response)
            for corr in corrs:
                print(f"[SARA] Correção aprendida: {corr}")
                if self.memory:
                    # Busca a última resposta da SARA como "o que ela fez errado"
                    recent = self.memory.get_recent_conversations(2)
                    sara_did = ""
                    for entry in reversed(recent):
                        if entry['role'] == 'assistant':
                            sara_did = entry['content'][:200]
                            break
                    self.memory.add_correction(
                        user_said=self.command,
                        sara_did=sara_did,
                        correction=corr,
                        source="voz"
                    )

            if self.memory:
                self.memory.add_conversation("user", self.command)
                self.memory.add_conversation("assistant", full_response)
                self.memory.save_all()

            # Espera a primeira frase terminar de tocar
            if first_channel:
                while first_channel.get_busy():
                    pygame.time.wait(30)
            if first_temp:
                try:
                    os.remove(first_temp)
                except:
                    pass

            # Fala o restante como UM BLOCO CONTÍNUO
            if HAS_TTS and remaining_sentences:
                combined_text = " ".join(remaining_sentences)
                self._speak_block(combined_text, rate)
            elif HAS_TTS and not first_sentence_playing and full_response.strip():
                clean_all = _clean_for_tts(full_response.strip())
                if clean_all:
                    self._speak_block(clean_all, rate)

        except Exception as e:
            print(f"Erro ao processar voz: {e}")
            self.response_ready.emit(f"Erro: {str(e)}")

        self.finished_speaking.emit()

    def _emit_audio_data(self, sound):
        """Extrai PCM e emite para o visualizador HUD."""
        try:
            from audio_analyzer import AudioAmplitudeExtractor
            raw = sound.get_raw()
            if raw and len(raw) > 0:
                extractor = AudioAmplitudeExtractor(raw)
                self.speaking_started.emit(extractor)
            else:
                self.speaking_started.emit(None)
        except Exception:
            self.speaking_started.emit(None)

    def _generate_audio_file(self, text, rate):
        """Gera arquivo MP3 do TTS e retorna o path."""
        temp_file = os.path.join(tempfile.gettempdir(), f"sara_voice_{uuid.uuid4().hex[:8]}.mp3")
        synthesize_to_file(text, temp_file, voice=self.voice, rate=rate)
        return temp_file

    def _speak_block(self, text, rate):
        """Gera TTS e reproduz um bloco de texto contínuo via Sound+Channel."""
        try:
            temp_file = self._generate_audio_file(text, rate)
            sound = pygame.mixer.Sound(temp_file)
            self._emit_audio_data(sound)
            channel = pygame.mixer.Channel(0)
            channel.play(sound)
            while channel.get_busy():
                pygame.time.wait(30)
            try:
                os.remove(temp_file)
            except:
                pass
        except Exception as e:
            print(f"[TTS] Erro ao falar bloco: {e}")

class ChatThread(QThread):
    """Thread para requisições à API"""
    response_ready = pyqtSignal(str)

    def __init__(self, client, messages, image_path=None):
        super().__init__()
        self.client = client
        self.messages = messages
        self.image_path = image_path

    def run(self):
        try:
            if self.image_path:
                model = "llama-3.2-90b-vision-preview"
                with open(self.image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")

                ext = self.image_path.lower().split('.')[-1]
                media_types = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
                media_type = media_types.get(ext, "image/png")

                last_msg = self.messages[-1]["content"]
                self.messages[-1]["content"] = [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                    {"type": "text", "text": last_msg if last_msg else "Analise esta imagem."}
                ]
            else:
                model = "llama-3.3-70b-versatile"

            completion = self.client.chat.completions.create(
                model=model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=1024,
            )
            response = completion.choices[0].message.content
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"Erro: {str(e)}")


# ==================== SPEECH BUBBLE ====================

class SimpleSpeechBubble(QWidget):
    """Balão de fala simples"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMaximumWidth(250)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.95);
                color: #333;
                border: 2px solid #3498db;
                border-radius: 15px;
                padding: 12px 16px;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.finished.connect(self.hide)

    def show_message(self, text, duration=4000, position=None):
        self.label.setText(text)
        self.adjustSize()

        if position:
            screen = QApplication.primaryScreen().geometry()
            x = max(10, min(position.x() - self.width() // 2 + 75, screen.width() - self.width() - 10))
            y = max(10, position.y() - self.height() - 15)
            self.move(x, y)

        self.opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()

        self.hide_timer.start(duration)

    def fade_out(self):
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()


# ==================== CHAT WINDOW ====================

class ChatWindow(QDialog):
    """Janela de Chat com Markdown básico"""
    def __init__(self, parent=None, initial_message=None, memory_manager=None):
        super().__init__(parent)
        self.parent_pet = parent
        self.memory = memory_manager
        self.setWindowTitle("SARA — Terminal")
        self.setFixedSize(450, 500)
        self.pending_image = None
        self.tts_enabled = True
        self.tts_voice = "Cherry"
        self.tts_speed = 1.0

        if self.memory:
            self.tts_enabled = self.memory.preferences.tts_enabled
            self.tts_voice = self.memory.preferences.tts_voice
            self.tts_speed = self.memory.preferences.tts_speed

        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None

        # Monta system prompt com contexto de memória
        system_content = ASSISTANT_SYSTEM_PROMPT
        if self.memory:
            context = self.memory.get_context_for_ai()
            if context:
                system_content += f"\n\n## CONTEXTO OPERACIONAL\n{context}"

        self.messages = [{
            "role": "system",
            "content": system_content
        }]

        self.setup_ui()

        if not self.client:
            self.add_message("SARA", "API key não configurada. Verifique o arquivo .env.")
        elif initial_message:
            self.input_field.setText(initial_message)
            self.send_message()
        else:
            self.add_message("SARA", "Pronta para operar, Senhor. Em que posso ser útil?")

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.image_label = QLabel("")
        self.image_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        layout.addWidget(self.image_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #eee;
                border: 2px solid #3498db;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.chat_display)

        control_layout = QHBoxLayout()

        self.btn_tts = QPushButton("🔊" if self.tts_enabled else "🔇")
        self.btn_tts.setFixedSize(30, 30)
        self.btn_tts.setCheckable(True)
        self.btn_tts.setChecked(self.tts_enabled)
        self.btn_tts.clicked.connect(self.toggle_tts)
        self.btn_tts.setToolTip("TTS On/Off")
        control_layout.addWidget(self.btn_tts)

        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setFixedSize(30, 30)
        self.btn_clear.clicked.connect(self.clear_chat)
        self.btn_clear.setToolTip("Limpar conversa")
        control_layout.addWidget(self.btn_clear)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        input_layout = QHBoxLayout()

        self.btn_image = QPushButton("📷")
        self.btn_image.setFixedSize(35, 35)
        self.btn_image.clicked.connect(self.select_image)
        self.btn_image.setStyleSheet("QPushButton { background-color: #9b59b6; color: white; border-radius: 5px; }")
        input_layout.addWidget(self.btn_image)

        self.btn_voice = QPushButton("🎤")
        self.btn_voice.setFixedSize(35, 35)
        self.btn_voice.clicked.connect(self.start_voice_input)
        self.btn_voice.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 5px; }")
        input_layout.addWidget(self.btn_voice)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Digite ou fale...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 2px solid #3498db;
                border-radius: 5px;
                font-size: 12px;
                background-color: #2c3e50;
                color: white;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("➤")
        self.send_button.setFixedSize(40, 35)
        self.send_button.setStyleSheet("QPushButton { background-color: #3498db; color: white; border-radius: 5px; font-weight: bold; }")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)
        self.setLayout(layout)

    def toggle_tts(self):
        self.tts_enabled = self.btn_tts.isChecked()
        self.btn_tts.setText("🔊" if self.tts_enabled else "🔇")
        if self.memory:
            self.memory.update_preferences(tts_enabled=self.tts_enabled)

    def clear_chat(self):
        self.chat_display.clear()
        self.messages = [self.messages[0]]  # Mantém só system prompt
        self.add_message("SARA", "Histórico limpo. Contexto reiniciado.")

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Imagem", "", "Imagens (*.png *.jpg *.jpeg);;Todos (*.*)")
        if file_path:
            self.pending_image = file_path
            self.image_label.setText(f"Anexo: {os.path.basename(file_path)[:30]}")
            self.btn_image.setText("[OK]")

    def clear_pending_image(self):
        self.pending_image = None
        self.image_label.setText("")
        self.btn_image.setText("📷")

    def start_voice_input(self):
        if not HAS_STT:
            self.add_message("SARA", "Módulo de reconhecimento de voz não disponível.")
            return

        self.btn_voice.setEnabled(False)
        self.status_label.setText("Ouvindo...")

        self.stt_thread = STTThread(groq_client=self.client)
        self.stt_thread.result.connect(self.handle_voice_result)
        self.stt_thread.start()

    def handle_voice_result(self, text):
        self.btn_voice.setEnabled(True)
        self.status_label.setText("")

        if text:
            self.input_field.setText(text)
            self.send_message()
        else:
            self.add_message("Sistema", "Reconhecimento falhou. Tente novamente.")

    def format_message(self, text):
        """Formata mensagem com markdown básico"""
        # Código em bloco ```
        text = re.sub(r'```(\w+)?\n(.*?)```', r'<pre style="background-color: #2d2d2d; padding: 8px; border-radius: 5px; font-family: monospace; font-size: 11px; color: #f8f8f2;">\2</pre>', text, flags=re.DOTALL)

        # Código inline `code`
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: #2d2d2d; padding: 2px 5px; border-radius: 3px; font-family: monospace; color: #f8f8f2;">\1</code>', text)

        # Negrito **text**
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)

        # Itálico *text*
        text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)

        # Links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #3498db;">\1</a>', text)

        return text

    def add_message(self, sender, message):
        formatted = self.format_message(message)

        if sender == "Você":
            self.chat_display.append(f"<b style='color: #3498db;'>{sender}:</b> {formatted}")
        elif sender == "SARA":
            self.chat_display.append(f"<b style='color: #2ecc71;'>{sender}:</b> {formatted}")
        else:
            self.chat_display.append(f"<i style='color: #95a5a6;'>{formatted}</i>")

        self.chat_display.append("")

        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)

    def send_message(self):
        if not self.client:
            self.add_message("SARA", "API não configurada.")
            return

        message = self.input_field.text().strip()
        image_path = self.pending_image

        if not message and not image_path:
            return

        display_msg = f"[img] {message}" if image_path else message
        self.add_message("Você", display_msg or "(imagem)")
        self.input_field.clear()
        self.clear_pending_image()

        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.status_label.setText("Processando...")

        user_content = message or "Analise esta imagem"
        self.messages.append({"role": "user", "content": user_content})

        # Detecta se o usuário está corrigindo a SARA
        if message and _detect_user_correction(message) and self.memory:
            correction_hint = (
                "\n\n[SISTEMA: O Operador está te corrigindo. Reconheça o erro com elegância, "
                "corrija sua resposta e adicione ao final: [CORRIGIR: breve descrição do erro e o correto]]"
            )
            # Injeta hint no system prompt temporariamente
            msgs_copy = self.messages.copy()
            if msgs_copy and msgs_copy[0]["role"] == "system":
                msgs_copy[0] = {
                    "role": "system",
                    "content": msgs_copy[0]["content"] + correction_hint
                }
        else:
            msgs_copy = self.messages.copy()

        # Salvar no histórico
        if self.memory:
            self.memory.add_conversation("user", user_content)

        self.chat_thread = ChatThread(self.client, msgs_copy, image_path)
        self.chat_thread.response_ready.connect(self.handle_response)
        self.chat_thread.start()

    def handle_response(self, response):
        # Extrai memórias antes de processar resposta
        memories = _extract_memories(response)
        for mem in memories:
            if self.memory:
                self.memory.add_memory(mem, source="chat")
                print(f"[SARA] Memória registrada: {mem}")

        # Extrai correções aprendidas
        corrs = _extract_corrections(response)
        for corr in corrs:
            if self.memory:
                # Busca o que o usuário disse e o que SARA fez de errado
                recent = self.memory.get_recent_conversations(4)
                user_said = ""
                sara_did = ""
                for entry in reversed(recent):
                    if entry['role'] == 'user' and not user_said:
                        user_said = entry['content']
                    elif entry['role'] == 'assistant' and not sara_did:
                        sara_did = entry['content'][:200]
                    if user_said and sara_did:
                        break
                self.memory.add_correction(
                    user_said=user_said,
                    sara_did=sara_did,
                    correction=corr,
                    source="chat"
                )
                print(f"[SARA] Correção aprendida: {corr}")

        # Remove tags de memória e correção para exibição
        import re as _re
        display_response = _re.sub(r'\[MEMORIZAR:[^\]]*\]', '', response).strip()
        display_response = _re.sub(r'\[CORRIGIR:[^\]]*\]', '', display_response).strip()

        self.messages.append({"role": "assistant", "content": response})
        self.add_message("SARA", display_response)
        self.status_label.setText("")

        # Salvar no histórico
        if self.memory:
            self.memory.add_conversation("assistant", response)

        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

        if self.tts_enabled and HAS_TTS:
            self.tts_thread = TTSThread(display_response, self.tts_voice, self.tts_speed)
            self.tts_thread.start()


# ==================== SETTINGS WINDOW ====================

class SettingsWindow(QDialog):
    """Janela de Configurações Expandida"""
    def __init__(self, parent=None, memory=None):
        super().__init__(parent)
        self.parent_pet = parent
        self.memory = memory
        self.setWindowTitle("SARA — Configurações")
        self.setFixedSize(450, 550)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Tabs
        self.tabs = QTabWidget()

        # Tab Aparência
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)

        # Modo de Exibição
        mode_group = QGroupBox("Modo de Exibicao")
        mode_layout = QVBoxLayout(mode_group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("HUD Visualizer (padrao)")
        self.mode_combo.addItem("Sprite / Skin")
        self.mode_combo.currentIndexChanged.connect(self._on_display_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        appearance_layout.addWidget(mode_group)

        # Skin (visível apenas no modo Sprite)
        self.skin_group = QGroupBox("Skin")
        skin_layout = QVBoxLayout(self.skin_group)

        self.skin_list = QListWidget()
        try:
            _base = os.path.dirname(os.path.abspath(__file__))
            _assets = os.path.join(_base, "assets")
            skins = [f for f in os.listdir(_assets) if os.path.isdir(os.path.join(_assets, f))]
            self.skin_list.addItems(skins)
        except:
            pass
        skin_layout.addWidget(self.skin_list)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Tamanho:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(80)
        self.size_slider.setMaximum(300)
        self.size_slider.setValue(150)
        size_layout.addWidget(self.size_slider)
        self.size_label = QLabel("150px")
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(f"{v}px"))
        size_layout.addWidget(self.size_label)
        skin_layout.addLayout(size_layout)

        appearance_layout.addWidget(self.skin_group)
        self.tabs.addTab(appearance_tab, "Aparência")

        # Tab Voz
        voice_tab = QWidget()
        voice_layout = QVBoxLayout(voice_tab)

        voice_group = QGroupBox("Text-to-Speech")
        voice_group_layout = QVBoxLayout(voice_group)

        self.tts_enabled_check = QCheckBox("Ativar TTS")
        self.tts_enabled_check.setChecked(True)
        voice_group_layout.addWidget(self.tts_enabled_check)

        voice_select_layout = QHBoxLayout()
        voice_select_layout.addWidget(QLabel("Voz:"))
        self.voice_combo = QComboBox()
        # Mapa ordenado: display name → voice ID
        self._voice_options = [
            ("Qwen Cherry", "Cherry"),
            ("Qwen Seren", "Seren"),
            ("Qwen Mia", "Mia"),
            ("Qwen Stella", "Stella"),
            ("Qwen Neil", "Neil"),
            ("Qwen Kai", "Kai"),
            ("Edge Francisca (BR)", "pt-BR-FranciscaNeural"),
            ("Edge Antonio (BR)", "pt-BR-AntonioNeural"),
        ]
        for display_name, _ in self._voice_options:
            self.voice_combo.addItem(display_name)
        voice_select_layout.addWidget(self.voice_combo)
        voice_group_layout.addLayout(voice_select_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidade:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(150)
        self.speed_slider.setValue(100)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        self.speed_slider.valueChanged.connect(lambda v: self.speed_label.setText(f"{v/100:.1f}x"))
        speed_layout.addWidget(self.speed_label)
        voice_group_layout.addLayout(speed_layout)

        voice_layout.addWidget(voice_group)

        # Wake Word
        wake_group = QGroupBox("Ativação por Voz")
        wake_layout = QVBoxLayout(wake_group)

        self.wake_enabled_check = QCheckBox("Ativar wake word ('Sara')")
        self.wake_enabled_check.setChecked(True)
        wake_layout.addWidget(self.wake_enabled_check)

        voice_layout.addWidget(wake_group)
        voice_layout.addStretch()
        self.tabs.addTab(voice_tab, "Voz")

        # Tab Proatividade
        proactive_tab = QWidget()
        proactive_layout = QVBoxLayout(proactive_tab)

        proactive_group = QGroupBox("Comportamento Proativo")
        proactive_group_layout = QVBoxLayout(proactive_group)

        self.proactive_enabled_check = QCheckBox("Ativar notificações proativas")
        self.proactive_enabled_check.setChecked(True)
        proactive_group_layout.addWidget(self.proactive_enabled_check)

        self.greetings_check = QCheckBox("Saudações automáticas")
        self.greetings_check.setChecked(True)
        proactive_group_layout.addWidget(self.greetings_check)

        self.tips_check = QCheckBox("Dicas de produtividade")
        self.tips_check.setChecked(True)
        proactive_group_layout.addWidget(self.tips_check)

        pause_layout = QHBoxLayout()
        pause_layout.addWidget(QLabel("Lembrete de pausa (min):"))
        self.pause_spin = QSpinBox()
        self.pause_spin.setMinimum(15)
        self.pause_spin.setMaximum(120)
        self.pause_spin.setValue(45)
        pause_layout.addWidget(self.pause_spin)
        proactive_group_layout.addLayout(pause_layout)

        proactive_layout.addWidget(proactive_group)
        proactive_layout.addStretch()
        self.tabs.addTab(proactive_tab, "Proatividade")

        # Tab Pomodoro
        pomodoro_tab = QWidget()
        pomodoro_layout = QVBoxLayout(pomodoro_tab)

        pomodoro_group = QGroupBox("Timer Pomodoro")
        pomodoro_group_layout = QVBoxLayout(pomodoro_group)

        work_layout = QHBoxLayout()
        work_layout.addWidget(QLabel("Foco (min):"))
        self.work_spin = QSpinBox()
        self.work_spin.setMinimum(15)
        self.work_spin.setMaximum(60)
        self.work_spin.setValue(25)
        work_layout.addWidget(self.work_spin)
        pomodoro_group_layout.addLayout(work_layout)

        short_layout = QHBoxLayout()
        short_layout.addWidget(QLabel("Pausa curta (min):"))
        self.short_spin = QSpinBox()
        self.short_spin.setMinimum(3)
        self.short_spin.setMaximum(15)
        self.short_spin.setValue(5)
        short_layout.addWidget(self.short_spin)
        pomodoro_group_layout.addLayout(short_layout)

        long_layout = QHBoxLayout()
        long_layout.addWidget(QLabel("Pausa longa (min):"))
        self.long_spin = QSpinBox()
        self.long_spin.setMinimum(10)
        self.long_spin.setMaximum(30)
        self.long_spin.setValue(15)
        long_layout.addWidget(self.long_spin)
        pomodoro_group_layout.addLayout(long_layout)

        pomodoro_layout.addWidget(pomodoro_group)
        pomodoro_layout.addStretch()
        self.tabs.addTab(pomodoro_tab, "Pomodoro")

        layout.addWidget(self.tabs)

        # Botões
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Salvar")
        btn_save.clicked.connect(self.save_and_accept)
        btn_save.setStyleSheet("background-color: #27ae60; color: white;")
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_display_mode_changed(self, index):
        """Mostra/esconde controles de skin conforme modo selecionado."""
        is_skin = (index == 1)
        self.skin_group.setVisible(is_skin)

    def load_settings(self):
        """Carrega configurações salvas"""
        if not self.memory:
            return

        prefs = self.memory.preferences
        state = self.memory.pet_state

        # Modo de exibição
        if state.display_mode == "skin":
            self.mode_combo.setCurrentIndex(1)
        else:
            self.mode_combo.setCurrentIndex(0)
        self._on_display_mode_changed(self.mode_combo.currentIndex())

        # Skin
        items = self.skin_list.findItems(state.current_skin, Qt.MatchFlag.MatchExactly)
        if items:
            self.skin_list.setCurrentItem(items[0])
        self.size_slider.setValue(state.pet_size)

        # Voz
        self.tts_enabled_check.setChecked(prefs.tts_enabled)
        self.speed_slider.setValue(int(prefs.tts_speed * 100))
        self.wake_enabled_check.setChecked(state.voice_enabled)
        # Seleciona a voz salva no combo
        saved_voice = prefs.tts_voice
        for i, (_, voice_id) in enumerate(self._voice_options):
            if voice_id == saved_voice:
                self.voice_combo.setCurrentIndex(i)
                break

        # Proatividade
        self.proactive_enabled_check.setChecked(prefs.proactive_enabled)
        self.greetings_check.setChecked(prefs.greetings_enabled)
        self.tips_check.setChecked(prefs.tips_enabled)
        self.pause_spin.setValue(prefs.pause_reminder_interval)

        # Pomodoro
        self.work_spin.setValue(prefs.pomodoro_work)
        self.short_spin.setValue(prefs.pomodoro_short_break)
        self.long_spin.setValue(prefs.pomodoro_long_break)

    def _get_selected_voice_id(self) -> str:
        """Retorna o voice ID selecionado no combo."""
        idx = self.voice_combo.currentIndex()
        if 0 <= idx < len(self._voice_options):
            return self._voice_options[idx][1]
        return "Cherry"

    def save_and_accept(self):
        """Salva configurações e fecha"""
        if self.memory:
            self.memory.update_preferences(
                tts_enabled=self.tts_enabled_check.isChecked(),
                tts_voice=self._get_selected_voice_id(),
                tts_speed=self.speed_slider.value() / 100,
                proactive_enabled=self.proactive_enabled_check.isChecked(),
                greetings_enabled=self.greetings_check.isChecked(),
                tips_enabled=self.tips_check.isChecked(),
                pause_reminder_interval=self.pause_spin.value(),
                pomodoro_work=self.work_spin.value(),
                pomodoro_short_break=self.short_spin.value(),
                pomodoro_long_break=self.long_spin.value()
            )

            # Estado do pet
            display_mode = "hud" if self.mode_combo.currentIndex() == 0 else "skin"
            self.memory.update_pet_config(
                display_mode=display_mode,
                current_skin=self.skin_list.currentItem().text() if self.skin_list.currentItem() else "robot_skin",
                pet_size=self.size_slider.value(),
                voice_enabled=self.wake_enabled_check.isChecked()
            )

            self.memory.save_all()

        self.accept()

    def get_settings(self):
        """Retorna configurações atuais"""
        return {
            "display_mode": "hud" if self.mode_combo.currentIndex() == 0 else "skin",
            "skin": self.skin_list.currentItem().text() if self.skin_list.currentItem() else None,
            "size": self.size_slider.value(),
            "voice_enabled": self.wake_enabled_check.isChecked(),
            "tts_enabled": self.tts_enabled_check.isChecked(),
            "tts_voice": self._get_selected_voice_id(),
            "tts_speed": self.speed_slider.value() / 100,
            "proactive_enabled": self.proactive_enabled_check.isChecked(),
            "pomodoro_work": self.work_spin.value(),
            "pomodoro_short": self.short_spin.value(),
            "pomodoro_long": self.long_spin.value()
        }


# ==================== POMODORO WINDOW ====================

class PomodoroWindow(QDialog):
    """Janela do Timer Pomodoro"""
    def __init__(self, parent=None, memory=None):
        super().__init__(parent)
        self.parent_pet = parent
        self.memory = memory
        self.setWindowTitle("SARA — Pomodoro")
        self.setFixedSize(300, 350)

        self.is_running = False
        self.is_break = False
        self.time_left = 0
        self.sessions = 0

        # Configurações
        if memory:
            self.work_time = memory.preferences.pomodoro_work * 60
            self.short_break = memory.preferences.pomodoro_short_break * 60
            self.long_break = memory.preferences.pomodoro_long_break * 60
        else:
            self.work_time = 25 * 60
            self.short_break = 5 * 60
            self.long_break = 15 * 60

        self.setup_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Timer display
        self.time_label = QLabel("25:00")
        self.time_label.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: #e74c3c;
            font-family: 'Consolas', monospace;
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # Status
        self.status_label = QLabel("Pronto para iniciar.")
        self.status_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Sessões
        self.sessions_label = QLabel("Sessões: 0")
        self.sessions_label.setStyleSheet("font-size: 12px; color: #95a5a6;")
        self.sessions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sessions_label)

        # Botões
        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("Iniciar")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_start.clicked.connect(self.toggle_timer)
        btn_layout.addWidget(self.btn_start)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_reset.clicked.connect(self.reset_timer)
        btn_layout.addWidget(self.btn_reset)

        layout.addLayout(btn_layout)

        # Skip break button
        self.btn_skip = QPushButton("Pular Pausa")
        self.btn_skip.setStyleSheet("color: #7f8c8d;")
        self.btn_skip.clicked.connect(self.skip_break)
        self.btn_skip.setVisible(False)
        layout.addWidget(self.btn_skip)

        self.setLayout(layout)
        self.update_display()

    def toggle_timer(self):
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.time_left == 0:
            self.time_left = self.work_time

        self.is_running = True
        self.btn_start.setText("Pausar")
        self.timer.start(1000)
        self.status_label.setText("Foco ativo." if not self.is_break else "Intervalo em andamento.")

        if self.parent_pet:
            msg = "Pomodoro iniciado. Foco total." if not self.is_break else "Intervalo iniciado. Recupere energia."
            self.parent_pet.show_bubble(msg)

    def pause_timer(self):
        self.is_running = False
        self.btn_start.setText("Continuar")
        self.timer.stop()
        self.status_label.setText("Pausado")

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.is_break = False
        self.time_left = self.work_time
        self.btn_start.setText("Iniciar")
        self.btn_skip.setVisible(False)
        self.status_label.setText("Pronto para iniciar.")
        self.update_display()

    def tick(self):
        self.time_left -= 1
        self.update_display()

        if self.time_left <= 0:
            self.on_period_complete()

    def on_period_complete(self):
        self.timer.stop()
        self.is_running = False

        if self.is_break:
            # Fim da pausa
            self.is_break = False
            self.time_left = self.work_time
            self.btn_skip.setVisible(False)
            self.status_label.setText("De volta ao foco.")
            self.btn_start.setText("Iniciar")

            if self.parent_pet:
                self.parent_pet.show_bubble("Intervalo encerrado. De volta ao foco.")

        else:
            # Fim do foco
            self.sessions += 1
            self.sessions_label.setText(f"Sessões: {self.sessions}")
            self.is_break = True

            # A cada 4 sessões, pausa longa
            if self.sessions % 4 == 0:
                self.time_left = self.long_break
                msg = f"{self.sessions} sessões concluídas. Pausa longa merecida."
            else:
                self.time_left = self.short_break
                msg = "Sessão concluída. Pausa curta recomendada."

            self.status_label.setText(msg)
            self.btn_skip.setVisible(True)
            self.btn_start.setText("Iniciar Intervalo")

            if self.parent_pet:
                self.parent_pet.show_bubble(msg)

        self.update_display()

    def skip_break(self):
        self.is_break = False
        self.time_left = self.work_time
        self.btn_skip.setVisible(False)
        self.status_label.setText("Pronto para iniciar.")
        self.btn_start.setText("Iniciar")
        self.update_display()

    def update_display(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Cor baseada no estado
        if self.is_break:
            self.time_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #27ae60; font-family: 'Consolas', monospace;")
        else:
            self.time_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #e74c3c; font-family: 'Consolas', monospace;")


# ==================== MAIN PET WIDGET ====================

class VirtualPet(QWidget):
    """Widget Principal do Pet SARA"""
    def __init__(self):
        super().__init__()

        # Configurações de Overlay
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.label)

        # Memória persistente
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        self.memory = MemoryManager(data_dir=os.path.join(_base_dir, "data")) if HAS_MEMORY else None

        # API Client para comandos de voz
        api_key = os.getenv("GROQ_API_KEY")
        self.api_client = Groq(api_key=api_key) if api_key else None

        # Ações do sistema (controle do PC)
        self.system_actions = SystemActions() if HAS_SYSTEM_ACTIONS else None

        # Configurações de TTS
        if self.memory:
            self.tts_voice = self.memory.preferences.tts_voice
            self.tts_speed = self.memory.preferences.tts_speed
        else:
            self.tts_voice = "Cherry"
            self.tts_speed = 1.0

        # Variáveis de Estado
        if self.memory:
            self.current_skin = self.memory.pet_state.current_skin
            self.pet_width = self.memory.pet_state.pet_size
            self.voice_enabled = self.memory.pet_state.voice_enabled
            self.display_mode = self.memory.pet_state.display_mode
        else:
            self.current_skin = "robot_skin"
            self.pet_width = 150
            self.voice_enabled = True
            self.display_mode = "hud"

        self.current_action = "idle"
        self.frame_index = 0
        self.animations = {}
        self.modo_passeio = False
        self.facing_right = True
        self.last_interaction_time = time.time()

        # Movimento
        self.old_pos = None
        self.animation_move = QPropertyAnimation(self, b"pos")
        self.animation_move.finished.connect(self.finalizar_caminhada)

        # Balão de fala
        self.speech_bubble = SimpleSpeechBubble()

        # HUD Visualizer
        self.hud_widget = None
        if HAS_HUD:
            self.hud_widget = HUDVisualizer(pet_ref=self, size=220)

        # System Tray
        self.setup_system_tray()

        self.load_assets()

        # Timers
        self.timer_frames = QTimer(self)
        self.timer_frames.timeout.connect(self.update_frame)
        self.timer_frames.start(400)

        self.timer_passeio = QTimer(self)
        self.timer_passeio.timeout.connect(self.decidir_caminhada)
        self.timer_passeio.start(5000)

        self.timer_proativo = QTimer(self)
        self.timer_proativo.timeout.connect(self.check_proactive_actions)
        self.timer_proativo.start(60000)

        self.timer_system = QTimer(self)
        self.timer_system.timeout.connect(self.check_system_status)
        self.timer_system.start(300000)

        self.timer_attention = QTimer(self)
        self.timer_attention.timeout.connect(self.seek_attention)
        self.timer_attention.start(300000)

        self.timer_save = QTimer(self)
        self.timer_save.timeout.connect(self.save_state)
        self.timer_save.start(60000)

        # Contadores
        self.minutes_since_pause = 0
        self.minutes_since_tip = 0

        # Wake word
        self.wake_word_thread = None
        if HAS_STT and self.voice_enabled:
            self.start_wake_word_listener()

        # Aplica modo de exibição (HUD ou Skin)
        self._apply_display_mode()

        # Saudação
        QTimer.singleShot(2000, self.greet_user)

        print("[SARA] Inicializada. Todos os módulos operacionais.")

    def setup_system_tray(self):
        """Configura System Tray"""
        self.tray_icon = QSystemTrayIcon(self)

        # Criar ícone simples
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        self.tray_icon.setIcon(QIcon(pixmap))

        # Menu
        tray_menu = QMenu()

        action_show = QAction("Mostrar SARA", self)
        action_show.triggered.connect(self.show)
        tray_menu.addAction(action_show)

        action_chat = QAction("Conversar", self)
        action_chat.triggered.connect(self.open_chat)
        tray_menu.addAction(action_chat)

        action_pomodoro = QAction("Pomodoro", self)
        action_pomodoro.triggered.connect(self.open_pomodoro)
        tray_menu.addAction(action_pomodoro)

        tray_menu.addSeparator()

        action_settings = QAction("Configurações", self)
        action_settings.triggered.connect(self.open_settings)
        tray_menu.addAction(action_settings)

        tray_menu.addSeparator()

        action_exit = QAction("Encerrar", self)
        action_exit.triggered.connect(self.cleanup_and_exit)
        tray_menu.addAction(action_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.setToolTip("SARA - Pet Assistant")
        self.tray_icon.show()

    def tray_activated(self, reason):
        """Ação ao clicar no tray"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()

    def save_state(self):
        """Salva estado atual"""
        if not self.memory:
            return

        self.memory.update_pet_config(
            display_mode=self.display_mode,
            current_skin=self.current_skin,
            pet_size=self.pet_width,
            voice_enabled=self.voice_enabled,
            modo_passeio=self.modo_passeio,
            position_x=self.pos().x() if self.display_mode == "skin" else (self.hud_widget.pos().x() if self.hud_widget else self.pos().x()),
            position_y=self.pos().y() if self.display_mode == "skin" else (self.hud_widget.pos().y() if self.hud_widget else self.pos().y()),
        )
        self.memory.save_all()

    def _apply_display_mode(self):
        """Alterna entre HUD Visualizer e Sprite/Skin."""
        if self.display_mode == "hud" and self.hud_widget:
            self.label.hide()
            self.hide()
            # Posiciona HUD onde o pet estava
            if self.memory:
                self.hud_widget.move(self.memory.pet_state.position_x, self.memory.pet_state.position_y)
            else:
                self.hud_widget.move(self.pos())
            self.hud_widget.show()
            # Desativa passeio no modo HUD
            if self.modo_passeio:
                self.modo_passeio = False
                self.animation_move.stop()
        else:
            # Modo skin
            if self.hud_widget:
                self.hud_widget.hide()
            self.label.show()
            self.show()
            self.load_assets()

    def _show_context_menu_at(self, global_pos):
        """Exibe context menu na posição global (chamado pelo HUD ou pelo pet)."""
        self.last_interaction_time = time.time()
        menu = QMenu(self)

        action_chat = menu.addAction("Conversar")
        action_pomodoro = menu.addAction("Pomodoro")
        menu.addSeparator()

        # Submenu Modo Visual
        visual_menu = menu.addMenu("Modo Visual")
        action_hud = visual_menu.addAction("HUD Visualizer" + (" [ON]" if self.display_mode == "hud" else ""))
        action_skin = visual_menu.addAction("Sprite / Skin" + (" [ON]" if self.display_mode == "skin" else ""))

        if self.display_mode == "skin":
            texto_passeio = "[ON] Modo Passeio" if self.modo_passeio else "Modo Passeio"
            action_passeio = menu.addAction(texto_passeio)
        else:
            action_passeio = None

        texto_voz = "[ON] Ativacao por Voz" if self.voice_enabled else "Ativacao por Voz"
        action_voz = menu.addAction(texto_voz)

        menu.addSeparator()
        action_settings = menu.addAction("Configuracoes")
        action_quit = menu.addAction("Encerrar")

        action = menu.exec(global_pos)

        if action == action_chat:
            self.open_chat()
        elif action == action_pomodoro:
            self.open_pomodoro()
        elif action == action_hud:
            if self.display_mode != "hud":
                self.display_mode = "hud"
                self._apply_display_mode()
        elif action == action_skin:
            if self.display_mode != "skin":
                self.display_mode = "skin"
                self._apply_display_mode()
        elif action_passeio and action == action_passeio:
            self.modo_passeio = not self.modo_passeio
            if not self.modo_passeio:
                self.animation_move.stop()
        elif action == action_voz:
            self.toggle_voice()
        elif action == action_settings:
            self.open_settings()
        elif action == action_quit:
            self.cleanup_and_exit()

    def _on_speaking_started(self, extractor):
        """Encaminha dados de áudio para o HUD."""
        if self.display_mode == "hud" and self.hud_widget:
            self.hud_widget.set_speaking(extractor)

    def _on_speaking_finished(self):
        """Retorna HUD ao idle após terminar de falar."""
        if self.display_mode == "hud" and self.hud_widget:
            self.hud_widget.set_idle()

    def _on_stt_status_changed(self, status):
        """Atualiza estado visual do HUD baseado no STT."""
        if self.display_mode == "hud" and self.hud_widget:
            if status == "listening":
                self.hud_widget.set_state("listening")
            elif status == "processing":
                self.hud_widget.set_state("processing")
            elif status == "idle":
                self.hud_widget.set_state("idle")

    def start_wake_word_listener(self):
        if self.wake_word_thread and self.wake_word_thread.isRunning():
            return

        self.wake_word_thread = WakeWordThread(groq_client=self.api_client)
        self.wake_word_thread.wake_word_detected.connect(self.on_wake_word)
        self.wake_word_thread.command_received.connect(self.on_voice_command)
        self.wake_word_thread.status_changed.connect(self._on_stt_status_changed)
        self.wake_word_thread.start()
        print("[SARA] Wake word listener ativo.")

    def stop_wake_word_listener(self):
        if self.wake_word_thread:
            self.wake_word_thread.stop()
            self.wake_word_thread.wait(2000)
            self.wake_word_thread = None

    def on_wake_word(self):
        self.show_bubble("Às ordens, Senhor.")
        self.last_interaction_time = time.time()
        if HAS_TTS:
            tts = TTSThread("Às ordens, Senhor.")
            tts.start()

    def on_voice_command(self, command):
        """Processa comando de voz — tenta ação do sistema primeiro, depois IA."""
        self.last_interaction_time = time.time()
        print(f"[SARA] Comando recebido: {command}")

        # HUD → processing
        if self.display_mode == "hud" and self.hud_widget:
            self.hud_widget.set_state("processing")

        # Pausa a escuta enquanto processa
        if self.wake_word_thread:
            self.wake_word_thread.pause()

        # 1) Tenta executar como ação do sistema (instantânea, sem IA)
        if self.system_actions:
            result = self.system_actions.parse_and_execute(command)
            if result:
                print(f"[SARA] Ação do sistema: {result}")
                self.show_bubble(result, 4000)
                # Fala a confirmação por TTS
                if HAS_TTS:
                    self.tts_thread = TTSThread(result, self.tts_voice, self.tts_speed)
                    self.tts_thread.speaking_started.connect(self._on_speaking_started)
                    self.tts_thread.speaking_stopped.connect(self._on_speaking_finished)
                    self.tts_thread.finished.connect(self.on_voice_finished)
                    self.tts_thread.start()
                else:
                    self.on_voice_finished()
                return

        # 2) Não é ação do sistema — envia para a IA
        self.show_bubble(f"Processando: {command[:30]}...", 3000)

        self.voice_response_thread = VoiceResponseThread(
            self.api_client, command, self.tts_voice, self.tts_speed, self.memory
        )
        self.voice_response_thread.response_ready.connect(self.on_voice_response)
        self.voice_response_thread.speaking_started.connect(self._on_speaking_started)
        self.voice_response_thread.finished_speaking.connect(self._on_speaking_finished)
        self.voice_response_thread.finished_speaking.connect(self.on_voice_finished)
        self.voice_response_thread.memory_extracted.connect(self.on_memory_saved)
        self.voice_response_thread.start()

    def on_voice_response(self, response):
        """Mostra a resposta no balão"""
        # Remove tags internas antes de exibir
        import re as _re
        clean = _re.sub(r'\[MEMORIZAR:[^\]]*\]', '', response)
        clean = _re.sub(r'\[CORRIGIR:[^\]]*\]', '', clean).strip()
        display_text = clean[:100] + "..." if len(clean) > 100 else clean
        self.show_bubble(display_text, 6000)

    def on_memory_saved(self, memory_text):
        """Callback quando uma memória é extraída e salva"""
        print(f"[SARA] Memória registrada: {memory_text}")

    def on_voice_finished(self):
        """Retoma a escuta após terminar de falar"""
        if self.wake_word_thread:
            self.wake_word_thread.resume()
        print("[SARA] Retomando escuta.")

    def greet_user(self):
        hour = datetime.now().hour

        if 5 <= hour < 12:
            messages = PROACTIVE_MESSAGES.get("morning_greetings", ["Bom dia, Senhor."])
        elif 12 <= hour < 18:
            messages = PROACTIVE_MESSAGES.get("afternoon_greetings", ["Boa tarde, Senhor."])
        else:
            messages = PROACTIVE_MESSAGES.get("evening_greetings", ["Boa noite, Senhor."])

        self.show_bubble(random.choice(messages))

    def show_bubble(self, message, duration=4000):
        # Posiciona relativo ao widget ativo (HUD ou sprite)
        if self.display_mode == "hud" and self.hud_widget and self.hud_widget.isVisible():
            pos = self.hud_widget.pos()
        else:
            pos = self.pos()
        self.speech_bubble.show_message(message, duration, pos)

    def check_proactive_actions(self):
        self.minutes_since_pause += 1
        self.minutes_since_tip += 1

        pause_interval = PROACTIVE_CONFIG.get("pause_reminder_interval", 45)
        if self.minutes_since_pause >= pause_interval:
            messages = PROACTIVE_MESSAGES.get("pause_reminders", ["Pausa recomendada."])
            msg = random.choice(messages)
            # Injeta dados reais se o template suportar
            try:
                msg = msg.format(minutes=self.minutes_since_pause)
            except (KeyError, IndexError):
                pass
            self.show_bubble(msg, 5000)
            self.minutes_since_pause = 0

        if PROACTIVE_CONFIG.get("random_tips_enabled", True):
            tips_interval = PROACTIVE_CONFIG.get("tips_interval", 30)
            if self.minutes_since_tip >= tips_interval:
                messages = PROACTIVE_MESSAGES.get("productivity_tips", ["Dica de produtividade."])
                self.show_bubble(random.choice(messages), 6000)
                self.minutes_since_tip = 0

    def check_system_status(self):
        if not HAS_PSUTIL:
            return

        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent

            if cpu > 80:
                messages = PROACTIVE_MESSAGES.get("cpu_high", ["CPU em uso elevado."])
                msg = random.choice(messages)
                try:
                    msg = msg.format(value=cpu)
                except (KeyError, IndexError):
                    pass
                self.show_bubble(msg, 5000)
            elif memory > 85:
                messages = PROACTIVE_MESSAGES.get("memory_high", ["Memória em uso elevado."])
                msg = random.choice(messages)
                try:
                    msg = msg.format(value=memory)
                except (KeyError, IndexError):
                    pass
                self.show_bubble(msg, 5000)
        except Exception as e:
            print(f"[SARA] Erro no monitor de sistema: {e}")

    def seek_attention(self):
        time_since = time.time() - self.last_interaction_time
        if time_since > 600 and random.random() < 0.3:
            # Após longo período sem interação, oferece utilidade
            messages = PROACTIVE_MESSAGES.get("attention_seeking", ["Alguma tarefa pendente?"])
            self.show_bubble(random.choice(messages))

    def load_assets(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        skin_path = os.path.join(base_dir, "assets", self.current_skin)
        if not os.path.exists(skin_path):
            print(f"[SARA] Assets não encontrados: {skin_path}")
            return

        self.animations = {
            "idle": self._load_frames(skin_path, "idle"),
            "walk": self._load_frames(skin_path, "walk")
        }
        self.update_frame()

    def _load_frames(self, path, action_name):
        frames = []
        i = 0
        while True:
            file_path = os.path.join(path, f"{action_name}_{i}.png")
            if os.path.exists(file_path):
                pix = QPixmap(file_path)
                frames.append(pix.scaledToWidth(self.pet_width, Qt.TransformationMode.SmoothTransformation))
                i += 1
            else:
                break
        return frames

    def update_frame(self):
        frames = self.animations.get(self.current_action, [])
        if frames:
            self.frame_index = (self.frame_index + 1) % len(frames)
            pixmap = frames[self.frame_index]

            if not self.facing_right:
                transform = QTransform().scale(-1, 1)
                pixmap = pixmap.transformed(transform)

            self.label.setPixmap(pixmap)
            self.adjustSize()

    def decidir_caminhada(self):
        if self.modo_passeio and self.current_action == "idle":
            if random.random() < 0.3:
                self.iniciar_passeio_aleatorio()

    def iniciar_passeio_aleatorio(self):
        screen = QApplication.primaryScreen().geometry()
        target_x = random.randint(0, screen.width() - self.width())
        target_y = random.randint(0, screen.height() - self.height())
        target_pos = QPoint(target_x, target_y)

        self.facing_right = target_x > self.pos().x()
        distancia = (target_pos - self.pos()).manhattanLength()

        self.set_action("walk")
        self.animation_move.setDuration(distancia * 7)
        self.animation_move.setStartValue(self.pos())
        self.animation_move.setEndValue(target_pos)
        self.animation_move.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation_move.start()

    def finalizar_caminhada(self):
        self.set_action("idle")

    def set_action(self, action):
        if self.current_action != action:
            self.current_action = action
            self.frame_index = 0

    def contextMenuEvent(self, event):
        self._show_context_menu_at(event.globalPos())

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        if self.voice_enabled:
            self.start_wake_word_listener()
            self.show_bubble("Reconhecimento de voz ativado.")
        else:
            self.stop_wake_word_listener()
            self.show_bubble("Reconhecimento de voz desativado.")

    def open_chat(self, initial_message=None):
        dialog = ChatWindow(self, initial_message, self.memory)
        dialog.exec()

    def open_pomodoro(self):
        dialog = PomodoroWindow(self, self.memory)
        dialog.exec()

    def open_settings(self):
        dialog = SettingsWindow(self, self.memory)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()

            if settings["skin"]:
                self.current_skin = settings["skin"]
            self.pet_width = settings["size"]

            # Aplica voz e velocidade do TTS
            new_voice = settings.get("tts_voice", self.tts_voice)
            new_speed = settings.get("tts_speed", self.tts_speed)
            if new_voice != self.tts_voice or new_speed != self.tts_speed:
                self.tts_voice = new_voice
                self.tts_speed = new_speed
                print(f"[SARA] Voz alterada: {self.tts_voice}, velocidade: {self.tts_speed}x")

            if settings["voice_enabled"] != self.voice_enabled:
                self.voice_enabled = settings["voice_enabled"]
                if self.voice_enabled:
                    self.start_wake_word_listener()
                else:
                    self.stop_wake_word_listener()

            # Aplica modo de exibição
            new_mode = settings.get("display_mode", self.display_mode)
            if new_mode != self.display_mode:
                self.display_mode = new_mode
                self._apply_display_mode()
            elif self.display_mode == "skin":
                self.load_assets()

    def cleanup_and_exit(self):
        self.save_state()
        self.stop_wake_word_listener()
        self.tray_icon.hide()
        QApplication.quit()

    def mousePressEvent(self, event):
        self.last_interaction_time = time.time()
        if event.button() == Qt.MouseButton.LeftButton:
            self.animation_move.stop()
            self.old_pos = event.globalPosition().toPoint()
            self.set_action("walk")

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            if delta.x() > 0:
                self.facing_right = True
            elif delta.x() < 0:
                self.facing_right = False
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

            self.speech_bubble.move(
                self.pos().x() - self.speech_bubble.width() // 2 + 75,
                self.pos().y() - self.speech_bubble.height() - 15
            )

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.set_action("idle")

    def closeEvent(self, event):
        # Minimiza para tray em vez de fechar
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("SARA", "Operando em segundo plano.", QSystemTrayIcon.MessageIcon.Information, 2000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Não fecha ao fechar janela

    pet = VirtualPet()
    pet.show()

    sys.exit(app.exec())
