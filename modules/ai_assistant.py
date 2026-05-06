"""
Módulo de Assistente AI
Usa a API GRATUITA do Groq para gerar respostas
Suporta análise de imagens com Llama Vision
"""
from groq import Groq
from typing import Optional, List, Dict
import base64
import sys
sys.path.append('..')
from config import AI_CONFIG, ASSISTANT_SYSTEM_PROMPT, GROQ_API_KEY


class AIAssistant:
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o assistente AI com Groq (GRATUITO!).
        
        Args:
            api_key: Chave da API Groq (ou usa variável de ambiente)
        """
        key = api_key or GROQ_API_KEY
        if key:
            self.client = Groq(api_key=key)
        else:
            self.client = Groq()  # Tenta usar variável de ambiente GROQ_API_KEY
            
        self.model = AI_CONFIG["model"]
        self.vision_model = "llama-3.2-90b-vision-preview"  # Modelo com visão
        self.max_tokens = AI_CONFIG["max_tokens"]
        self.temperature = AI_CONFIG["temperature"]
        
        # Histórico de conversação
        self.conversation_history: List[Dict] = []
        self.max_history = 20  # Mantém últimas 20 mensagens
        
        # System prompt personalizado
        self.system_prompt = ASSISTANT_SYSTEM_PROMPT
    
    def chat(self, user_message: str, image_path: Optional[str] = None) -> str:
        """
        Envia uma mensagem e recebe a resposta do assistente.
        Pode incluir uma imagem para análise.
        
        Args:
            user_message: Mensagem do usuário
            image_path: Caminho para imagem (opcional)
            
        Returns:
            Resposta do assistente
        """
        # Prepara o conteúdo da mensagem
        if image_path:
            content = self._create_image_message(user_message, image_path)
            model_to_use = self.vision_model
        else:
            content = user_message
            model_to_use = self.model
        
        # Adiciona mensagem ao histórico
        self.conversation_history.append({
            "role": "user",
            "content": content
        })
        
        # Limita o histórico
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        try:
            # Monta mensagens com system prompt
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            response = self.client.chat.completions.create(
                model=model_to_use,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=messages
            )
            
            assistant_message = response.choices[0].message.content
            
            # Adiciona resposta ao histórico (só texto)
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "api_key" in error_msg or "authentication" in error_msg:
                return "Senhor, a API key não está configurada. Verifique a variável GROQ_API_KEY."
            elif "rate" in error_msg or "limit" in error_msg:
                return "Rate limit atingido. Aguarde alguns segundos antes da próxima requisição."
            elif "connection" in error_msg:
                return "Falha na conexão com o servidor. Verifique a conectividade."
            elif "vision" in error_msg or "image" in error_msg:
                return "Falha ao processar a imagem. Tente outro formato ou arquivo."
            else:
                return f"Erro na operação: {str(e)[:100]}"
    
    def _create_image_message(self, text: str, image_path: str) -> list:
        """Cria mensagem com imagem em base64."""
        try:
            # Lê e codifica a imagem
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")
            
            # Detecta tipo da imagem
            if image_path.lower().endswith(".png"):
                media_type = "image/png"
            elif image_path.lower().endswith((".jpg", ".jpeg")):
                media_type = "image/jpeg"
            elif image_path.lower().endswith(".gif"):
                media_type = "image/gif"
            elif image_path.lower().endswith(".webp"):
                media_type = "image/webp"
            else:
                media_type = "image/png"
            
            return [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_data}"
                    }
                },
                {
                    "type": "text",
                    "text": text if text else "O que você vê nesta imagem? Se for código, analise e me ajude."
                }
            ]
        except Exception as e:
            print(f"Erro ao processar imagem: {e}")
            return text
    
    def analyze_image(self, image_path: str, prompt: str = None) -> str:
        """
        Analisa uma imagem e retorna descrição/análise.
        
        Args:
            image_path: Caminho para a imagem
            prompt: Pergunta específica sobre a imagem
            
        Returns:
            Análise da imagem
        """
        if not prompt:
            prompt = "Analise esta imagem detalhadamente. Se for código, explique o que faz e identifique possíveis problemas."
        
        return self.chat(prompt, image_path=image_path)
    
    def clear_history(self):
        """Limpa o histórico de conversação."""
        self.conversation_history = []
    
    def get_simple_response(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Obtém uma resposta simples sem manter histórico.
        Útil para análises pontuais.
        
        Args:
            prompt: Prompt para o modelo
            system: System prompt customizado (opcional)
            
        Returns:
            Resposta do modelo
        """
        try:
            messages = [
                {"role": "system", "content": system or "Responda de forma breve e direta."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=100,
                temperature=0.3,
                messages=messages
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Erro: {str(e)}"


if __name__ == "__main__":
    # Teste do módulo
    print("Testando AI Assistant (Groq)...")
    
    try:
        assistant = AIAssistant()
        
        # Teste de chat
        response = assistant.chat("Olá! Qual é o seu nome?")
        print(f"Resposta: {response}")
        
    except Exception as e:
        print(f"Erro no teste: {e}")
        print("Certifique-se de que a variável GROQ_API_KEY está configurada.")
