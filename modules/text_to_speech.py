"""
Módulo de Text-to-Speech (Texto para Fala)
Usa Edge TTS (Microsoft) - Vozes neurais de alta qualidade GRATUITAS
"""
import edge_tts
import asyncio
import threading
import tempfile
import os

# Tenta importar pygame para reprodução de áudio
try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    print("[TTS] pygame não encontrado. Instale com: pip install pygame")


class TextToSpeech:
    # Vozes disponíveis em português brasileiro (Neural - alta qualidade)
    VOICES = {
        "francisca": "pt-BR-FranciscaNeural",  # Feminina - muito natural
        "antonio": "pt-BR-AntonioNeural",      # Masculina - muito natural
        "thalita": "pt-BR-ThalitaNeural",      # Feminina - jovem
        "macerio": "pt-BR-MacerioNeural",      # Masculina
        "leila": "pt-BR-LeilaNeural",          # Feminina
        "donato": "pt-BR-DonatoNeural",        # Masculina
    }
    
    def __init__(self, voice: str = "francisca", rate: str = "+0%", volume: str = "+0%"):
        """
        Inicializa o módulo de síntese de voz com Edge TTS.
        
        Args:
            voice: Nome da voz (francisca, antonio, thalita, macerio, leila, donato)
            rate: Velocidade da fala (ex: "+10%", "-20%", "+0%")
            volume: Volume (ex: "+10%", "-20%", "+0%")
        """
        self.voice = self.VOICES.get(voice.lower(), self.VOICES["francisca"])
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()
        
        # Diretório temporário para arquivos de áudio
        self.temp_dir = tempfile.gettempdir()
        
        print(f"[TTS] Voz selecionada: {self.voice}")
    
    def speak(self, text: str, block: bool = True):
        """
        Fala o texto fornecido.
        
        Args:
            text: Texto para ser falado
            block: Se True, bloqueia até terminar de falar
        """
        if block:
            self._speak_sync(text)
        else:
            threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()
    
    def _speak_sync(self, text: str):
        """Fala de forma síncrona."""
        with self._lock:
            try:
                # Cria arquivo temporário com nome único
                import uuid
                temp_file = os.path.join(self.temp_dir, f"buddy_speech_{uuid.uuid4().hex[:8]}.mp3")
                
                # Gera áudio com Edge TTS
                asyncio.run(self._generate_audio(text, temp_file))
                
                # Reproduz o áudio
                self._play_audio(temp_file)
                
                # Remove arquivo temporário (com delay para garantir que terminou)
                try:
                    import time
                    time.sleep(0.2)
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
                    
            except Exception as e:
                print(f"Erro no TTS: {e}")
    
    async def _generate_audio(self, text: str, output_file: str):
        """Gera áudio usando Edge TTS."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume
        )
        await communicate.save(output_file)
    
    def _play_audio(self, file_path: str):
        """Reproduz arquivo de áudio."""
        if HAS_PYGAME:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                pygame.mixer.music.unload()  # Libera o arquivo
            except Exception as e:
                print(f"Erro ao reproduzir áudio: {e}")
                try:
                    pygame.mixer.music.unload()
                except:
                    pass
        else:
            # Fallback: tenta usar player do sistema
            try:
                if os.name == 'nt':  # Windows
                    import subprocess
                    subprocess.run(['powershell', '-c', f'(New-Object Media.SoundPlayer "{file_path}").PlaySync()'], 
                                 capture_output=True, timeout=30)
                else:
                    os.system(f'mpg123 "{file_path}" 2>/dev/null || afplay "{file_path}" 2>/dev/null')
            except:
                print("Não foi possível reproduzir o áudio")
    
    def set_voice(self, voice: str):
        """Muda a voz."""
        if voice.lower() in self.VOICES:
            self.voice = self.VOICES[voice.lower()]
            print(f"[TTS] Voz alterada: {self.voice}")
        else:
            print(f"Voz '{voice}' não encontrada. Opções: {list(self.VOICES.keys())}")
    
    def set_rate(self, rate: str):
        """Define velocidade (ex: '+10%', '-20%')."""
        self.rate = rate
    
    def set_volume(self, volume: str):
        """Define volume (ex: '+10%', '-20%')."""
        self.volume = volume
    
    @classmethod
    def list_voices(cls) -> dict:
        """Lista vozes disponíveis."""
        return cls.VOICES


# Função de conveniência
def quick_speak(text: str, voice: str = "francisca"):
    """Fala rapidamente um texto."""
    tts = TextToSpeech(voice=voice)
    tts.speak(text)


if __name__ == "__main__":
    # Teste do módulo
    print("Testando Edge TTS...")
    print(f"Vozes disponíveis: {TextToSpeech.list_voices()}")
    
    tts = TextToSpeech(voice="francisca")
    tts.speak("SARA operacional. Protocolo A.T.L.A.S. ativo.")
    
    tts.set_voice("antonio")
    tts.speak("Voz alternativa ativa.")
    
    print("[TTS] Teste concluído.")
