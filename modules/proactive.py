"""
Módulo de Comportamento Proativo da SARA
Gerencia lembretes, dicas, saudações e comportamentos automáticos
"""
import random
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class ProactiveEventType(Enum):
    """Tipos de eventos proativos"""
    GREETING = "greeting"
    PAUSE_REMINDER = "pause_reminder"
    TIP = "tip"
    ATTENTION = "attention"
    SYSTEM_ALERT = "system_alert"
    ATTRIBUTE_WARNING = "attribute_warning"
    SCHEDULED = "scheduled"
    POMODORO = "pomodoro"


@dataclass
class ProactiveEvent:
    """Representa um evento proativo"""
    event_type: ProactiveEventType
    message: str
    priority: int = 1  # 1 = baixa, 5 = alta
    duration: int = 4000  # ms para mostrar
    speak: bool = False  # Se deve falar a mensagem
    callback: Optional[Callable] = None


@dataclass
class PomodoroState:
    """Estado do timer Pomodoro"""
    is_active: bool = False
    is_break: bool = False
    work_duration: int = 25  # minutos
    short_break: int = 5
    long_break: int = 15
    sessions_completed: int = 0
    current_time_left: int = 0  # segundos
    timer: Optional[threading.Timer] = None


class ProactiveManager:
    """Gerenciador de comportamentos proativos"""

    def __init__(self, config: Dict, messages: Dict, callback: Callable[[ProactiveEvent], None]):
        """
        Inicializa o gerenciador proativo

        Args:
            config: Configurações de proatividade
            messages: Dicionário de mensagens
            callback: Função chamada quando evento deve ser mostrado
        """
        self.config = config
        self.messages = messages
        self.callback = callback

        # Contadores
        self.minutes_since_pause = 0
        self.minutes_since_tip = 0
        self.minutes_since_interaction = 0
        self.greeted_today = False
        self.last_greeting_date = None

        # Pomodoro
        self.pomodoro = PomodoroState()

        # Fila de eventos pendentes
        self.event_queue: List[ProactiveEvent] = []

        # Timers
        self._timers: List[threading.Timer] = []

    def tick(self):
        """Chamado a cada minuto para verificar ações"""
        self.minutes_since_pause += 1
        self.minutes_since_tip += 1
        self.minutes_since_interaction += 1

        self._check_pause_reminder()
        self._check_productivity_tip()
        self._check_greeting()

    def _check_pause_reminder(self):
        """Verifica se deve lembrar pausa"""
        interval = self.config.get("pause_reminder_interval", 45)
        if self.minutes_since_pause >= interval:
            messages = self.messages.get("pause_reminders", ["Hora de uma pausa!"])
            self._emit_event(ProactiveEvent(
                event_type=ProactiveEventType.PAUSE_REMINDER,
                message=random.choice(messages),
                priority=2,
                duration=5000
            ))
            self.minutes_since_pause = 0

    def _check_productivity_tip(self):
        """Verifica se deve mostrar dica"""
        if not self.config.get("random_tips_enabled", True):
            return

        interval = self.config.get("tips_interval", 30)
        if self.minutes_since_tip >= interval:
            messages = self.messages.get("productivity_tips", ["Dica do dia!"])
            self._emit_event(ProactiveEvent(
                event_type=ProactiveEventType.TIP,
                message=random.choice(messages),
                priority=1,
                duration=6000
            ))
            self.minutes_since_tip = 0

    def _check_greeting(self):
        """Verifica se deve cumprimentar"""
        if not self.config.get("greeting_enabled", True):
            return

        today = datetime.now().date()
        if self.last_greeting_date == today:
            return

        self.last_greeting_date = today
        self._emit_greeting()

    def _emit_greeting(self):
        """Emite saudação baseada na hora"""
        hour = datetime.now().hour

        if 5 <= hour < 12:
            messages = self.messages.get("morning_greetings", ["Bom dia!"])
        elif 12 <= hour < 18:
            messages = self.messages.get("afternoon_greetings", ["Boa tarde!"])
        else:
            messages = self.messages.get("evening_greetings", ["Boa noite!"])

        self._emit_event(ProactiveEvent(
            event_type=ProactiveEventType.GREETING,
            message=random.choice(messages),
            priority=2,
            duration=4000,
            speak=True
        ))

    def check_attention(self, felicidade: int = 100):
        """Verifica se pet deve pedir atenção"""
        # Se mais de 10 minutos sem interação
        if self.minutes_since_interaction < 10:
            return

        if random.random() > 0.3:
            return

        if felicidade > 50:
            messages = self.messages.get("idle_messages", ["Sistemas em standby."])
        else:
            messages = self.messages.get("attention_seeking", ["Alguma tarefa pendente?"])

        self._emit_event(ProactiveEvent(
            event_type=ProactiveEventType.ATTENTION,
            message=random.choice(messages),
            priority=1,
            duration=4000
        ))

    def emit_attribute_warning(self, attribute: str):
        """Emite aviso de atributo baixo"""
        warnings = {
            "fome": "Senhor, refeição pendente. Nutrição impacta rendimento.",
            "energia": "Nível de energia baixo. Pausa recomendada.",
            "higiene": "Lembrete de autocuidado pendente.",
            "felicidade": "Indicadores de bem-estar abaixo do ideal.",
            "diversao": "Sem atividade de lazer recente. Equilíbrio é estratégico.",
            "saude": "Atenção à saúde recomendada. Prioridade alta."
        }

        msg = warnings.get(attribute, "Atenção necessária.")
        self._emit_event(ProactiveEvent(
            event_type=ProactiveEventType.ATTRIBUTE_WARNING,
            message=msg,
            priority=3,
            duration=5000
        ))

    def emit_system_alert(self, alert_type: str):
        """Emite alerta de sistema"""
        if alert_type == "cpu_high":
            messages = self.messages.get("cpu_high", ["CPU alta!"])
        elif alert_type == "memory_high":
            messages = self.messages.get("memory_high", ["Memória alta!"])
        elif alert_type == "clipboard_code":
            messages = self.messages.get("clipboard_code", ["Código detectado!"])
        else:
            messages = ["Alerta do sistema!"]

        self._emit_event(ProactiveEvent(
            event_type=ProactiveEventType.SYSTEM_ALERT,
            message=random.choice(messages),
            priority=4,
            duration=5000
        ))

    def on_interaction(self):
        """Chamado quando usuário interage"""
        self.minutes_since_interaction = 0

    def _emit_event(self, event: ProactiveEvent):
        """Emite evento para callback"""
        if self.callback:
            self.callback(event)

    # ========== POMODORO ==========

    def start_pomodoro(self, work_minutes: int = 25, short_break: int = 5, long_break: int = 15):
        """Inicia sessão Pomodoro"""
        self.pomodoro.work_duration = work_minutes
        self.pomodoro.short_break = short_break
        self.pomodoro.long_break = long_break
        self.pomodoro.is_active = True
        self.pomodoro.is_break = False
        self.pomodoro.current_time_left = work_minutes * 60

        self._emit_event(ProactiveEvent(
            event_type=ProactiveEventType.POMODORO,
            message=f"Pomodoro iniciado. {work_minutes}min de foco.",
            priority=3,
            duration=4000,
            speak=True
        ))

        self._schedule_pomodoro_end()

    def _schedule_pomodoro_end(self):
        """Agenda fim do período atual"""
        if self.pomodoro.timer:
            self.pomodoro.timer.cancel()

        seconds = self.pomodoro.current_time_left
        self.pomodoro.timer = threading.Timer(seconds, self._on_pomodoro_period_end)
        self.pomodoro.timer.daemon = True
        self.pomodoro.timer.start()

    def _on_pomodoro_period_end(self):
        """Chamado quando período termina"""
        if not self.pomodoro.is_active:
            return

        if self.pomodoro.is_break:
            # Fim do intervalo, volta ao trabalho
            self.pomodoro.is_break = False
            self.pomodoro.current_time_left = self.pomodoro.work_duration * 60

            self._emit_event(ProactiveEvent(
                event_type=ProactiveEventType.POMODORO,
                message="Intervalo encerrado. De volta ao foco.",
                priority=4,
                duration=5000,
                speak=True
            ))
        else:
            # Fim do trabalho, inicia intervalo
            self.pomodoro.sessions_completed += 1
            self.pomodoro.is_break = True

            # A cada 4 sessões, intervalo longo
            if self.pomodoro.sessions_completed % 4 == 0:
                break_time = self.pomodoro.long_break
                msg = f"4 sessões concluídas. Pausa longa de {break_time}min."
            else:
                break_time = self.pomodoro.short_break
                msg = f"Sessão concluída. Pausa de {break_time}min recomendada."

            self.pomodoro.current_time_left = break_time * 60

            self._emit_event(ProactiveEvent(
                event_type=ProactiveEventType.POMODORO,
                message=msg,
                priority=4,
                duration=5000,
                speak=True
            ))

        self._schedule_pomodoro_end()

    def stop_pomodoro(self):
        """Para o Pomodoro"""
        if self.pomodoro.timer:
            self.pomodoro.timer.cancel()

        self.pomodoro.is_active = False

        self._emit_event(ProactiveEvent(
            event_type=ProactiveEventType.POMODORO,
            message=f"Pomodoro pausado. {self.pomodoro.sessions_completed} sessões registradas.",
            priority=2,
            duration=4000
        ))

    def get_pomodoro_status(self) -> str:
        """Retorna status do Pomodoro"""
        if not self.pomodoro.is_active:
            return "Pomodoro inativo"

        minutes = self.pomodoro.current_time_left // 60
        seconds = self.pomodoro.current_time_left % 60

        if self.pomodoro.is_break:
            return f"Intervalo: {minutes:02d}:{seconds:02d}"
        else:
            return f"Foco: {minutes:02d}:{seconds:02d}"

    def cleanup(self):
        """Limpa recursos"""
        if self.pomodoro.timer:
            self.pomodoro.timer.cancel()
        for timer in self._timers:
            timer.cancel()
