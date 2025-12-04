# zfish_gui.py - minimal working GUI for controlling Arduino and recording experiments
import sys, time, json, threading
from datetime import datetime
from pathlib import Path
from PyQt6 import QtWidgets, QtCore
try:
    import serial, serial.tools.list_ports
except:
    serial = None
try:
    import cv2
except:
    cv2 = None
try:
    from pypylon import pylon
    PYPYLON_AVAILABLE = True
except:
    PYPYLON_AVAILABLE = False

APP_DIR = Path.cwd() / "experiments"
APP_DIR.mkdir(exist_ok=True)

class SerialThread(QtCore.QThread):
    line_received = QtCore.pyqtSignal(str)
    def __init__(self, ser):
        super().__init__()
        self.ser = ser; self._running = True
    def run(self):
        while self._running:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8',errors='ignore').strip()
                    if line: self.line_received.emit(line)
                else: time.sleep(0.05)
            except Exception as e:
                self.line_received.emit(f"[SERIAL ERR] {e}"); time.sleep(0.5)
    def stop(self):
        self._running = False; self.wait(1000)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("ZFish Control"); self.resize(900,600)
        self.ser=None; self.simulate=False; self.camera_running=False; self._build_ui()
    def _build_ui(self):
        w=QtWidgets.QWidget(); self.setCentralWidget(w); lay=QtWidgets.QVBoxLayout(w)
        conn_group=QtWidgets.QGroupBox("Connection"); c_l=QtWidgets.QHBoxLayout(conn_group)
        self.port_combo=QtWidgets.QComboBox(); self.refresh_btn=QtWidgets.QPushButton("Refresh"); self.connect_btn=QtWidgets.QPushButton("Connect"); self.status_label=QtWidgets.QLabel("Not connected")
        c_l.addWidget(self.port_combo); c_l.addWidget(self.refresh_btn); c_l.addWidget(self.connect_btn); c_l.addWidget(self.status_label)
        lay.addWidget(conn_group); self.refresh_btn.clicked.connect(self.refresh_ports); self.connect_btn.clicked.connect(self.toggle_connect)
        exp_group=QtWidgets.QGroupBox("Experiment Control"); exp_l=QtWidgets.QGridLayout(exp_group)
        exp_l.addWidget(QtWidgets.QLabel("Duration (s):"),0,0); self.duration_spin=QtWidgets.QSpinBox(); self.duration_spin.setRange(1,36000); self.duration_spin.setValue(60); exp_l.addWidget(self.duration_spin,0,1)
        self.chk_ir=QtWidgets.QCheckBox("IR"); self.chk_white=QtWidgets.QCheckBox("White"); self.chk_pump=QtWidgets.QCheckBox("Pump"); self.chk_vib=QtWidgets.QCheckBox("Vib"); self.chk_heater=QtWidgets.QCheckBox("Heater")
        cbx=QtWidgets.QHBoxLayout(); cbx.addWidget(self.chk_ir); cbx.addWidget(self.chk_white); cbx.addWidget(self.chk_pump); cbx.addWidget(self.chk_vib); cbx.addWidget(self.chk_heater)
        exp_l.addLayout(cbx,1,1); exp_l.addWidget(QtWidgets.QLabel("ON (ms):"),2,0); self.on_spin=QtWidgets.QSpinBox(); self.on_spin.setRange(10,600000); self.on_spin.setValue(1000); exp_l.addWidget(self.on_spin,2,1)
        exp_l.addWidget(QtWidgets.QLabel("OFF (ms):"),2,2); self.off_spin=QtWidgets.QSpinBox(); self.off_spin.setRange(10,600000); self.off_spin.setValue(1000); exp_l.addWidget(self.off_spin,2,3)
        exp_l.addWidget(QtWidgets.QLabel("IR PWM (0-255):"),3,0); self.ir_pwm=QtWidgets.QSpinBox(); self.ir_pwm.setRange(0,255); self.ir_pwm.setValue(200); exp_l.addWidget(self.ir_pwm,3,1)
        exp_l.addWidget(QtWidgets.QLabel("Pump PWM (0-255):"),3,2); self.pump_pwm=QtWidgets.QSpinBox(); self.pump_pwm.setRange(0,255); self.pump_pwm.setValue(200); exp_l.addWidget(self.pump_pwm,3,3)
        exp_l.addWidget(QtWidgets.QLabel("Vib PWM (0-255):"),4,0); self.vib_pwm=QtWidgets.QSpinBox(); self.vib_pwm.setRange(0,255); self.vib_pwm.setValue(128); exp_l.addWidget(self.vib_pwm,4,1)
        self.start_btn=QtWidgets.QPushButton("Start Experiment"); self.stop_btn=QtWidgets.QPushButton("Stop Experiment"); exp_l.addWidget(self.start_btn,5,0); exp_l.addWidget(self.stop_btn,5,1)
        self.start_btn.clicked.connect(self.start_experiment); self.stop_btn.clicked.connect(self.stop_experiment)
        lay.addWidget(exp_group)
        self.log=QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); lay.addWidget(self.log,stretch=1)
    def refresh_ports(self):
        self.port_combo.clear()
        if serial is None:
            self.port_combo.addItem("pyserial not installed"); return
        ports=serial.tools.list_ports.comports()
        for p in ports: self.port_combo.addItem(f"{p.device} - {p.description}", p.device)
    def toggle_connect(self):
        if self.ser is None:
            if serial is None:
                self.log_msg("pyserial not installed - running in simulate mode"); self.simulate=True; self.status_label.setText("SIMULATE"); return
            port_data=self.port_combo.currentData()
            if port_data is None: self.log_msg("No port selected"); return
            try:
                self.ser=serial.Serial(port_data,115200,timeout=0.1); time.sleep(0.2)
                self.serial_thread=SerialThread(self.ser); self.serial_thread.line_received.connect(self.on_serial_line); self.serial_thread.start()
                self.status_label.setText(f"Connected {port_data}"); self.log_msg("Serial connected")
            except Exception as e:
                self.log_msg(f"Serial connect error: {e}"); self.ser=None
        else:
            if hasattr(self,'serial_thread') and self.serial_thread: self.serial_thread.stop(); self.serial_thread=None
            try: self.ser.close()
            except: pass
            self.ser=None; self.status_label.setText("Not connected"); self.log_msg("Serial disconnected")
    def send_serial(self,line):
        if self.simulate:
            self.log_msg(f"[SIM] TX: {line}")
            if line.startswith("START"): self.log_msg("[SIM] EXPERIMENT_STARTED")
            return
        if not self.ser: self.log_msg("Not connected to Arduino"); return
        try:
            self.ser.write((line+"\n").encode('utf-8')); self.log_msg(f"TX: {line}")
        except Exception as e: self.log_msg(f"Serial send error: {e}")
    def on_serial_line(self,line):
        self.log_msg("RX: "+line)
    def start_experiment(self):
        targets=[]
        if self.chk_ir.isChecked(): targets.append("IR")
        if self.chk_white.isChecked(): targets.append("WHITE")
        if self.chk_pump.isChecked(): targets.append("PUMP")
        if self.chk_vib.isChecked(): targets.append("VIB")
        if self.chk_heater.isChecked(): targets.append("HEATER")
        if not targets: self.log_msg("Choose at least one stimulus"); return
        target_str="+".join(targets)
        onms=self.on_spin.value(); offms=self.off_spin.value(); irv=self.ir_pwm.value(); pumpv=self.pump_pwm.value(); vibv=self.vib_pwm.value()
        pattern_cmd=f"SET PATTERN {target_str} {onms} {offms} {irv} {pumpv} {vibv}"; self.send_serial(pattern_cmd)
        dur=int(self.duration_spin.value()*1000); start_cmd=f"START {dur}"; self.send_serial(start_cmd)
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S"); folder=APP_DIR/f"experiment_{stamp}"; folder.mkdir(parents=True,exist_ok=True)
        cfg={"timestamp":stamp,"targets":targets,"onms":onms,"offms":offms,"ir":irv,"pump":pumpv,"vib":vibv,"duration_s":self.duration_spin.value()}
        with open(folder/"config.json","w") as f: json.dump(cfg,f,indent=2)
        self.log_msg(f"Experiment started, folder: {folder}")
    def stop_experiment(self): self.send_serial("STOP"); self.log_msg("Stop command sent")
    def send_manual(self,text): self.send_serial("MANUAL "+text)
    def log_msg(self,s): ts=datetime.now().strftime("%H:%M:%S"); self.log.appendPlainText(f"[{ts}] {s}"); self.log.ensureCursorVisible()
def main():
    app=QtWidgets.QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec())
if __name__=="__main__": main()
