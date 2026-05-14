"""DeepFace 独立服务：提供轻量的人脸情绪识别 API，供主应用远程调用。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from deepface import DeepFace
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png"}
EMOTION_CN_MAP = {
    "happy": "开心",
    "sad": "难过",
    "angry": "生气",
    "neutral": "平静",
    "fear": "紧张",
    "disgust": "厌恶",
    "surprise": "惊讶",
}


def _normalize_result(raw_result):
    if isinstance(raw_result, list):
        if not raw_result:
            raise ValueError("DeepFace 返回空结果")
        raw_result = raw_result[0]

    if not isinstance(raw_result, dict):
        raise TypeError("DeepFace 返回结构异常")

    emotions = raw_result.get("emotion", {})
    if not isinstance(emotions, dict) or not emotions:
        raise ValueError("DeepFace 缺少 emotion 字段")

    top_emotion = max(emotions, key=lambda key: float(emotions.get(key, 0) or 0))
    top_score = float(emotions.get(top_emotion, 0) or 0)

    emotion = str(top_emotion).lower().strip()
    if emotion not in EMOTION_CN_MAP:
        emotion = "neutral"
        top_score = 50.0

    confidence = max(0.0, min(1.0, top_score / 100.0))
    return {
        "emotion": emotion,
        "emotion_cn": EMOTION_CN_MAP[emotion],
        "confidence": confidence,
    }


@app.get("/")
def index():
    return jsonify(
        {
            "status": "ok",
            "service": "xinqing-deepface",
            "message": "DeepFace service is running",
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/analyze_face")
def analyze_face():
    file = request.files.get("file")
    if file is None or not str(file.filename or "").strip():
        return jsonify({"success": False, "message": "请上传图片文件"}), 400

    suffix = Path(str(file.filename)).suffix.lower()
    if suffix not in ALLOWED_SUFFIX:
        return jsonify({"success": False, "message": "仅支持 jpg、jpeg、png"}), 400

    temp_path = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix="deepface_", suffix=suffix)
        os.close(fd)
        temp_path = Path(temp_name)
        file.save(temp_path)

        raw_result = DeepFace.analyze(
            img_path=str(temp_path),
            actions=["emotion"],
            enforce_detection=False,
        )
        normalized = _normalize_result(raw_result)

        return jsonify(
            {
                "success": True,
                "emotion": normalized["emotion"],
                "emotion_cn": normalized["emotion_cn"],
                "confidence": normalized["confidence"],
                "source": "deepface_remote",
            }
        )
    except Exception as error:
        app.logger.warning("deepface analyze failed: %s", error)
        return jsonify({"success": False, "message": "未识别到清晰人脸"}), 200
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
