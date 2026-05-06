"""
Módulo de Speech-to-Text (Fala para Texto)
Usa SpeechRecognition com suporte a Whisper e Google
"""
import speech_recognition as sr
from typing import Optional, Callable
import threading


class SpeechToText:
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        """
        Inicializa o módulo de reconhecimento de voz.
        
        Args:
            callback: Função chamada quando texto é reconhecido
        """
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.callback = callback
        self.is_listening = False
        self._listen_thread: Optional[threading.Thread] = None
        
        # Ajusta para ruído ambiente
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
    
    def listen_once(self, timeout: float = 5.0) -> Optional[str]:
        """
        Escuta uma única vez e retorna o texto reconhecido.
        
        Args:
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            Texto reconhecido ou None se falhar
        """
        try:
            with self.microphone as source:
                print("[STT] Ouvindo...")
                # Ajusta para ruído
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
                
            print("[STT] Processando...")
            
            # Usa Google Speech Recognition (mais rápido e confiável)
            try:
                text = self.recognizer.recognize_google(audio, language="pt-BR")
                print(f"[STT] Reconhecido: {text}")
                return text.strip()
            except sr.UnknownValueError:
                print("[STT] Áudio não reconhecido.")
                return None
            except sr.RequestError as e:
                print(f"[STT] Erro no serviço Google: {e}")
                # Tenta Whisper como fallback
                try:
                    text = self.recognizer.recognize_whisper(audio, model="base", language="pt")
                    print(f"[STT] Reconhecido (Whisper): {text}")
                    return text.strip()
                except:
                    return None
            
        except sr.WaitTimeoutError:
            print("[STT] Timeout — nenhuma fala detectada.")
            return None
        except Exception as e:
            print(f"[STT] Erro: {e}")
            return None
    
    def start_continuous_listening(self):
        """Inicia escuta contínua em background."""
        if self.is_listening:
            return
            
        self.is_listening = True
        self._listen_thread = threading.Thread(target=self._continuous_listen_loop, daemon=True)
        self._listen_thread.start()
    
    def stop_continuous_listening(self):
        """Para a escuta contínua."""
        self.is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2)
    
    def _continuous_listen_loop(self):
        """Loop interno para escuta contínua."""
        while self.is_listening:
            text = self.listen_once(timeout=3.0)
            if text and self.callback:
                self.callback(text)


# Função de conveniência para uso rápido
def quick_listen() -> Optional[str]:
    """Escuta rapidamente e retorna o texto."""
    stt = SpeechToText()
    return stt.listen_once()


if __name__ == "__main__":
    # Teste do módulo
    print("Testando Speech-to-Text...")
    result = quick_listen()
    if result:
        print(f"Você disse: {result}")
    else:
        print("Nenhum texto reconhecido")
