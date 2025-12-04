ZFish MVP project - uploaded via script

Structure:
- arduino/zfish_controller.ino      # Arduino sketch
- gui/zfish_gui.py                  # PyQt6 GUI app (minimal version)
- requirements.txt                  # Python deps (pypylon optional)
- backend/                          # placeholder for future backend modules
- docs/

How to use:
1. Arduino: open arduino/zfish_controller.ino in Arduino IDE and upload to UNO/Nano.
   Install OneWire and DallasTemperature libraries via Library Manager.

2. GUI:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python .\gui\zfish_gui.py

3. When hardware arrives, wire MOSFETs/relays per wiring guide in docs/
