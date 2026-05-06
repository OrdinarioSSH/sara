"""
HUD Waveform Visualizer — SARA
Widget QPainter com espectro de áudio reativo, estilo Jarvis/cybernetic.
"""
import math
import time
import random

from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QRadialGradient,
    QFont, QIcon, QPixmap
)

from hud_config import *


class HUDVisualizer(QWidget):
    """HUD Waveform Visualizer — display audio-reativo para SARA."""

    def __init__(self, pet_ref=None, size=DEFAULT_HUD_SIZE):
        super().__init__(None)
        self._pet = pet_ref
        self._size = size

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(size, size)

        # Estado de animação
        self._state = "idle"
        self._tick = 0
        self._breath_phase = 0.0
        self._bar_values = [0.0] * NUM_BARS
        self._bar_targets = [0.0] * NUM_BARS
        self._glow_intensity = BREATH_MIN

        # Áudio
        self._extractor = None
        self._playback_start = 0.0

        # Drag
        self._drag_pos = None

        # Timer de animação
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(FRAME_INTERVAL_MS)

    # === API pública ===

    def set_state(self, state: str):
        """Muda o estado: idle, listening, processing, speaking."""
        if state != self._state:
            self._state = state
            if state == "speaking" and self._extractor:
                self._playback_start = time.time()

    def set_speaking(self, extractor):
        """Inicia modo speaking com dados de áudio reais."""
        self._extractor = extractor
        self._playback_start = time.time()
        self._state = "speaking"

    def set_idle(self):
        """Volta ao modo idle."""
        self._state = "idle"
        self._extractor = None

    # === Tick (30fps) ===

    def _on_tick(self):
        self._tick += 1

        if self._state == "idle":
            self._breath_phase += BREATH_SPEED
            self._glow_intensity = BREATH_MIN + (BREATH_MAX - BREATH_MIN) * 0.5 * (1 + math.sin(self._breath_phase))
            for i in range(NUM_BARS):
                self._bar_targets[i] = IDLE_BAR_MIN + random.random() * (IDLE_BAR_MAX - IDLE_BAR_MIN)

        elif self._state == "listening":
            self._glow_intensity = 0.5 + 0.2 * math.sin(self._tick * 0.15)
            for i in range(NUM_BARS):
                wave = 0.5 * (1 + math.sin(self._tick * 0.1 + i * 0.4))
                self._bar_targets[i] = LISTEN_BAR_MIN + wave * (LISTEN_BAR_MAX - LISTEN_BAR_MIN)

        elif self._state == "processing":
            self._glow_intensity = 0.4
            wave_pos = (self._tick % 40) / 40.0
            for i in range(NUM_BARS):
                dist = abs((i / NUM_BARS) - wave_pos)
                self._bar_targets[i] = max(0.05, 0.6 * math.exp(-dist * 8))

        elif self._state == "speaking":
            self._glow_intensity = 0.7 + 0.15 * math.sin(self._tick * 0.2)
            if self._extractor:
                elapsed = time.time() - self._playback_start
                frame_data = self._extractor.get_frame(elapsed)
                for i in range(min(NUM_BARS, len(frame_data))):
                    self._bar_targets[i] = frame_data[i]
            else:
                for i in range(NUM_BARS):
                    self._bar_targets[i] = 0.2 + random.random() * 0.5

        # Lerp suave
        for i in range(NUM_BARS):
            self._bar_values[i] += (self._bar_targets[i] - self._bar_values[i]) * (1.0 - BAR_SMOOTHING)

        self.update()

    # === Renderização ===

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        self._draw_outer_glow(p)
        self._draw_hud_frame(p)
        self._draw_ring_segments(p)
        self._draw_spectrum_bars(p)
        self._draw_center_orb(p)
        self._draw_labels(p)

        p.end()

    def _draw_outer_glow(self, p: QPainter):
        cx, cy = self._size / 2, self._size / 2
        r = self._size / 2
        grad = QRadialGradient(QPointF(cx, cy), r)
        a = int(40 * self._glow_intensity)
        grad.setColorAt(0.0, QColor(0, 255, 255, a))
        grad.setColorAt(0.5, QColor(0, 180, 255, a // 2))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_hud_frame(self, p: QPainter):
        m = CORNER_MARGIN
        bl = BRACKET_LENGTH
        s = self._size
        rect = QRectF(m, m, s - 2 * m, s - 2 * m)

        pen = QPen(QColor(0, 255, 255, 120))
        pen.setWidth(2)
        p.setPen(pen)

        # Cantoneiras
        corners = [
            (rect.left(), rect.top(), bl, 0, 0, bl),
            (rect.right(), rect.top(), -bl, 0, 0, bl),
            (rect.left(), rect.bottom(), bl, 0, 0, -bl),
            (rect.right(), rect.bottom(), -bl, 0, 0, -bl),
        ]
        for x, y, dx1, dy1, dx2, dy2 in corners:
            p.drawLine(QPointF(x, y), QPointF(x + dx1, y + dy1))
            p.drawLine(QPointF(x, y), QPointF(x + dx2, y + dy2))

        # Círculo externo fino
        pen2 = QPen(QColor(0, 200, 255, 60))
        pen2.setWidth(1)
        p.setPen(pen2)
        cr = (s / 2) - 12
        p.drawEllipse(QPointF(s / 2, s / 2), cr, cr)

    def _draw_ring_segments(self, p: QPainter):
        cx, cy = self._size / 2, self._size / 2 + CENTER_OFFSET_Y
        rr = RING_RADIUS
        rotation = (self._tick * RING_ROTATION_SPEED) % 360

        pen = QPen(QColor(0, 200, 255, 50))
        pen.setWidth(1)
        p.setPen(pen)

        rect = QRectF(cx - rr, cy - rr, rr * 2, rr * 2)
        for seg in range(4):
            start_angle = rotation + seg * 90
            p.drawArc(rect, int(start_angle * 16), int(30 * 16))

    def _draw_spectrum_bars(self, p: QPainter):
        cx = self._size / 2
        cy = self._size / 2 + CENTER_OFFSET_Y
        ir = BAR_INNER_RADIUS
        mh = BAR_MAX_HEIGHT
        arc_start = -BAR_ARC_DEGREES / 2
        arc_span = BAR_ARC_DEGREES

        for i in range(NUM_BARS):
            t = i / (NUM_BARS - 1) if NUM_BARS > 1 else 0.5
            angle_deg = arc_start + t * arc_span
            angle_rad = math.radians(angle_deg - 90)

            bh = max(2, self._bar_values[i] * mh)
            x1 = cx + ir * math.cos(angle_rad)
            y1 = cy + ir * math.sin(angle_rad)
            x2 = cx + (ir + bh) * math.cos(angle_rad)
            y2 = cy + (ir + bh) * math.sin(angle_rad)

            intensity = self._bar_values[i]
            r = int(0 + intensity * 50)
            g = int(180 + intensity * 75)
            b = 255
            a = int(150 + intensity * 105)

            pen = QPen(QColor(r, g, b, a))
            pen.setWidth(BAR_WIDTH)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_center_orb(self, p: QPainter):
        cx = self._size / 2
        cy = self._size / 2 + CENTER_OFFSET_Y
        avg = sum(self._bar_values) / NUM_BARS if NUM_BARS > 0 else 0
        orb_r = ORB_BASE_RADIUS + avg * ORB_AMPLITUDE_SCALE

        grad = QRadialGradient(QPointF(cx, cy), orb_r)

        if self._state == "speaking":
            grad.setColorAt(0.0, QColor(0, 255, 255, 200))
            grad.setColorAt(0.5, QColor(0, 180, 255, 100))
            grad.setColorAt(1.0, QColor(0, 100, 200, 0))
        elif self._state == "listening":
            grad.setColorAt(0.0, QColor(50, 255, 150, 180))
            grad.setColorAt(0.5, QColor(0, 200, 100, 80))
            grad.setColorAt(1.0, QColor(0, 100, 50, 0))
        elif self._state == "processing":
            grad.setColorAt(0.0, QColor(255, 200, 0, 180))
            grad.setColorAt(0.5, QColor(200, 150, 0, 80))
            grad.setColorAt(1.0, QColor(100, 80, 0, 0))
        else:
            gi = self._glow_intensity
            grad.setColorAt(0.0, QColor(0, 200, 255, int(80 + 40 * gi)))
            grad.setColorAt(0.5, QColor(0, 120, 200, int(30 + 20 * gi)))
            grad.setColorAt(1.0, QColor(0, 50, 100, 0))

        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), orb_r, orb_r)

    def _draw_labels(self, p: QPainter):
        s = self._size

        # "S A R A" no topo
        font = QFont("Consolas", 10, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(0, 255, 255, 200))
        p.drawText(QRectF(0, 8, s, 20),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   "S A R A")

        # Status na parte inferior
        font_sm = QFont("Consolas", 7)
        p.setFont(font_sm)

        status_map = {
            "idle": ("STANDBY", QColor(100, 200, 255, 150)),
            "listening": ("LISTENING", QColor(50, 255, 150, 200)),
            "speaking": ("SPEAKING", QColor(0, 255, 255, 230)),
            "processing": ("PROCESSING", QColor(255, 200, 0, 200)),
        }
        text, color = status_map.get(self._state, ("STANDBY", QColor(150, 150, 150, 150)))
        p.setPen(color)
        p.drawText(QRectF(0, s - 22, s, 16),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                   text)

    # === Drag ===

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            # Atualiza speech bubble se o pet tiver uma
            if self._pet and hasattr(self._pet, 'speech_bubble'):
                self._pet.speech_bubble.show_message(
                    self._pet.speech_bubble.label.text(),
                    0, new_pos
                ) if self._pet.speech_bubble.isVisible() else None
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if self._pet and hasattr(self._pet, 'open_chat'):
            self._pet.open_chat()

    # === Context Menu ===

    def contextMenuEvent(self, event):
        if self._pet:
            self._pet.last_interaction_time = time.time()
            self._pet._show_context_menu_at(event.globalPos())
