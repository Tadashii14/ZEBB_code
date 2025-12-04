from PyQt6 import QtWidgets
import time
from pathlib import Path

class CameraTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = parent
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel("Camera preview will appear here.\n(pypylon not enabled yet)")
        layout.addWidget(self.label)
