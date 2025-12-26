from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTabWidget, QGroupBox, QPushButton,
    QCheckBox, QSlider, QSpinBox, QColorDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import logging
import time
from gui.settings_dialog import SettingsDialog
from gui.analysis_tab import AnalysisTab


class MainWindow(QMainWindow):
    def __init__(self, runner=None, arduino=None, camera=None):
        super().__init__()
        self.runner = runner
        self.arduino = arduino
        self.camera = camera
        self.logger = logging.getLogger("main_window")
        
        # Initialize ZebraZoom integration
        try:
            from backend.zebrazoom_integration import ZebraZoomIntegration
            self.zebrazoom = ZebraZoomIntegration()
        except Exception as e:
            self.logger.warning(f"ZebraZoom integration not available: {e}")
            self.zebrazoom = None

        # Widget references for backend integration
        self.ir_slider = None
        self.ir_enable = None
        self.white_slider = None
        self.white_enable = None
        self.pump_slider = None
        self.pump_enable = None
        self.temp_label = None
        self.arduino_status_label = None
        
        self.vib_slider = None
        self.vib_enable = None
        self.vib_duration = None
        self.vib_delay = None
        self.vib_continuous = None
        self.buzzer_slider = None
        self.buzzer_enable = None
        self.buzzer_duration = None
        self.buzzer_delay = None
        self.buzzer_continuous = None
        self.heater_slider = None
        self.heater_enable = None
        self.heater_duration = None
        self.heater_delay = None
        self.heater_continuous = None
        
        # Temperature update timer
        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self._update_temperature)
        self.temp_timer.start(2000)  # Update every 2 seconds
        
        # Experiment timer
        self.experiment_timer = None
        self.experiment_start_time = None

        self.setWindowTitle("ZIMON — Behaviour Tracking System")
        self.resize(1400, 850)
        self._build_ui()
        self._connect_backend()

    # ---------- UI ROOT ----------
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addLayout(self._build_header())
        root.addWidget(self._build_tabs(), 1)

        self.setCentralWidget(central)

    # ---------- HEADER ----------
    def _build_header(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 4)

        title = QLabel("ZIMON")
        title.setObjectName("Title")

        subtitle = QLabel("Behaviour Tracking System")
        subtitle.setObjectName("Subtitle")

        left = QVBoxLayout()
        left.setSpacing(2)
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(title)
        left.addWidget(subtitle)

        layout.addLayout(left)
        layout.addStretch()
        
        # Arduino connection status
        status_label = QLabel("Arduino: Checking...")
        status_label.setObjectName("ArduinoStatus")
        status_label.setStyleSheet("color: #9aa0aa; font-size: 11px; padding: 4px 8px;")
        self.arduino_status_label = status_label
        layout.addWidget(status_label)
        
        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("SettingsButton")
        settings_btn.setStyleSheet("""
            QPushButton#SettingsButton {
                background: transparent;
                border: 1px solid #2b2f3a;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 18px;
                color: #b8bcc8;
                min-width: 36px;
                max-width: 36px;
            }
            QPushButton#SettingsButton:hover {
                background: #252830;
                border-color: #7c5cff;
                color: #ffffff;
            }
            QPushButton#SettingsButton:pressed {
                background: #1d1f26;
            }
        """)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(settings_btn)

        return layout

    # ---------- TABS ----------
    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(self._environment_tab(), "Environment")
        self.tabs.addTab(self._experiment_tab(), "Experiment")
        self.tabs.addTab(self._placeholder_tab("Presets"), "Presets")
        
        # Analysis tab with ZebraZoom integration
        self.analysis_tab = AnalysisTab(self.zebrazoom)
        self.tabs.addTab(self.analysis_tab, "Analysis")
        
        return self.tabs

    # ---------- ENVIRONMENT TAB ----------
    def _environment_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)

        # Top row: Camera preview (smaller) and settings side by side
        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(self._camera_preview_box(), 1)  # Reduced from 2 to 1
        top.addWidget(self._camera_settings_box(), 1)

        layout.addLayout(top)
        layout.addWidget(self._environment_controls(), 0)

        return page

    # ---------- EXPERIMENT TAB ----------
    def _experiment_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)

        # Top section: Camera and experiment status side by side
        top_section = QHBoxLayout()
        top_section.setSpacing(14)
        top_section.addWidget(self._camera_preview_box(), 1)
        top_section.addWidget(self._experiment_status_box(), 1)

        layout.addLayout(top_section)
        layout.addWidget(self._stimuli_controls(), 0)

        # Action buttons with experiment info
        actions_container = QGroupBox("Experiment Control")
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setContentsMargins(16, 20, 16, 16)
        actions_layout.setSpacing(12)

        # Experiment timer/info
        timer_layout = QHBoxLayout()
        timer_layout.setSpacing(10)
        self.experiment_timer_label = QLabel("Duration: 00:00")
        self.experiment_timer_label.setStyleSheet("color: #9aa0aa; font-size: 13px;")
        timer_layout.addWidget(self.experiment_timer_label)
        timer_layout.addStretch()
        actions_layout.addLayout(timer_layout)

        # Buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()
        start_btn = QPushButton("▶ Start Experiment")
        start_btn.setMinimumWidth(160)
        start_btn.clicked.connect(self._on_start_experiment)
        actions.addWidget(start_btn)
        stop = QPushButton("⏹ Stop")
        stop.setObjectName("Danger")
        stop.setMinimumWidth(100)
        stop.clicked.connect(self._on_stop_experiment)
        stop.setEnabled(False)
        actions.addWidget(stop)
        
        # Store button references
        self.start_btn = start_btn
        self.stop_btn = stop

        actions_layout.addLayout(actions)
        layout.addWidget(actions_container)

        return page

    # ---------- CAMERA ----------
    def _camera_preview_box(self):
        box = QGroupBox("Camera Preview")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(8)

        preview = QLabel("Camera feed placeholder")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setObjectName("CameraPlaceholder")
        preview.setMinimumHeight(200)  # Reduced from 300 to 200
        preview.setMaximumHeight(250)  # Add max height for better proportions

        layout.addWidget(preview, 1)
        return box

    def _camera_settings_box(self):
        box = QGroupBox("Camera Settings")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(10)

        # Camera status indicator
        status_layout = QHBoxLayout()
        status_indicator = QLabel("●")
        status_indicator.setStyleSheet("color: #4fc3f7; font-size: 12px;")
        status_text = QLabel("Ready")
        status_text.setStyleSheet("color: #b8bcc8; font-weight: 500;")
        status_layout.addWidget(status_indicator)
        status_layout.addWidget(status_text)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Separator
        separator = QLabel("")
        separator.setStyleSheet("background: #2b2f3a; min-height: 1px; max-height: 1px;")
        layout.addWidget(separator)

        # Camera parameters
        fps_label = QLabel("FPS: —")
        exposure_label = QLabel("Exposure: —")
        gain_label = QLabel("Gain: —")
        resolution_label = QLabel("Resolution: —")
        
        # Style the labels for better readability
        for label in [fps_label, exposure_label, gain_label, resolution_label]:
            label.setStyleSheet("padding: 6px 0px; color: #e6e6e6;")
        
        layout.addWidget(fps_label)
        layout.addWidget(exposure_label)
        layout.addWidget(gain_label)
        layout.addWidget(resolution_label)
        layout.addStretch()

        return box
    
    def _experiment_status_box(self):
        """Create experiment status/info panel"""
        box = QGroupBox("Experiment Status")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(12)

        # Status indicator
        status_layout = QHBoxLayout()
        self.experiment_status_indicator = QLabel("●")
        self.experiment_status_indicator.setStyleSheet("color: #9aa0aa; font-size: 14px;")
        self.experiment_status_text = QLabel("Not Running")
        self.experiment_status_text.setStyleSheet("color: #b8bcc8; font-weight: 600; font-size: 13px;")
        status_layout.addWidget(self.experiment_status_indicator)
        status_layout.addWidget(self.experiment_status_text)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Separator
        separator = QLabel("")
        separator.setStyleSheet("background: #2b2f3a; min-height: 1px; max-height: 1px;")
        layout.addWidget(separator)

        # Active stimuli
        stimuli_label = QLabel("Active Stimuli:")
        stimuli_label.setStyleSheet("color: #9aa0aa; font-size: 12px; padding-top: 4px;")
        layout.addWidget(stimuli_label)
        
        self.active_stimuli_list = QLabel("None")
        self.active_stimuli_list.setStyleSheet("color: #e6e6e6; font-size: 11px; padding-left: 8px;")
        self.active_stimuli_list.setWordWrap(True)
        layout.addWidget(self.active_stimuli_list)

        # Recording status
        recording_layout = QHBoxLayout()
        recording_label = QLabel("Recording:")
        recording_label.setStyleSheet("color: #9aa0aa; font-size: 12px;")
        self.recording_status = QLabel("● Not Recording")
        self.recording_status.setStyleSheet("color: #d04f4f; font-size: 11px;")
        recording_layout.addWidget(recording_label)
        recording_layout.addWidget(self.recording_status)
        recording_layout.addStretch()
        layout.addLayout(recording_layout)

        layout.addStretch()

        return box

    # ---------- ENVIRONMENT CONTROLS ----------
    def _environment_controls(self):
        box = QGroupBox("Environment Variables")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(14)

        # Add a quick info header
        info_header = QLabel("Control environmental conditions for consistent experiments")
        info_header.setStyleSheet("color: #9aa0aa; font-size: 11px; padding-bottom: 4px;")
        layout.addWidget(info_header)

        layout.addLayout(self._slider_row("IR Light"))
        layout.addLayout(self._slider_row("White Light"))
        layout.addLayout(self._slider_row("Pump"))

        # Separator before temperature
        separator = QLabel("")
        separator.setStyleSheet("background: #2b2f3a; min-height: 1px; max-height: 1px; margin: 8px 0;")
        layout.addWidget(separator)

        # Temperature display with icon-like styling
        temp_container = QHBoxLayout()
        temp_container.setContentsMargins(0, 4, 0, 0)
        temp_icon = QLabel("🌡")
        temp_icon.setStyleSheet("font-size: 16px; padding-right: 4px;")
        temp = QLabel("Temperature:")
        temp.setStyleSheet("color: #b8bcc8; font-weight: 500;")
        temp_value = QLabel("-- °C")
        temp_value.setObjectName("Temperature")
        temp_container.addWidget(temp_icon)
        temp_container.addWidget(temp)
        temp_container.addWidget(temp_value)
        temp_container.addStretch()
        layout.addLayout(temp_container)
        
        # Store temperature label reference
        self.temp_label = temp_value

        return box

    # ---------- STIMULI ----------
    def _stimuli_controls(self):
        box = QGroupBox("Stimuli Control")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(14)

        # Add info header
        info_header = QLabel("Configure stimuli parameters for behavioral experiments")
        info_header.setStyleSheet("color: #9aa0aa; font-size: 11px; padding-bottom: 4px;")
        layout.addWidget(info_header)

        layout.addLayout(self._stimulus_row("Vibration"))
        layout.addLayout(self._stimulus_row("Buzzer"))
        layout.addLayout(self._stimulus_row("Heater"))
        layout.addLayout(self._rgb_row())

        return box

    # ---------- HELPERS ----------
    def _slider_row(self, name):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(name)
        label.setMinimumWidth(80)
        enable = QCheckBox("Enable")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(0)
        slider.setEnabled(False)  # Disabled until enable checkbox is checked

        # Store references based on name
        if name == "IR Light":
            self.ir_slider = slider
            self.ir_enable = enable
        elif name == "White Light":
            self.white_slider = slider
            self.white_enable = enable
        elif name == "Pump":
            self.pump_slider = slider
            self.pump_enable = enable

        # Connect enable checkbox to slider
        enable.toggled.connect(lambda checked, s=slider: s.setEnabled(checked))
        enable.toggled.connect(lambda checked, s=slider, n=name: self._on_enable_toggled(checked, s, n))
        
        # Connect slider to backend
        slider.valueChanged.connect(lambda val, n=name: self._on_slider_changed(val, n))

        row.addWidget(label)
        row.addWidget(enable)
        row.addWidget(slider, 1)

        return row

    def _stimulus_row(self, name):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(name)
        name_label.setMinimumWidth(80)
        row.addWidget(name_label)
        
        enable_cb = QCheckBox("Enable")
        row.addWidget(enable_cb)

        intensity_label = QLabel("Intensity")
        intensity_label.setMinimumWidth(60)
        row.addWidget(intensity_label)
        
        intensity_slider = QSlider(Qt.Orientation.Horizontal)
        intensity_slider.setRange(0, 100)
        intensity_slider.setValue(0)
        intensity_slider.setEnabled(False)
        row.addWidget(intensity_slider, 1)

        duration_label = QLabel("Duration")
        duration_label.setMinimumWidth(60)
        row.addWidget(duration_label)
        
        duration_spin = QSpinBox()
        duration_spin.setRange(0, 9999)
        duration_spin.setSuffix(" ms")
        duration_spin.setValue(0)
        row.addWidget(duration_spin)

        delay_label = QLabel("Delay")
        delay_label.setMinimumWidth(50)
        row.addWidget(delay_label)
        
        delay_spin = QSpinBox()
        delay_spin.setRange(0, 9999)
        delay_spin.setSuffix(" ms")
        delay_spin.setValue(0)
        row.addWidget(delay_spin)

        continuous_cb = QCheckBox("Continuous")
        row.addWidget(continuous_cb)

        # Store references for each stimulus
        if name == "Vibration":
            self.vib_slider = intensity_slider
            self.vib_enable = enable_cb
            self.vib_duration = duration_spin
            self.vib_delay = delay_spin
            self.vib_continuous = continuous_cb
        elif name == "Buzzer":
            self.buzzer_slider = intensity_slider
            self.buzzer_enable = enable_cb
            self.buzzer_duration = duration_spin
            self.buzzer_delay = delay_spin
            self.buzzer_continuous = continuous_cb
        elif name == "Heater":
            self.heater_slider = intensity_slider
            self.heater_enable = enable_cb
            self.heater_duration = duration_spin
            self.heater_delay = delay_spin
            self.heater_continuous = continuous_cb

        # Connect enable checkbox
        enable_cb.toggled.connect(lambda checked, s=intensity_slider: s.setEnabled(checked))
        enable_cb.toggled.connect(lambda checked, s=intensity_slider, n=name: self._on_stimulus_enable_toggled(checked, s, n))
        
        # Connect slider
        intensity_slider.valueChanged.connect(lambda val, n=name: self._on_stimulus_slider_changed(val, n))

        # Connect continuous checkbox to disable/enable duration and delay
        def on_continuous_toggled(checked):
            duration_spin.setEnabled(not checked)
            delay_spin.setEnabled(not checked)
            duration_label.setEnabled(not checked)
            delay_label.setEnabled(not checked)
            if checked:
                duration_spin.setValue(0)
                delay_spin.setValue(0)
        
        continuous_cb.toggled.connect(on_continuous_toggled)
        
        return row

    def _rgb_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)

        rgb_label = QLabel("RGB Light")
        rgb_label.setMinimumWidth(80)
        row.addWidget(rgb_label)
        
        enable_cb = QCheckBox("Enable")
        row.addWidget(enable_cb)

        pick = QPushButton("Pick Color")
        pick.setMinimumWidth(100)
        pick.clicked.connect(lambda: QColorDialog.getColor())
        row.addWidget(pick)

        row.addStretch()
        return row

    def _placeholder_tab(self, name):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        label = QLabel(f"{name} — Coming soon")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #9aa0aa; font-size: 14px;")
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()
        return page

    # ---------- BACKEND INTEGRATION ----------
    def _connect_backend(self):
        """Connect UI controls to backend Arduino controller"""
        if not self.arduino:
            self.logger.warning("Arduino controller not available")
            self._update_arduino_status(False, "Not initialized")
            return
        
        # Check connection status - try a test command first
        # Sometimes is_connected() returns False even when working
        is_actually_connected = False
        
        # First check the obvious way
        if self.arduino.is_connected():
            # If is_connected() says True, trust it (commands are working)
            is_actually_connected = True
        
        if not is_actually_connected:
            # Try to auto-connect if not already connected
            self.logger.info("Attempting to auto-connect Arduino...")
            self._update_arduino_status(False, "Connecting...")
            try:
                if self.arduino.auto_connect():
                    self.logger.info("Arduino auto-connected successfully")
                    # Test connection with a STATUS command
                    try:
                        reply = self.arduino.send("STATUS")
                        self.logger.info(f"Connection test: STATUS -> {reply}")
                        port = getattr(self.arduino, 'port', 'Unknown')
                        self._update_arduino_status(True, f"Connected ({port})")
                    except Exception as e:
                        self.logger.warning(f"Connection test failed: {e}")
                        # Still mark as connected if auto_connect succeeded
                        port = getattr(self.arduino, 'port', 'Unknown')
                        self._update_arduino_status(True, f"Connected ({port})")
                else:
                    self.logger.warning("Arduino auto-connect failed - check if Arduino is connected and firmware is loaded")
                    self._update_arduino_status(False, "Not connected")
            except Exception as e:
                self.logger.error(f"Error during auto-connect: {e}", exc_info=True)
                self._update_arduino_status(False, f"Error: {str(e)[:30]}")
        else:
            self.logger.info("Arduino already connected")
            port = getattr(self.arduino, 'port', 'Unknown')
            self._update_arduino_status(True, f"Connected ({port})")
    
    def _show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.arduino, self, self.zebrazoom)
        dialog.exec()
        # Update status after settings dialog closes
        self._update_connection_status()
        # Update zebrazoom reference if it was changed
        if hasattr(dialog, 'zebrazoom') and dialog.zebrazoom:
            self.zebrazoom = dialog.zebrazoom
            # Update analysis tab if it exists
            self._update_zebrazoom_in_analysis()
    
    def _update_zebrazoom_in_analysis(self):
        """Update ZebraZoom reference in analysis tab"""
        # Update the analysis tab's zebrazoom reference
        if hasattr(self, 'analysis_tab'):
            self.analysis_tab.zebrazoom = self.zebrazoom
            # Remove warning if ZebraZoom is now available
            if self.zebrazoom and self.zebrazoom.is_available():
                # Remove warning label if exists
                layout = self.analysis_tab.layout()
                if layout:
                    for j in range(layout.count()):
                        item = layout.itemAt(j)
                        if item and item.widget():
                            widget_item = item.widget()
                            if isinstance(widget_item, QLabel) and "⚠️" in widget_item.text():
                                widget_item.deleteLater()
    
    def _update_connection_status(self):
        """Update connection status by testing actual connection"""
        if not self.arduino:
            self._update_arduino_status(False, "Not initialized")
            return
            
        # Test if actually connected
        try:
            if self.arduino.is_connected():
                port = getattr(self.arduino, 'port', 'Unknown')
                self._update_arduino_status(True, f"Connected ({port})")
            else:
                # Try to reconnect if we have a port
                port = getattr(self.arduino, 'port', None)
                if port:
                    try:
                        if self.arduino.connect(port):
                            self._update_arduino_status(True, f"Connected ({port})")
                        else:
                            self._update_arduino_status(False, "Not connected")
                    except:
                        self._update_arduino_status(False, "Not connected")
                else:
                    self._update_arduino_status(False, "Not connected")
        except Exception as e:
            self.logger.error(f"Error checking connection: {e}")
            self._update_arduino_status(False, "Error")
    
    def _update_arduino_status(self, connected, message):
        """Update Arduino connection status label"""
        if self.arduino_status_label:
            if connected:
                self.arduino_status_label.setText(f"Arduino: {message}")
                self.arduino_status_label.setStyleSheet("color: #4fc3f7; font-size: 11px; padding: 4px 8px;")
            else:
                self.arduino_status_label.setText(f"Arduino: {message}")
                self.arduino_status_label.setStyleSheet("color: #d04f4f; font-size: 11px; padding: 4px 8px;")

    def _map_to_pwm(self, value_0_100):
        """Map slider value (0-100) to PWM value (0-255)"""
        return int((value_0_100 / 100.0) * 255)

    def _on_enable_toggled(self, checked, slider, name):
        """Handle enable checkbox toggle for environment controls"""
        if not checked:
            # Disable slider and set value to 0
            slider.setValue(0)
            self._send_arduino_command(name, 0)
        else:
            # Send current slider value
            self._send_arduino_command(name, slider.value())

    def _on_slider_changed(self, value, name):
        """Handle slider value change for environment controls"""
        if not self.arduino or not self.arduino.is_connected():
            return
        
        # Check if enabled
        enable_cb = None
        if name == "IR Light":
            enable_cb = self.ir_enable
        elif name == "White Light":
            enable_cb = self.white_enable
        elif name == "Pump":
            enable_cb = self.pump_enable
        
        if enable_cb and enable_cb.isChecked():
            self._send_arduino_command(name, value)

    def _on_stimulus_enable_toggled(self, checked, slider, name):
        """Handle enable checkbox toggle for stimulus controls"""
        if not checked:
            slider.setValue(0)
            self._send_stimulus_command(name, 0)
        else:
            self._send_stimulus_command(name, slider.value())

    def _on_stimulus_slider_changed(self, value, name):
        """Handle slider value change for stimulus controls"""
        if not self.arduino or not self.arduino.is_connected():
            return
        
        enable_cb = None
        if name == "Vibration":
            enable_cb = self.vib_enable
        elif name == "Buzzer":
            enable_cb = self.buzzer_enable
        elif name == "Heater":
            enable_cb = self.heater_enable
        
        if enable_cb and enable_cb.isChecked():
            self._send_stimulus_command(name, value)

    def _send_arduino_command(self, name, value_0_100):
        """Send command to Arduino for environment controls"""
        if not self.arduino:
            self.logger.warning("Arduino controller not available")
            return
            
        if not self.arduino.is_connected():
            self.logger.warning("Arduino not connected - attempting reconnect...")
            try:
                if not self.arduino.auto_connect():
                    self.logger.error("Failed to reconnect Arduino")
                    return
            except Exception as e:
                self.logger.error(f"Reconnect error: {e}")
                return
        
        pwm_value = self._map_to_pwm(value_0_100)
        
        cmd_map = {
            "IR Light": f"IR {pwm_value}",
            "White Light": f"WHITE {pwm_value}",
            "Pump": f"PUMP {pwm_value}"
        }
        
        cmd = cmd_map.get(name)
        if cmd:
            try:
                reply = self.arduino.send(cmd)
                self.logger.info(f"Arduino command: {cmd} -> {reply}")
            except Exception as e:
                self.logger.error(f"Failed to send Arduino command {cmd}: {e}", exc_info=True)

    def _send_stimulus_command(self, name, value_0_100):
        """Send command to Arduino for stimulus controls"""
        if not self.arduino:
            self.logger.warning("Arduino controller not available")
            return
            
        if not self.arduino.is_connected():
            self.logger.warning("Arduino not connected")
            return
        
        pwm_value = self._map_to_pwm(value_0_100)
        
        # Map stimulus names to Arduino commands
        # Note: Buzzer and Heater may not be implemented in Arduino yet
        cmd_map = {
            "Vibration": f"VIB {pwm_value}",
            "Buzzer": None,  # Not implemented in Arduino firmware
            "Heater": None   # Not implemented in Arduino firmware
        }
        
        cmd = cmd_map.get(name)
        if cmd:
            try:
                reply = self.arduino.send(cmd)
                self.logger.info(f"Arduino command: {cmd} -> {reply}")
            except Exception as e:
                self.logger.error(f"Failed to send Arduino command {cmd}: {e}", exc_info=True)
        elif cmd is None:
            self.logger.warning(f"Stimulus '{name}' not implemented in Arduino firmware")

    def _update_temperature(self):
        """Update temperature display from Arduino"""
        if not self.arduino:
            if self.temp_label:
                self.temp_label.setText("-- °C")
            return
            
        # Check connection more reliably
        is_connected = False
        try:
            if self.arduino.is_connected():
                # Try a quick test to see if actually working
                is_connected = True
        except:
            pass
            
        if not is_connected:
            if self.temp_label:
                self.temp_label.setText("-- °C")
            # Only update status if we're sure it's disconnected
            # Don't update on every temp check to avoid flickering
            return
        
        try:
            temp = self.arduino.read_temperature_c()
            if temp is not None:
                if self.temp_label:
                    self.temp_label.setText(f"{temp:.1f} °C")
            else:
                if self.temp_label:
                    self.temp_label.setText("-- °C")
        except Exception as e:
            self.logger.error(f"Failed to read temperature: {e}")
            if self.temp_label:
                self.temp_label.setText("ERR °C")

    def _on_start_experiment(self):
        """Handle start experiment button click"""
        if not self.runner:
            self.logger.warning("Experiment runner not available")
            return
        
        # Build experiment config from UI state
        # Collect active stimuli with their parameters
        stimuli_config = {}
        
        # Vibration
        if hasattr(self, 'vib_enable') and self.vib_enable and self.vib_enable.isChecked():
            intensity = self.vib_slider.value() if self.vib_slider else 0
            continuous = self.vib_continuous.isChecked() if self.vib_continuous else False
            stimuli_config["VIB"] = {
                "level": self._map_to_pwm(intensity),
                "continuous": continuous,
                "duration_ms": 0 if continuous else (self.vib_duration.value() if self.vib_duration else 0),
                "delay_ms": 0 if continuous else (self.vib_delay.value() if self.vib_delay else 0)
            }
        
        # Buzzer
        if hasattr(self, 'buzzer_enable') and self.buzzer_enable and self.buzzer_enable.isChecked():
            intensity = self.buzzer_slider.value() if self.buzzer_slider else 0
            continuous = self.buzzer_continuous.isChecked() if self.buzzer_continuous else False
            stimuli_config["BUZZER"] = {
                "level": self._map_to_pwm(intensity),
                "continuous": continuous,
                "duration_ms": 0 if continuous else (self.buzzer_duration.value() if self.buzzer_duration else 0),
                "delay_ms": 0 if continuous else (self.buzzer_delay.value() if self.buzzer_delay else 0)
            }
        
        # Heater
        if hasattr(self, 'heater_enable') and self.heater_enable and self.heater_enable.isChecked():
            intensity = self.heater_slider.value() if self.heater_slider else 0
            continuous = self.heater_continuous.isChecked() if self.heater_continuous else False
            stimuli_config["HEATER"] = {
                "level": self._map_to_pwm(intensity),
                "continuous": continuous,
                "duration_ms": 0 if continuous else (self.heater_duration.value() if self.heater_duration else 0),
                "delay_ms": 0 if continuous else (self.heater_delay.value() if self.heater_delay else 0)
            }
        
        # Calculate experiment duration (long enough for all stimuli)
        max_duration = 60  # Default 60 seconds
        if stimuli_config:
            # For now, use a reasonable default, could calculate from stimuli
            max_duration = 300  # 5 minutes default
        
        config = {
            "duration_s": max_duration,
            "stimuli": stimuli_config
        }
        
        try:
            if self.runner.start(config):
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                
                # Update status
                if hasattr(self, 'experiment_status_indicator'):
                    self.experiment_status_indicator.setStyleSheet("color: #4fc3f7; font-size: 14px;")
                    self.experiment_status_text.setText("Running")
                
                # Update active stimuli display
                if hasattr(self, 'active_stimuli_list'):
                    active_stimuli_names = list(stimuli_config.keys())
                    if active_stimuli_names:
                        self.active_stimuli_list.setText(", ".join(active_stimuli_names))
                    else:
                        self.active_stimuli_list.setText("None")
                
                # Start timer
                self.experiment_start_time = time.time()
                if not self.experiment_timer:
                    self.experiment_timer = QTimer()
                    self.experiment_timer.timeout.connect(self._update_experiment_timer)
                self.experiment_timer.start(1000)  # Update every second
                
                # Update recording status
                if hasattr(self, 'recording_status'):
                    self.recording_status.setText("● Recording")
                    self.recording_status.setStyleSheet("color: #4fc3f7; font-size: 11px;")
                
                self.logger.info("Experiment started")
            else:
                self.logger.warning("Failed to start experiment (already running?)")
        except Exception as e:
            self.logger.error(f"Error starting experiment: {e}")

    def _on_stop_experiment(self):
        """Handle stop experiment button click"""
        if not self.runner:
            return
        
        try:
            self.runner.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # Update status
            if hasattr(self, 'experiment_status_indicator'):
                self.experiment_status_indicator.setStyleSheet("color: #9aa0aa; font-size: 14px;")
                self.experiment_status_text.setText("Not Running")
            
            # Stop timer
            if self.experiment_timer:
                self.experiment_timer.stop()
            if hasattr(self, 'experiment_timer_label'):
                self.experiment_timer_label.setText("Duration: 00:00")
            self.experiment_start_time = None
            
            # Update recording status
            if hasattr(self, 'recording_status'):
                self.recording_status.setText("● Not Recording")
                self.recording_status.setStyleSheet("color: #d04f4f; font-size: 11px;")
            
            # Clear active stimuli
            if hasattr(self, 'active_stimuli_list'):
                self.active_stimuli_list.setText("None")
            
            self.logger.info("Experiment stopped")
        except Exception as e:
            self.logger.error(f"Error stopping experiment: {e}")
    
    def _update_experiment_timer(self):
        """Update experiment timer display"""
        if self.experiment_start_time and hasattr(self, 'experiment_timer_label'):
            elapsed = time.time() - self.experiment_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.experiment_timer_label.setText(f"Duration: {minutes:02d}:{seconds:02d}")
