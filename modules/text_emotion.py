"""功能模块：封装具体业务能力，供路由层调用。"""

EMOTION_LEXICON = {
    "positive": ["开心", "放松", "顺利", "舒服", "满意", "平静", "安心", "愉快", "轻松"],
    "negative": ["难受", "低落", "崩溃", "痛苦", "压抑", "失望", "委屈", "沮丧", "好崩溃"],
    "angry": ["生气", "愤怒", "烦", "暴躁", "火大", "讨厌", "忍不了", "气死", "很烦"],
    "anxious": [
        "焦虑",
        "紧张",
        "害怕",
        "担心",
        "慌",
        "不安",
        "恐惧",
        "压力大",
        "压力好大",
        "撑不住",
        "不知道怎么办",
        "我该怎么办",
        "怎么办",
    ],
    "tired": ["累", "疲惫", "困", "困倦", "没精神", "想睡", "乏力", "好累", "心累"],
}


EMOTION_CN_MAP = {
    "positive": "积极",
    "negative": "消极",
    "angry": "愤怒",
    "anxious": "焦虑",
    "tired": "疲劳",
    "neutral": "中性",
}


WEIGHTS = {
    "positive": -6,
    "negative": 8,
    "angry": 12,
    "anxious": 10,
    "tired": 7,
}


PRIORITY = ["angry", "anxious", "negative", "tired", "positive"]


def analyze_text(text):
    content = str(text or "").strip()
    if not content:
        return {
            "emotion": "neutral",
            "emotion_cn": EMOTION_CN_MAP["neutral"],
            "matched_keywords": [],
            "text_score": 50,
        }

    category_hits = {key: [] for key in EMOTION_LEXICON}
    weighted_score = 50

    for category, words in EMOTION_LEXICON.items():
        for word in words:
            count = content.count(word)
            if count > 0:
                category_hits[category].extend([word] * count)
                weighted_score += WEIGHTS[category] * count

    weighted_score = max(0, min(100, weighted_score))
    primary_emotion = "neutral"
    max_hits = 0
    for key in PRIORITY:
        hit_count = len(category_hits[key])
        if hit_count > max_hits:
            max_hits = hit_count
            primary_emotion = key

    if max_hits == 0:
        primary_emotion = "neutral"

    matched_keywords = []
    seen = set()
    for key in PRIORITY:
        for word in category_hits[key]:
            if word not in seen:
                seen.add(word)
                matched_keywords.append(word)

    return {
        "emotion": primary_emotion,
        "emotion_cn": EMOTION_CN_MAP[primary_emotion],
        "matched_keywords": matched_keywords,
        "text_score": int(round(weighted_score)),
    }
