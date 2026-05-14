"""功能模块：封装具体业务能力，供路由层调用。"""

import threading
import time

import cv2
import numpy as np

class CameraService:
    def __init__(self):
        self._lock = threading.Lock()
        self.status = {
            "camera_ready": False,
            "mode": "摄像头预览模式",
            "fatigue_status": "待启用",
            "risk_level": "未评估",
            "suggestion": "当前版本先完成摄像头接入，疲劳检测后续将基于眼睛开合程度 EAR 实现。",
            "warning": "",
        }

    def _set_status(self, **kwargs):
        with self._lock:
            self.status.update(kwargs)

    def get_status(self):
        with self._lock:
            return dict(self.status)

    def _encode_frame(self, frame):
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        return (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

    def _error_frame(self, text):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (0, 0), (639, 479), (32, 32, 32), 2)
        cv2.putText(
            frame,
            text[:60],
            (20, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 200, 255),
            2,
        )
        cv2.putText(
            frame,
            "Please check camera permission/settings.",
            (20, 260),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
        )
        return frame

    def generate_frames(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._set_status(
                camera_ready=False,
                warning="摄像头打开失败，请检查浏览器/系统权限或摄像头编号。",
                mode="摄像头预览模式",
                fatigue_status="待启用",
                risk_level="未评估",
            )
            while True:
                frame = self._error_frame("Camera open failed")
                encoded = self._encode_frame(frame)
                if encoded:
                    yield encoded
                time.sleep(0.15)

        try:
            self._set_status(
                camera_ready=True,
                warning="",
                mode="摄像头预览模式",
                fatigue_status="待启用",
                risk_level="未评估",
                suggestion="当前版本先完成摄像头接入，疲劳检测后续将基于眼睛开合程度 EAR 实现。",
            )
            while True:
                ok, frame = cap.read()
                if not ok:
                    self._set_status(
                        warning="摄像头打开失败，请检查浏览器/系统权限或摄像头编号。",
                        camera_ready=False,
                    )
                    frame = self._error_frame("Camera read failed")
                    encoded = self._encode_frame(frame)
                    if encoded:
                        yield encoded
                    time.sleep(0.1)
                    continue

                frame = cv2.flip(frame, 1)
                cv2.putText(
                    frame,
                    "Camera Preview Mode",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (36, 255, 12),
                    2,
                )
                cv2.putText(
                    frame,
                    "Fatigue detection will be enabled later.",
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.58,
                    (255, 255, 255),
                    1,
                )

                encoded = self._encode_frame(frame)
                if encoded:
                    yield encoded
        finally:
            cap.release()
            self._set_status(camera_ready=False)


camera_service = CameraService()
