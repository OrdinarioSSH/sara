"""
Módulo de Notificações da SARA
Gerencia balões de fala, notificações do sistema e toast messages
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QPushButton, QGraphicsOpacityEffect, QApplication)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class NotificationType(Enum):
    """Tipos de notificação"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    QUESTION = "question"


@dataclass
class NotificationStyle:
    """Estilo de notificação"""
    bg_color: str
    border_color: str
    text_color: str
    icon: str


# Estilos pré-definidos
NOTIFICATION_STYLES = {
    NotificationType.INFO: NotificationStyle(
        bg_color="rgba(52, 152, 219, 0.95)",
        border_color="#2980b9",
        text_color="white",
        icon="💬"
    ),
    NotificationType.SUCCESS: NotificationStyle(
        bg_color="rgba(46, 204, 113, 0.95)",
        border_color="#27ae60",
        text_color="white",
        icon="✅"
    ),
    NotificationType.WARNING: NotificationStyle(
        bg_color="rgba(241, 196, 15, 0.95)",
        border_color="#f39c12",
        text_color="#333",
        icon="⚠️"
    ),
    NotificationType.ERROR: NotificationStyle(
        bg_color="rgba(231, 76, 60, 0.95)",
        border_color="#c0392b",
        text_color="white",
        icon="❌"
    ),
    NotificationType.QUESTION: NotificationStyle(
        bg_color="rgba(155, 89, 182, 0.95)",
        border_color="#8e44ad",
        text_color="white",
        icon="❓"
    ),
}


class SpeechBubble(QWidget):
    """Balão de fala que aparece sobre o pet"""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self):
        """Configura UI do balão"""
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

    def _setup_animations(self):
        """Configura animações"""
        # Timer para auto-fechar
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

        # Efeito de opacidade
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        # Animação de fade
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def show_message(self, text: str, duration: int = 4000,
                    position: Optional[QPoint] = None,
                    notification_type: NotificationType = NotificationType.INFO):
        """
        Mostra mensagem no balão

        Args:
            text: Texto a mostrar
            duration: Duração em ms (0 para não fechar automaticamente)
            position: Posição do pet para posicionar balão acima
            notification_type: Tipo de notificação para estilo
        """
        # Aplica estilo
        style = NOTIFICATION_STYLES.get(notification_type, NOTIFICATION_STYLES[NotificationType.INFO])
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {style.bg_color};
                color: {style.text_color};
                border: 2px solid {style.border_color};
                border-radius: 15px;
                padding: 12px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)

        self.label.setText(text)
        self.adjustSize()

        # Posiciona acima do pet
        if position:
            x = position.x() - self.width() // 2 + 75
            y = position.y() - self.height() - 15

            # Garante que não saia da tela
            screen = QApplication.primaryScreen().geometry()
            x = max(10, min(x, screen.width() - self.width() - 10))
            y = max(10, y)

            self.move(x, y)

        # Fade in
        self.show()
        self.raise_()
        self.fade_animation.stop()
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

        # Timer para fechar
        if duration > 0:
            self.hide_timer.start(duration)

    def fade_out(self):
        """Anima saída do balão"""
        self.fade_animation.stop()
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._on_fade_out_complete)
        self.fade_animation.start()

    def _on_fade_out_complete(self):
        """Chamado quando fade out termina"""
        self.fade_animation.finished.disconnect(self._on_fade_out_complete)
        self.hide()

    def mousePressEvent(self, event):
        """Clique no balão"""
        self.clicked.emit()
        self.fade_out()


class ToastNotification(QWidget):
    """Notificação toast no canto da tela"""

    action_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self):
        """Configura UI"""
        self.setFixedWidth(300)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Container
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(44, 62, 80, 0.95);
                border-radius: 10px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 12, 15, 12)
        container_layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()

        self.icon_label = QLabel("💬")
        self.icon_label.setStyleSheet("font-size: 18px; background: transparent;")
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel("SARA")
        self.title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: white;
            background: transparent;
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #95a5a6;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        self.close_btn.clicked.connect(self.fade_out)
        header_layout.addWidget(self.close_btn)

        container_layout.addLayout(header_layout)

        # Mensagem
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            font-size: 12px;
            color: #ecf0f1;
            background: transparent;
        """)
        container_layout.addWidget(self.message_label)

        # Botões de ação
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)
        container_layout.addLayout(self.actions_layout)

        main_layout.addWidget(self.container)
        self.setLayout(main_layout)

    def _setup_animations(self):
        """Configura animações"""
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Animação de slide
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutBack)

    def show_notification(self, message: str, title: str = "SARA",
                         duration: int = 5000,
                         notification_type: NotificationType = NotificationType.INFO,
                         actions: Optional[list] = None):
        """
        Mostra notificação

        Args:
            message: Mensagem
            title: Título
            duration: Duração em ms
            notification_type: Tipo de notificação
            actions: Lista de tuples (texto, callback_key)
        """
        style = NOTIFICATION_STYLES.get(notification_type, NOTIFICATION_STYLES[NotificationType.INFO])

        self.icon_label.setText(style.icon)
        self.title_label.setText(title)
        self.message_label.setText(message)

        # Limpa ações anteriores
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Adiciona novas ações
        if actions:
            for text, key in actions:
                btn = QPushButton(text)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {style.border_color};
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 10px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {style.bg_color};
                    }}
                """)
                btn.clicked.connect(lambda checked, k=key: self._on_action(k))
                self.actions_layout.addWidget(btn)

        self.adjustSize()

        # Posiciona no canto inferior direito
        screen = QApplication.primaryScreen().geometry()
        start_x = screen.width() - self.width() - 20
        start_y = screen.height()
        end_y = screen.height() - self.height() - 60

        self.move(start_x, start_y)
        self.show()
        self.raise_()

        # Animação de entrada
        self.slide_animation.setDuration(400)
        self.slide_animation.setStartValue(QPoint(start_x, start_y))
        self.slide_animation.setEndValue(QPoint(start_x, end_y))
        self.slide_animation.start()

        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

        if duration > 0:
            self.hide_timer.start(duration)

    def fade_out(self):
        """Fecha com animação"""
        self.hide_timer.stop()

        screen = QApplication.primaryScreen().geometry()
        current_pos = self.pos()
        end_y = screen.height()

        self.slide_animation.setDuration(300)
        self.slide_animation.setStartValue(current_pos)
        self.slide_animation.setEndValue(QPoint(current_pos.x(), end_y))
        self.slide_animation.start()

        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()

    def _on_action(self, key: str):
        """Callback de ação"""
        self.action_clicked.emit(key)
        self.fade_out()


class NotificationManager:
    """Gerenciador de notificações"""

    def __init__(self):
        self.speech_bubble = SpeechBubble()
        self.toast = ToastNotification()
        self._toast_queue = []

    def show_bubble(self, text: str, duration: int = 4000,
                   position: Optional[QPoint] = None,
                   notification_type: NotificationType = NotificationType.INFO):
        """Mostra balão de fala"""
        self.speech_bubble.show_message(text, duration, position, notification_type)

    def show_toast(self, message: str, title: str = "SARA",
                  duration: int = 5000,
                  notification_type: NotificationType = NotificationType.INFO,
                  actions: Optional[list] = None):
        """Mostra notificação toast"""
        self.toast.show_notification(message, title, duration, notification_type, actions)

    def update_bubble_position(self, position: QPoint):
        """Atualiza posição do balão"""
        if self.speech_bubble.isVisible():
            x = position.x() - self.speech_bubble.width() // 2 + 75
            y = position.y() - self.speech_bubble.height() - 15
            self.speech_bubble.move(x, y)

    def hide_all(self):
        """Esconde todas as notificações"""
        self.speech_bubble.hide()
        self.toast.hide()
