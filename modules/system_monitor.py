"""
Módulo de Monitoramento de Sistema da SARA
Monitora CPU, memória, bateria, clipboard e atividade do usuário
"""
import threading
import time
from typing import Callable, Optional, Dict
from dataclasses import dataclass
from enum import Enum

# Imports condicionais
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


class AlertType(Enum):
    """Tipos de alertas do sistema"""
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    BATTERY_LOW = "battery_low"
    CLIPBOARD_CODE = "clipboard_code"
    IDLE_DETECTED = "idle_detected"


@dataclass
class SystemStatus:
    """Status atual do sistema"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    battery_percent: Optional[float] = None
    battery_plugged: bool = True
    disk_percent: float = 0.0
    is_idle: bool = False
    idle_time: float = 0.0  # segundos


class SystemMonitor:
    """Monitor de sistema"""

    def __init__(self, callback: Optional[Callable[[AlertType, Dict], None]] = None):
        """
        Inicializa o monitor

        Args:
            callback: Função chamada quando alerta é detectado
        """
        self.callback = callback
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # Configurações de limites
        self.thresholds = {
            "cpu_high": 80,  # %
            "memory_high": 85,  # %
            "battery_low": 20,  # %
            "idle_time": 300,  # segundos (5 min)
        }

        # Estado
        self.status = SystemStatus()
        self.last_clipboard = ""
        self._last_alert_time: Dict[AlertType, float] = {}
        self._alert_cooldown = 300  # segundos entre alertas do mesmo tipo

        # Padrões para detectar código
        self._code_patterns = [
            "def ", "class ", "import ", "from ",  # Python
            "function ", "const ", "let ", "var ",  # JavaScript
            "public ", "private ", "void ",  # Java/C#
            "<?php", "<!DOCTYPE", "<html",  # Web
            "#include", "int main",  # C/C++
            "func ", "package ",  # Go
            "fn ", "let mut",  # Rust
        ]

    def start(self, interval: float = 5.0):
        """
        Inicia monitoramento em background

        Args:
            interval: Intervalo entre verificações em segundos
        """
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        """Para o monitoramento"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _monitor_loop(self, interval: float):
        """Loop de monitoramento"""
        while self.running:
            try:
                self._check_system()
                self._check_clipboard()
            except Exception as e:
                print(f"Erro no monitor: {e}")

            time.sleep(interval)

    def _check_system(self):
        """Verifica status do sistema"""
        if not HAS_PSUTIL:
            return

        # CPU
        self.status.cpu_percent = psutil.cpu_percent(interval=1)
        if self.status.cpu_percent > self.thresholds["cpu_high"]:
            self._emit_alert(AlertType.CPU_HIGH, {
                "value": self.status.cpu_percent,
                "threshold": self.thresholds["cpu_high"]
            })

        # Memória
        mem = psutil.virtual_memory()
        self.status.memory_percent = mem.percent
        if self.status.memory_percent > self.thresholds["memory_high"]:
            self._emit_alert(AlertType.MEMORY_HIGH, {
                "value": self.status.memory_percent,
                "threshold": self.thresholds["memory_high"]
            })

        # Bateria
        battery = psutil.sensors_battery()
        if battery:
            self.status.battery_percent = battery.percent
            self.status.battery_plugged = battery.power_plugged

            if (not battery.power_plugged and
                battery.percent < self.thresholds["battery_low"]):
                self._emit_alert(AlertType.BATTERY_LOW, {
                    "value": battery.percent,
                    "threshold": self.thresholds["battery_low"]
                })

        # Disco
        disk = psutil.disk_usage('/')
        self.status.disk_percent = disk.percent

    def _check_clipboard(self):
        """Verifica clipboard para código"""
        if not HAS_PYPERCLIP:
            return

        try:
            current = pyperclip.paste()
            if current == self.last_clipboard:
                return

            self.last_clipboard = current

            # Verifica se parece código
            if self._looks_like_code(current):
                self._emit_alert(AlertType.CLIPBOARD_CODE, {
                    "content": current[:200]  # Primeiros 200 chars
                })

        except Exception:
            pass  # Clipboard pode não estar disponível

    def _looks_like_code(self, text: str) -> bool:
        """Verifica se texto parece código"""
        if not text or len(text) < 10:
            return False

        # Verifica padrões conhecidos
        for pattern in self._code_patterns:
            if pattern in text:
                return True

        # Verifica características de código
        lines = text.split('\n')
        if len(lines) < 2:
            return False

        # Muita indentação sugere código
        indented_lines = sum(1 for line in lines if line.startswith(('    ', '\t')))
        if indented_lines > len(lines) * 0.3:
            return True

        # Muitos caracteres especiais de código
        code_chars = text.count('{') + text.count('}') + text.count(';')
        code_chars += text.count('(') + text.count(')') + text.count('[')
        if code_chars > len(text) * 0.05:
            return True

        return False

    def _emit_alert(self, alert_type: AlertType, data: Dict):
        """Emite alerta respeitando cooldown"""
        now = time.time()
        last_time = self._last_alert_time.get(alert_type, 0)

        if now - last_time < self._alert_cooldown:
            return

        self._last_alert_time[alert_type] = now

        if self.callback:
            self.callback(alert_type, data)

    def get_status_summary(self) -> str:
        """Retorna resumo do status do sistema"""
        lines = []

        if HAS_PSUTIL:
            lines.append(f"CPU: {self.status.cpu_percent:.1f}%")
            lines.append(f"RAM: {self.status.memory_percent:.1f}%")
            lines.append(f"Disco: {self.status.disk_percent:.1f}%")

            if self.status.battery_percent is not None:
                state = "AC" if self.status.battery_plugged else "Bateria"
                lines.append(f"{state}: {self.status.battery_percent:.0f}%")
        else:
            lines.append("Monitoramento indisponível.")
            lines.append("Requisito: pip install psutil")

        return "\n".join(lines)

    def set_threshold(self, key: str, value: float):
        """Define limite para alertas"""
        if key in self.thresholds:
            self.thresholds[key] = value

    def get_top_processes(self, n: int = 5) -> list:
        """Retorna top N processos por uso de CPU"""
        if not HAS_PSUTIL:
            return []

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                processes.append({
                    'name': info['name'],
                    'cpu': info['cpu_percent'],
                    'memory': info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Ordena por CPU
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        return processes[:n]
