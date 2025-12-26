# camera_interface.py
import logging
import threading
import time
from typing import List

logger = logging.getLogger("CameraController")

class CameraController:
    """
    Minimal camera controller stub.
    Replace with real Basler or OpenCV capture code later.
    """

    def __init__(self):
        # simple placeholder state
        self.cameras = ["top", "side"]  # assume two cameras by default
        self.recording = {}
        self._lock = threading.Lock()

    def list_cameras(self) -> List[str]:
        # In real code query connected devices
        return list(self.cameras)

    def start_recording(self, camera_name: str, filename: str, duration_s: int=None):
        """
        Start recording (non-blocking). For now it just logs and simulates.
        Returns a token/handle that can be used to stop.
        """
        logger.info(f"Start recording camera={camera_name} -> {filename}")
        with self._lock:
            if camera_name in self.recording:
                logger.warning("Camera already recording")
                return None
            stop_flag = {"stop": False}
            self.recording[camera_name] = stop_flag

            def _simulate():
                logger.info(f"[{camera_name}] recording started (simulated)")
                t0 = time.time()
                while not stop_flag["stop"]:
                    time.sleep(0.2)
                    if duration_s and (time.time() - t0) > duration_s:
                        break
                logger.info(f"[{camera_name}] recording stopped (simulated)")
                with self._lock:
                    self.recording.pop(camera_name, None)

            threading.Thread(target=_simulate, daemon=True).start()
            return stop_flag

    def stop_recording(self, camera_name: str):
        with self._lock:
            flag = self.recording.get(camera_name)
            if flag:
                flag["stop"] = True
                return True
            return False
