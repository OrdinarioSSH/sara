"""
Módulo de Análise de Humor
Analisa o sentimento do usuário para adaptar as reações do pet
"""
from typing import Tuple
import sys
sys.path.append('..')
from config import MOOD_ANALYSIS_PROMPT, MOOD_COLORS


class MoodAnalyzer:
    def __init__(self, ai_assistant=None):
        """
        Inicializa o analisador de humor.
        
        Args:
            ai_assistant: Instância do AIAssistant para análise
        """
        self.ai_assistant = ai_assistant
        self.current_mood = "neutro"
        self.valid_moods = list(MOOD_COLORS.keys())
    
    def analyze(self, message: str) -> Tuple[str, str]:
        """
        Analisa o humor baseado na mensagem.
        
        Args:
            message: Mensagem do usuário
            
        Returns:
            Tupla (humor, cor_hex)
        """
        if not self.ai_assistant:
            return self._simple_analysis(message)
        
        try:
            prompt = MOOD_ANALYSIS_PROMPT.format(message=message)
            response = self.ai_assistant.get_simple_response(
                prompt,
                system="Você é um analisador de sentimentos. Responda apenas com a palavra do humor detectado."
            )
            
            # Normaliza a resposta
            detected_mood = response.lower().strip()
            
            # Valida o humor
            for mood in self.valid_moods:
                if mood in detected_mood:
                    self.current_mood = mood
                    return mood, MOOD_COLORS[mood]
            
            # Fallback para neutro
            return "neutro", MOOD_COLORS["neutro"]
            
        except Exception as e:
            print(f"Erro na análise de humor: {e}")
            return self._simple_analysis(message)
    
    def _simple_analysis(self, message: str) -> Tuple[str, str]:
        """
        Análise simples baseada em palavras-chave (fallback).
        """
        message = message.lower()
        
        # Palavras-chave para cada humor
        mood_keywords = {
            "feliz": ["feliz", "legal", "ótimo", "maravilh", "adoro", "amo", "obrigad", "valeu", ":)", "haha", "rsrs"],
            "triste": ["triste", "chateado", "mal", "ruim", "péssimo", "infeliz", ":(", "decepcion"],
            "irritado": ["raiva", "irritad", "bravo", "ódio", "droga", "merda", "porra", "inferno"],
            "animado": ["animad", "empolgad", "eba", "uhul", "vamos", "bora", "!!", "nossa"],
            "cansado": ["cansad", "exaust", "sono", "dormir", "esgotad", "preguiça"],
            "curioso": ["como", "por que", "o que", "quando", "onde", "quem", "?"],
        }
        
        for mood, keywords in mood_keywords.items():
            if any(kw in message for kw in keywords):
                self.current_mood = mood
                return mood, MOOD_COLORS[mood]
        
        return "neutro", MOOD_COLORS["neutro"]
    
    def get_current_mood(self) -> Tuple[str, str]:
        """Retorna o humor atual e sua cor."""
        return self.current_mood, MOOD_COLORS.get(self.current_mood, MOOD_COLORS["neutro"])


if __name__ == "__main__":
    # Teste do módulo
    print("Testando Mood Analyzer...")
    
    analyzer = MoodAnalyzer()  # Sem AI, usa análise simples
    
    test_messages = [
        "Estou muito feliz hoje!",
        "Que droga, nada funciona",
        "Hmm, interessante...",
        "Estou cansado demais",
        "Como funciona isso?",
        "Oi, tudo bem?",
    ]
    
    for msg in test_messages:
        mood, color = analyzer.analyze(msg)
        print(f"'{msg}' -> {mood} ({color})")
