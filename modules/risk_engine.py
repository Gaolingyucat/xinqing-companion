"""功能模块：封装具体业务能力，供路由层调用。"""

def _normalize_confidence(confidence):
    value = float(confidence)
    if value <= 1:
        return value * 100
    return value


def get_risk_level(risk_score):
    score = int(round(float(risk_score)))
    if score <= 30:
        return "低风险"
    if score <= 60:
        return "中风险"
    return "高风险"


def evaluate_image_risk(emotion, confidence):
    confidence_pct = _normalize_confidence(confidence)
    emotion_key = str(emotion).lower()

    base_map = {
        "angry": 55,
        "fear": 58,
        "sad": 50,
        "surprise": 42,
        "disgust": 52,
        "neutral": 22,
        "happy": 15,
    }
    base_score = base_map.get(emotion_key, 35)
    confidence_adjust = int(round((confidence_pct - 50) * 0.25))
    risk_score = max(0, min(100, base_score + confidence_adjust))
    risk_level = get_risk_level(risk_score)

    return {"risk_score": risk_score, "risk_level": risk_level}


def calculate_risk_score(emotion, confidence):
    return evaluate_image_risk(emotion, confidence)["risk_score"]


def evaluate_text_risk(text_emotion, score):
    emotion_key = str(text_emotion).lower()
    text_score = int(round(float(score)))
    text_score = max(0, min(100, text_score))

    base_map = {
        "positive": 18,
        "neutral": 25,
        "negative": 45,
        "angry": 65,
        "anxious": 58,
        "tired": 48,
    }
    base_score = base_map.get(emotion_key, 35)
    risk_score = int(round(base_score * 0.6 + text_score * 0.4))
    risk_score = max(0, min(100, risk_score))
    risk_level = get_risk_level(risk_score)

    reason_map = {
        "positive": "命中积极词，整体情绪偏稳定。",
        "neutral": "未命中明显情绪词，文本情绪接近中性。",
        "negative": "命中消极词，存在一定负面情绪表达。",
        "angry": "命中愤怒类词汇，情绪波动较明显。",
        "anxious": "命中焦虑类词汇，存在紧张与担忧倾向。",
        "tired": "命中疲劳类词汇，可能存在身心疲惫状态。",
    }

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": reason_map.get(emotion_key, "检测到一定情绪波动，建议持续观察。"),
    }


def evaluate_audio_risk(audio_emotion, score):
    emotion_key = str(audio_emotion).lower()
    audio_score = int(round(float(score)))
    audio_score = max(0, min(100, audio_score))

    base_map = {
        "calm": 20,
        "tense": 50,
        "low": 52,
        "tired": 54,
        "excited": 62,
    }
    base_score = base_map.get(emotion_key, 38)
    risk_score = int(round(base_score * 0.65 + audio_score * 0.35))
    if emotion_key == "excited" and audio_score >= 75:
        risk_score = max(risk_score, 68)
    risk_score = max(0, min(100, risk_score))
    risk_level = get_risk_level(risk_score)

    reason_map = {
        "calm": "语音能量与过零率处于平稳区间。",
        "tense": "语音能量和语速波动偏高，存在紧张倾向。",
        "low": "语音能量偏低且时长偏短，存在低落倾向。",
        "tired": "语音整体能量偏低，可能存在疲惫状态。",
        "excited": "语音能量与波动明显偏高，存在激动状态。",
    }
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": reason_map.get(emotion_key, "语音状态存在一定波动，建议继续观察。"),
    }
