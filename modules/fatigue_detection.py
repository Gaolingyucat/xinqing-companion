"""功能模块：封装具体业务能力，供路由层调用。"""

import math


LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

EAR_THRESHOLD = 0.21
FATIGUE_FRAMES_THRESHOLD = 20


def _euclidean(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _eye_ear(eye_points):
    p1, p2, p3, p4, p5, p6 = eye_points
    vertical = _euclidean(p2, p6) + _euclidean(p3, p5)
    horizontal = 2.0 * _euclidean(p1, p4)
    if horizontal == 0:
        return 0.0
    return vertical / horizontal


def calculate_ear(landmarks, image_width, image_height):
    left_eye = []
    right_eye = []

    for idx in LEFT_EYE_IDX:
        pt = landmarks[idx]
        left_eye.append((pt.x * image_width, pt.y * image_height))
    for idx in RIGHT_EYE_IDX:
        pt = landmarks[idx]
        right_eye.append((pt.x * image_width, pt.y * image_height))

    left_ear = _eye_ear(left_eye)
    right_ear = _eye_ear(right_eye)
    return (left_ear + right_ear) / 2.0


def detect_fatigue_status(ear, closed_frames):
    if ear < EAR_THRESHOLD:
        eye_state = "闭眼"
        if closed_frames >= FATIGUE_FRAMES_THRESHOLD:
            return {
                "eye_state": eye_state,
                "fatigue_status": "疑似疲劳",
                "risk_level": "高风险",
                "suggestion": "检测到连续闭眼，请暂停当前任务并短暂休息，建议调整坐姿与光线后再继续。",
            }
        return {
            "eye_state": eye_state,
            "fatigue_status": "短暂闭眼",
            "risk_level": "中风险",
            "suggestion": "检测到短暂闭眼，建议眨眼放松并减少连续高强度用眼。",
        }

    return {
        "eye_state": "正常",
        "fatigue_status": "正常",
        "risk_level": "低风险",
        "suggestion": "当前状态正常，建议保持良好坐姿并持续观察。",
    }
