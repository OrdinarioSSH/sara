"""
Módulo de Memória Persistente da SARA
Salva e carrega estado do pet, preferências do usuário e histórico
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict, field


@dataclass
class PetState:
    """Estado persistente do pet"""
    # Configurações visuais
    display_mode: str = "hud"  # "hud" ou "skin"
    current_skin: str = "robot_skin"
    pet_size: int = 150
    position_x: int = 100
    position_y: int = 100

    # Estados
    modo_passeio: bool = False
    voice_enabled: bool = True

    # Estatísticas
    total_interactions: int = 0
    total_messages: int = 0
    created_at: str = ""
    last_seen: str = ""


@dataclass
class UserPreferences:
    """Preferências do usuário"""
    # Voz
    tts_enabled: bool = True
    tts_voice: str = "piper"
    tts_speed: float = 1.0

    # Proatividade
    proactive_enabled: bool = True
    pause_reminder_interval: int = 45
    tips_enabled: bool = True
    tips_interval: int = 30
    greetings_enabled: bool = True

    # Sistema
    start_minimized: bool = False
    start_with_windows: bool = False
    show_in_tray: bool = True

    # Pomodoro
    pomodoro_work: int = 25
    pomodoro_short_break: int = 5
    pomodoro_long_break: int = 15


@dataclass
class ConversationEntry:
    """Entrada de histórico de conversa"""
    timestamp: str
    role: str  # "user" ou "assistant"
    content: str


class MemoryManager:
    """Gerenciador de memória persistente"""

    def __init__(self, data_dir: str = "data"):
        """
        Inicializa o gerenciador de memória

        Args:
            data_dir: Diretório para salvar dados
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.state_file = self.data_dir / "pet_state.json"
        self.prefs_file = self.data_dir / "preferences.json"
        self.history_file = self.data_dir / "conversation_history.json"
        self.notes_file = self.data_dir / "notes.json"
        self.memories_file = self.data_dir / "memories.json"
        self.corrections_file = self.data_dir / "corrections.json"

        # Estado em memória
        self.pet_state = PetState()
        self.preferences = UserPreferences()
        self.conversation_history: List[ConversationEntry] = []
        self.notes: List[Dict] = []
        self.memories: List[Dict] = []
        self.corrections: List[Dict] = []

        # Carrega dados existentes
        self.load_all()

    def load_all(self):
        """Carrega todos os dados"""
        self._load_pet_state()
        self._load_preferences()
        self._load_conversation_history()
        self._load_notes()
        self._load_memories()
        self._load_corrections()

    def save_all(self):
        """Salva todos os dados"""
        self._save_pet_state()
        self._save_preferences()
        self._save_conversation_history()
        self._save_notes()
        self._save_memories()
        self._save_corrections()

    # ========== PET STATE ==========

    def _load_pet_state(self):
        """Carrega estado do pet"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.pet_state = PetState(**data)
            except Exception as e:
                print(f"Erro ao carregar estado: {e}")
                self.pet_state = PetState()
        else:
            self.pet_state = PetState(created_at=datetime.now().isoformat())

    def _save_pet_state(self):
        """Salva estado do pet"""
        self.pet_state.last_seen = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.pet_state), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar estado: {e}")

    def update_pet_config(self, **kwargs):
        """Atualiza configurações do pet"""
        for key, value in kwargs.items():
            if hasattr(self.pet_state, key):
                setattr(self.pet_state, key, value)

    def increment_interaction(self):
        """Incrementa contador de interações"""
        self.pet_state.total_interactions += 1

    def increment_messages(self):
        """Incrementa contador de mensagens"""
        self.pet_state.total_messages += 1

    # ========== PREFERENCES ==========

    def _load_preferences(self):
        """Carrega preferências"""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.preferences = UserPreferences(**data)
            except Exception as e:
                print(f"Erro ao carregar preferências: {e}")
                self.preferences = UserPreferences()
        else:
            self.preferences = UserPreferences()

    def _save_preferences(self):
        """Salva preferências"""
        try:
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.preferences), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar preferências: {e}")

    def update_preferences(self, **kwargs):
        """Atualiza preferências"""
        for key, value in kwargs.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
        self._save_preferences()

    # ========== CONVERSATION HISTORY ==========

    def _load_conversation_history(self):
        """Carrega histórico de conversas"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = [
                        ConversationEntry(**entry) for entry in data
                    ]
            except Exception as e:
                print(f"Erro ao carregar histórico: {e}")
                self.conversation_history = []

    def _save_conversation_history(self):
        """Salva histórico de conversas"""
        try:
            # Mantém apenas últimas 100 mensagens
            history_to_save = self.conversation_history[-100:]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(entry) for entry in history_to_save], f,
                         indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar histórico: {e}")

    def add_conversation(self, role: str, content: str):
        """Adiciona mensagem ao histórico"""
        entry = ConversationEntry(
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content
        )
        self.conversation_history.append(entry)
        self.increment_messages()

    def get_recent_conversations(self, n: int = 10) -> List[Dict]:
        """Retorna últimas N conversas"""
        return [asdict(entry) for entry in self.conversation_history[-n:]]

    def clear_conversation_history(self):
        """Limpa histórico de conversas"""
        self.conversation_history = []
        self._save_conversation_history()

    # ========== NOTES ==========

    def _load_notes(self):
        """Carrega notas"""
        if self.notes_file.exists():
            try:
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    self.notes = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar notas: {e}")
                self.notes = []

    def _save_notes(self):
        """Salva notas"""
        try:
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(self.notes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar notas: {e}")

    def add_note(self, content: str, title: str = "") -> Dict:
        """Adiciona uma nota"""
        note = {
            "id": len(self.notes) + 1,
            "title": title,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.notes.append(note)
        self._save_notes()
        return note

    def update_note(self, note_id: int, content: str, title: str = None):
        """Atualiza uma nota"""
        for note in self.notes:
            if note["id"] == note_id:
                note["content"] = content
                if title is not None:
                    note["title"] = title
                note["updated_at"] = datetime.now().isoformat()
                self._save_notes()
                return note
        return None

    def delete_note(self, note_id: int) -> bool:
        """Deleta uma nota"""
        for i, note in enumerate(self.notes):
            if note["id"] == note_id:
                del self.notes[i]
                self._save_notes()
                return True
        return False

    def get_notes(self) -> List[Dict]:
        """Retorna todas as notas"""
        return self.notes

    # ========== MEMORIES (Memória de longo prazo) ==========

    def _load_memories(self):
        """Carrega memórias persistentes"""
        if self.memories_file.exists():
            try:
                with open(self.memories_file, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar memórias: {e}")
                self.memories = []

    def _save_memories(self):
        """Salva memórias persistentes"""
        try:
            with open(self.memories_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar memórias: {e}")

    def add_memory(self, content: str, source: str = "auto") -> Dict:
        """Adiciona uma memória de longo prazo.

        Args:
            content: Fato/informação a memorizar
            source: Origem (voz, chat, auto)
        """
        memory = {
            "id": len(self.memories) + 1,
            "content": content.strip(),
            "source": source,
            "created_at": datetime.now().isoformat()
        }
        self.memories.append(memory)
        self._save_memories()
        return memory

    def get_memories(self) -> List[Dict]:
        """Retorna todas as memórias"""
        return self.memories

    def delete_memory(self, memory_id: int) -> bool:
        """Remove uma memória"""
        for i, mem in enumerate(self.memories):
            if mem["id"] == memory_id:
                del self.memories[i]
                self._save_memories()
                return True
        return False

    # ========== CORRECTIONS (Aprendizado por erro) ==========

    def _load_corrections(self):
        """Carrega correções aprendidas"""
        if self.corrections_file.exists():
            try:
                with open(self.corrections_file, 'r', encoding='utf-8') as f:
                    self.corrections = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar correções: {e}")
                self.corrections = []

    def _save_corrections(self):
        """Salva correções aprendidas"""
        try:
            # Mantém últimas 50 correções
            corrections_to_save = self.corrections[-50:]
            with open(self.corrections_file, 'w', encoding='utf-8') as f:
                json.dump(corrections_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar correções: {e}")

    def add_correction(self, user_said: str, sara_did: str, correction: str, source: str = "auto") -> Dict:
        """Registra uma correção/aprendizado.

        Args:
            user_said: O que o usuário pediu originalmente
            sara_did: O que SARA fez/disse de errado
            correction: A correção ou o que deveria ter feito
            source: Origem (voz, chat, auto)
        """
        entry = {
            "id": len(self.corrections) + 1,
            "user_said": user_said.strip(),
            "sara_did": sara_did.strip()[:200],
            "correction": correction.strip(),
            "source": source,
            "times_applied": 0,
            "created_at": datetime.now().isoformat()
        }
        self.corrections.append(entry)
        self._save_corrections()
        return entry

    def get_corrections(self) -> List[Dict]:
        """Retorna todas as correções"""
        return self.corrections

    def get_relevant_corrections(self, context: str, limit: int = 10) -> List[Dict]:
        """Retorna correções relevantes para o contexto atual.

        Busca correções cujas palavras-chave aparecem no contexto.
        """
        if not self.corrections or not context:
            return self.corrections[-limit:]

        context_lower = context.lower()
        scored = []
        for corr in self.corrections:
            # Pontua pela relevância ao contexto atual
            score = 0
            words_user = set(corr.get("user_said", "").lower().split())
            words_correction = set(corr.get("correction", "").lower().split())
            context_words = set(context_lower.split())

            # Palavras em comum
            common = words_user & context_words
            score += len(common) * 2
            common_corr = words_correction & context_words
            score += len(common_corr)

            scored.append((score, corr))

        # Ordena por relevância, pega as mais relevantes + as mais recentes
        scored.sort(key=lambda x: x[0], reverse=True)
        relevant = [c for s, c in scored if s > 0][:limit // 2]

        # Completa com as mais recentes
        recent = self.corrections[-(limit // 2):]
        seen_ids = {c["id"] for c in relevant}
        for c in recent:
            if c["id"] not in seen_ids:
                relevant.append(c)

        return relevant[:limit]

    def increment_correction_usage(self, correction_id: int):
        """Marca uma correção como aplicada."""
        for corr in self.corrections:
            if corr["id"] == correction_id:
                corr["times_applied"] = corr.get("times_applied", 0) + 1
                self._save_corrections()
                return

    # ========== STATISTICS ==========

    def get_statistics(self) -> Dict:
        """Retorna estatísticas do pet"""
        created = self.pet_state.created_at
        if created:
            try:
                created_dt = datetime.fromisoformat(created)
                days_alive = (datetime.now() - created_dt).days
            except:
                days_alive = 0
        else:
            days_alive = 0

        return {
            "days_alive": days_alive,
            "total_interactions": self.pet_state.total_interactions,
            "total_messages": self.pet_state.total_messages,
            "created_at": self.pet_state.created_at,
            "last_seen": self.pet_state.last_seen,
            "notes_count": len(self.notes)
        }

    # ========== CONTEXT FOR AI ==========

    def get_context_for_ai(self) -> str:
        """Gera contexto operacional para a SARA."""
        stats = self.get_statistics()
        recent = self.get_recent_conversations(10)

        context_parts = []

        # Dados do Operador
        context_parts.append(f"Tempo de operação com o Operador: {stats['days_alive']} dias.")
        context_parts.append(f"Total de interações registradas: {stats['total_messages']}.")
        if stats.get('last_seen'):
            context_parts.append(f"Última sessão: {stats['last_seen'][:16]}.")

        # Histórico recente para gestão de contexto
        if recent:
            context_parts.append("\n### Histórico recente (para referência cruzada):")
            for entry in recent[-5:]:
                role = "Operador" if entry['role'] == 'user' else "SARA"
                content = entry['content'][:150]
                ts = entry.get('timestamp', '')[:16]
                context_parts.append(f"- [{ts}] {role}: {content}")

        # Notas do operador
        if self.notes:
            context_parts.append(f"\n### Notas do Operador ({len(self.notes)} registradas):")
            for note in self.notes[-5:]:
                title = note.get('title', 'Sem título')
                content = note.get('content', '')[:80]
                context_parts.append(f"- **{title}**: {content}")

        # Memórias de longo prazo
        if self.memories:
            context_parts.append(f"\n### Memórias do Operador ({len(self.memories)} registradas):")
            for mem in self.memories[-15:]:
                content = mem.get('content', '')
                ts = mem.get('created_at', '')[:10]
                context_parts.append(f"- [{ts}] {content}")

        # Correções aprendidas (erros passados para não repetir)
        if self.corrections:
            context_parts.append(f"\n### Correções Aprendidas ({len(self.corrections)} registradas):")
            context_parts.append("IMPORTANTE: Estes são erros que você cometeu e DEVE evitar repetir.")
            for corr in self.corrections[-10:]:
                user_said = corr.get('user_said', '')
                sara_did = corr.get('sara_did', '')[:100]
                correction = corr.get('correction', '')
                context_parts.append(f"- Operador pediu: \"{user_said}\" → Você errou: \"{sara_did}\" → Correto: \"{correction}\"")

        # Instrução de uso do contexto
        context_parts.append("\nUse estas informações para conectar assuntos, antecipar necessidades e validar decisões do Operador. Preste atenção especial às correções para não repetir erros.")

        return "\n".join(context_parts)
