"""功能模块：封装具体业务能力，供路由层调用。"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path


EMOTION_CN_MAP = {
    "angry": "愤怒",
    "disgust": "厌恶",
    "fear": "恐惧",
    "happy": "开心",
    "sad": "悲伤",
    "surprise": "惊讶",
    "neutral": "中性",
}


def _mock_result(warning_message):
    return {
        "emotion": "neutral",
        "emotion_cn": "中性",
        "confidence": 0.50,
        "source": "mock",
        "warning": warning_message,
    }


def _normalize_deepface_result(raw_result):
    if isinstance(raw_result, list):
        if not raw_result:
            raise ValueError("DeepFace 返回空结果列表")
        raw_result = raw_result[0]
    if not isinstance(raw_result, dict):
        raise TypeError(f"DeepFace 返回类型异常: {type(raw_result)}")
    emotions = raw_result.get("emotion", {})
    if not isinstance(emotions, dict) or not emotions:
        raise ValueError("DeepFace 结果中缺少 emotion 概率字典")
    return emotions


def _build_temp_image_path(image_path):
    original_path = Path(image_path)
    suffix = original_path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError(f"不支持的图片格式: {suffix or '无扩展名'}")

    temp_dir = Path(tempfile.gettempdir()) / "emotion_warning_deepface"
    temp_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"input_{stamp}{suffix}"
    return temp_dir / filename


def analyze_image(image_path):
    try:
        from deepface import DeepFace
    except Exception:
        return _mock_result("DeepFace 未安装，已使用兜底结果")

    temp_image_path = None
    try:
        temp_image_path = _build_temp_image_path(image_path)
        shutil.copy2(image_path, temp_image_path)
    except Exception as e:
        return _mock_result(f"临时文件复制失败：{e}")

    try:
        raw_result = DeepFace.analyze(
            img_path=str(temp_image_path),
            actions=["emotion"],
            enforce_detection=False,
        )
        emotions = _normalize_deepface_result(raw_result)

        top_emotion = max(emotions, key=lambda key: float(emotions.get(key, 0)))
        top_score = float(emotions.get(top_emotion, 0))
        top_emotion = str(top_emotion).lower()

        if top_emotion not in EMOTION_CN_MAP:
            top_emotion = "neutral"
            top_score = 50.0

        confidence = max(0.0, min(1.0, top_score / 100.0))
        return {
            "emotion": top_emotion,
            "emotion_cn": EMOTION_CN_MAP[top_emotion],
            "confidence": confidence,
            "source": "deepface",
            "warning": "",
        }
    except Exception as e:
        return _mock_result(f"真实模型识别失败：{e}")
    finally:
        if temp_image_path is not None:
            try:
                Path(temp_image_path).unlink(missing_ok=True)
            except Exception:
                pass
