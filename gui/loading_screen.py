# gui/loading_screen.py
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(420, 260)
        self.setStyleSheet("background-color: #121016; border-radius: 14px;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        logo = QLabel("🐟")
        logo.setFont(QFont("Segoe UI Emoji", 40))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("ZIMON")
        title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #8B5CF6;")

        subtitle = QLabel("Behaviour Tracking System")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #AAAAAA;")

        self.status = QLabel("Initializing…")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #CCCCCC;")

        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.status)

        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(450)

    def _animate(self):
        self._dot_count = (self._dot_count + 1) % 4
        self.status.setText("Initializing" + "." * self._dot_count)

    def set_status(self, text: str):
        self.status.setText(text)
