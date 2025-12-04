# (same code as before shortened here for clarity)
from PyQt6 import QtWidgets, QtCore
import time, threading
from pathlib import Path

try:
    import serial, serial.tools.list_ports
except:
    serial = None

from tabs.camera_tab import CameraTab
from tabs.stimuli_tab import StimuliTab
from tabs.experiment_tab import ExperimentTab
from tabs.settings_tab import SettingsTab

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZFish Control â€” Multi")
        self.resize(1100, 720)
        self.ser = None
        self.serial_thread = None
        self.simulate = False
        self._build_ui()

    def log(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {text}")

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 3)

        right = QtWidgets.QVBoxLayout()
        layout.addLayout(right, 1)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        right.addWidget(QtWidgets.QLabel("System Log"))
        right.addWidget(self.log_view)

        self.tabs.addTab(CameraTab(self), "Camera")
        self.tabs.addTab(StimuliTab(self), "Stimuli")
        self.tabs.addTab(ExperimentTab(self), "Experiment")
        self.tabs.addTab(SettingsTab(self), "Settings")

        self.log("UI Ready")
