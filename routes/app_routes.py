"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from datetime import datetime
import json
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from werkzeug.utils import secure_filename

from modules.audio_emotion import analyze_audio_file
from modules.image_emotion import analyze_image
from modules.llm_advisor import generate_photo_companion_reply, generate_voice_companion_reply
from modules.record_manager import add_record, read_records
from modules.risk_engine import evaluate_audio_risk, evaluate_image_risk
from modules.suggestion_engine import generate_suggestion


app_bp = Blueprint("app", __name__)


VOICE_ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "webm", "ogg"}
PHOTO_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
REMOTE_EMOTION_CN_MAP = {
    "happy": "开心",
    "sad": "难过",
    "angry": "生气",
    "neutral": "平静",
    "fear": "紧张",
    "disgust": "厌恶",
    "surprise": "惊讶",
}
UNSAFE_COMPANION_LLM_TERMS = {
    "治疗",
    "确诊",
    "心理疾病",
    "患者",
    "我可以替代",
    "替代专业帮助",
    "不需要任何专业帮助",
}


def _load_records():
    csv_path = Path(current_app.root_path) / "data" / "records.csv"
    return read_records(csv_path)


def _map_input_type(input_type):
    labels = {
        "image": "自拍心情",
        "photo": "自拍心情",
        "text": "文字倾诉",
        "chat": "AI 倾诉",
        "app_chat": "AI 倾诉",
        "audio": "语音心情",
        "voice": "语音心情",
        "relax": "放松练习",
        "relaxation": "放松练习",
        "relax_music": "放松音乐",
        "multimodal": "综合分析",
        "crisis": "安全提醒",
    }
    key = (input_type or "").strip()
    return labels.get(key, key or "其他")


def _build_today_status(latest_record):
    if not latest_record:
        return {
            "label": "平稳",
            "badge_class": "status-calm",
            "note": "今天还没有新记录，先从一句倾诉或一次放松开始。",
        }

    risk_level = (latest_record.get("risk_level", "") or "").strip()
    emotion = (latest_record.get("emotion_cn", "") or latest_record.get("emotion", "")).strip()

    if risk_level == "高风险" or emotion in {"危机状态", "高压状态"}:
        return {
            "label": "重点关注",
            "badge_class": "status-watch",
            "note": "你今天承受了不少压力。先稳住自己，再找一位可信任的人聊聊。",
        }

    if risk_level == "中风险":
        return {
            "label": "有压力",
            "badge_class": "status-stress",
            "note": "今天有一些压力痕迹。先把最压你的那一件事拆小一点。",
        }

    return {
        "label": "平稳",
        "badge_class": "status-calm",
        "note": "今天整体状态还算平稳，继续保持对情绪的小关注。",
    }


def _pick_companion_line(status_label):
    mapping = {
        "重点关注": "你不用一个人扛完全部，我们先把眼前这一步照顾好。",
        "有压力": "先别急着把所有问题同时解决，先从最小的一步开始。",
        "平稳": "情绪有起伏很正常，能记录下来就是一种温柔的力量。",
    }
    return mapping.get(status_label, mapping["平稳"])


def _status_to_weather(status_label, latest_record=None):
    emotion = str((latest_record or {}).get("emotion_cn", "") or "")
    if emotion in {"难过", "低落"} and status_label != "重点关注":
        return {"weather": "小雨", "emoji": "🌧", "line": "今天像小雨天，慢一点也没关系。"}

    weather_map = {
        "平稳": {"weather": "晴", "emoji": "☀️", "line": "今天是晴天心情，继续慢慢来。"},
        "有压力": {"weather": "多云", "emoji": "☁️", "line": "云有点厚，先照顾好当下这一步。"},
        "重点关注": {"weather": "暴雨预警", "emoji": "⛈", "line": "风雨有点大，先确保安全，再找人聊聊。"},
    }
    return weather_map.get(status_label, {"weather": "小雨", "emoji": "🌧", "line": "有点下雨也没关系，先轻轻放慢。"})


def _build_recent_records(records, limit=3):
    rows = []
    for row in records[:limit]:
        rows.append(
            {
                "time": row.get("time", ""),
                "input_type": _map_input_type(row.get("input_type", "")),
                "input_type_key": (row.get("input_type", "") or "").strip(),
                "emotion": (
                    row.get("emotion_cn", "") or row.get("emotion", "") or "未知情绪"
                ).strip(),
                "risk_level": row.get("risk_level", ""),
            }
        )
    return rows


def _build_music_recommendations(latest_record):
    emotion = (latest_record or {}).get("emotion_cn", "") if latest_record else ""
    risk_level = (latest_record or {}).get("risk_level", "") if latest_record else ""
    emotion = str(emotion or "")
    risk_level = str(risk_level or "")

    group_key = "calm"
    if risk_level == "高风险" or emotion in {"高压状态", "焦虑"}:
        group_key = "stress"
    elif emotion in {"疲惫"}:
        group_key = "tired"
    elif emotion in {"难过", "低落"}:
        group_key = "sad"

    groups = {
        "stress": [
            ("雨声放松", "雨声 白噪音 放松", "焦虑/压力大", "像把心里的噪音调低一点。"),
            ("呼吸冥想", "呼吸 冥想 音乐", "焦虑/压力大", "先把节奏放慢，再看下一步。"),
            ("森林白噪音", "森林 白噪音", "焦虑/压力大", "让注意力先回到当下。"),
        ],
        "tired": [
            ("睡前钢琴", "睡前 钢琴 轻音乐", "疲惫/想休息", "适合让脑子慢慢降速。"),
            ("自然声音", "自然声音 放松", "疲惫/想休息", "不需要想太多，先躺一会。"),
            ("低速纯音乐", "慢节奏 纯音乐", "疲惫/想休息", "给自己一个短暂停靠点。"),
        ],
        "sad": [
            ("温柔治愈", "温柔 治愈 音乐", "难过/低落", "先让心情被轻轻接住。"),
            ("舒缓人声", "舒缓 人声 歌单", "难过/低落", "像有人在旁边安静陪着你。"),
            ("安静歌单", "安静 歌单 放松", "难过/低落", "先不急着变好，先稳住。"),
        ],
        "calm": [
            ("Lo-fi 专注", "lofi focus", "平稳/想专注", "适合学习或工作时慢慢进入状态。"),
            ("森林环境音", "森林 环境音", "平稳/想专注", "给思绪留一点呼吸空间。"),
            ("轻节奏纯音乐", "轻节奏 纯音乐", "平稳/想专注", "保持温和稳定的节奏。"),
        ],
    }

    cards = []
    for title, keyword, fit_for, desc in groups[group_key]:
        encoded = quote(keyword)
        cards.append(
            {
                "title": title,
                "keyword": keyword,
                "fit_for": fit_for,
                "description": desc,
                "links": {
                    "netease": f"https://music.163.com/#/search/m/?s={encoded}&type=1",
                    "qq": f"https://y.qq.com/n/ryqq/search?w={encoded}",
                    "spotify": f"https://open.spotify.com/search/{encoded}",
                    "apple": f"https://music.apple.com/cn/search?term={encoded}",
                },
            }
        )
    return cards


def _build_ready_checks():
    return [
        ("首页可访问", True),
        ("聊天可用", True),
        ("语音输入可用", True),
        ("图片输入可用", True),
        ("多模态综合可用", True),
        ("放松空间可用", True),
        ("放松音乐可用", True),
        ("记录页可用", True),
        ("隐私说明已补齐", True),
        ("非医疗声明已补齐", True),
    ]


def _build_journal_records(records, limit=120):
    def _parse_time(value):
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _shorten_suggestion(text, max_len=34):
        value = str(text or "").strip()
        if not value:
            return "继续按自己的节奏慢慢来。"
        if len(value) <= max_len:
            return value
        return f"{value[:max_len]}..."

    def _is_focus_record(record):
        risk_level = str(record.get("risk_level", "") or "").strip()
        emotion = str(record.get("emotion", "") or "").strip()
        return risk_level in {"高风险", "中高风险"} or emotion in {"危机状态", "高压状态", "重点关注"}

    rows = []
    today = datetime.now().date()
    for row in records[:limit]:
        key = (row.get("input_type", "") or "").strip()
        parsed_time = _parse_time(row.get("time", ""))
        time_raw = str(row.get("time", "") or "").strip()
        date_key = parsed_time.strftime("%Y-%m-%d") if parsed_time else (time_raw.split(" ")[0] if time_raw else "未知日期")
        time_short = parsed_time.strftime("%H:%M") if parsed_time else (time_raw[11:16] if len(time_raw) >= 16 else "--:--")
        emotion_text = (row.get("emotion_cn", "") or row.get("emotion", "") or "未知情绪").strip()
        risk_level = str(row.get("risk_level", "") or "未知").strip()
        suggestion_full = str(row.get("suggestion", "") or "").strip()
        confidence_raw = row.get("confidence", "")
        confidence_text = ""
        if str(confidence_raw or "").strip():
            try:
                conf_value = float(confidence_raw)
                if conf_value <= 1:
                    confidence_text = f"{conf_value * 100:.1f}%"
                else:
                    confidence_text = f"{conf_value:.1f}"
            except ValueError:
                confidence_text = str(confidence_raw)

        focus_flag = _is_focus_record({"risk_level": risk_level, "emotion": emotion_text})
        focus_status = emotion_text if emotion_text in {"危机状态", "高压状态", "重点关注"} else risk_level
        rows.append(
            {
                "time": time_raw,
                "time_short": time_short,
                "date_key": date_key,
                "is_today": parsed_time.date() == today if parsed_time else False,
                "input_type": _map_input_type(key),
                "input_type_key": key,
                "emotion": emotion_text,
                "risk_level": risk_level,
                "suggestion": _shorten_suggestion(suggestion_full),
                "suggestion_full": suggestion_full or "继续按自己的节奏慢慢来。",
                "confidence": confidence_text,
                "icon": _pick_type_icon(key),
                "filter_group": _record_filter_group(key),
                "is_focus": focus_flag,
                "focus_status": focus_status,
                "source": str(row.get("source", "") or "").strip(),
            }
        )
    return rows


def _build_journal_today_summary(journal_records):
    today_rows = [row for row in journal_records if row.get("is_today")]
    if not today_rows:
        return {
            "count": 0,
            "main_status": "暂无记录",
            "weather": "晴",
            "reminder": "这里还很安静，等你慢慢写下第一条心情。",
        }

    high_risk_hit = any(
        row["risk_level"] == "高风险" or row["emotion"] in {"危机状态", "重点关注"}
        for row in today_rows
    )
    high_pressure_hit = any(row["emotion"] in {"高压状态", "重点关注"} for row in today_rows)
    mid_count = sum(1 for row in today_rows if row["risk_level"] == "中风险")
    low_count = sum(1 for row in today_rows if row["risk_level"] == "低风险")

    if high_risk_hit:
        return {
            "count": len(today_rows),
            "main_status": "重点关注",
            "weather": "暴雨预警",
            "reminder": "今天出现过需要重点关注的记录。",
        }
    if high_pressure_hit or mid_count >= 2:
        return {
            "count": len(today_rows),
            "main_status": "有压力",
            "weather": "小雨",
            "reminder": "今天压力有点高，适合慢一点。",
        }
    if mid_count > 0 and mid_count >= low_count:
        return {
            "count": len(today_rows),
            "main_status": "有压力",
            "weather": "多云",
            "reminder": "今天有一些压力痕迹，先照顾好自己。",
        }
    return {
        "count": len(today_rows),
        "main_status": "平稳",
        "weather": "晴",
        "reminder": "今天整体还算平稳，继续保持自己的节奏。",
    }


def _build_journal_focus_rows(journal_records, limit=3):
    rows = [row for row in journal_records if row.get("is_today") and row.get("is_focus")]
    return rows[:limit]


def _record_filter_group(input_type_key):
    key = str(input_type_key or "").strip()
    if key in {"text", "chat", "app_chat"}:
        return "text"
    if key in {"audio", "voice"}:
        return "voice"
    if key in {"image", "photo"}:
        return "photo"
    if key.startswith("relax"):
        return "relax"
    return "other"


def _pick_type_icon(input_type_key):
    key = str(input_type_key or "")
    if key in {"text", "chat", "app_chat"}:
        return "💬"
    if key in {"audio", "voice"}:
        return "🎧"
    if key in {"image", "photo"}:
        return "📷"
    if key == "relax_music":
        return "🎵"
    if key.startswith("relax"):
        return "🌙"
    if key == "multimodal":
        return "✨"
    return "📔"


def _calculate_profile_stats(records):
    total_count = len(records)
    high_risk_count = sum(1 for row in records if row.get("risk_level", "") == "高风险")
    multimodal_count = sum(
        1
        for row in records
        if (row.get("input_type", "") or "").strip() in {"image", "photo", "audio", "voice", "text", "chat", "app_chat"}
    )

    days = 1
    continuous_days = 1
    valid_dates = []
    for row in records:
        time_value = (row.get("time", "") or "").strip()
        if not time_value:
            continue
        try:
            valid_dates.append(datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S").date())
        except ValueError:
            continue

    if valid_dates:
        earliest = min(valid_dates)
        days = max((datetime.now().date() - earliest).days + 1, 1)

        dates = sorted(set(valid_dates), reverse=True)
        current = dates[0]
        continuous_days = 1
        for next_day in dates[1:]:
            if (current - next_day).days == 1:
                continuous_days += 1
                current = next_day
            else:
                break

    return {
        "days": days,
        "continuous_days": continuous_days,
        "total_count": total_count,
        "high_risk_count": high_risk_count,
        "multimodal_count": multimodal_count,
    }


def _extract_latest_by_types(records, keys):
    for row in records:
        if (row.get("input_type", "") or "").strip() in keys:
            return {
                "time": row.get("time", ""),
                "emotion": (row.get("emotion_cn", "") or row.get("emotion", "") or "未知").strip(),
                "risk_level": row.get("risk_level", ""),
                "risk_score": int(float(row.get("risk_score", "0") or 0)),
            }
    return None


def _is_negative_emotion(emotion_text):
    text = str(emotion_text or "")
    negative_words = {"焦虑", "愤怒", "疲惫", "低落", "难过", "消极", "高压状态", "危机状态", "紧张", "悲伤"}
    return text in negative_words


def _build_multimodal_result(records):
    text_data = _extract_latest_by_types(records, {"text", "chat", "app_chat"})
    audio_data = _extract_latest_by_types(records, {"audio", "voice"})
    image_data = _extract_latest_by_types(records, {"image", "photo"})

    modalities = {"text": text_data, "audio": audio_data, "image": image_data}
    available = [v for v in modalities.values() if v]
    if not available:
        return {
            "has_data": False,
            "text": text_data,
            "audio": audio_data,
            "image": image_data,
            "status": "暂无",
            "risk_level": "暂无",
            "weather": "暂无",
            "reason": "暂无足够记录",
            "suggestion": "先完成一次文字、语音或自拍心情记录。",
            "flow": "文字/语音/图像 → 多模态融合 → 综合状态",
        }

    high_trigger = any(v["risk_level"] == "高风险" or v["emotion"] == "危机状态" for v in available)
    negative_count = sum(1 for v in available if _is_negative_emotion(v["emotion"]))

    if high_trigger:
        risk_level = "高风险"
        status = "重点关注"
    elif negative_count >= 2:
        risk_level = "中风险"
        status = "有压力"
    elif negative_count == 1:
        risk_level = "中风险"
        status = "有压力"
    else:
        risk_level = "低风险"
        status = "平稳"

    reason_parts = []
    if text_data:
        reason_parts.append(f"文字{ text_data['emotion'] }")
    if audio_data:
        reason_parts.append(f"语音{ audio_data['emotion'] }")
    if image_data:
        reason_parts.append(f"自拍{ image_data['emotion'] }")
    reason = "，".join(reason_parts)

    if risk_level == "高风险":
        suggestion = "你现在可能承受了较强压力。先确认自己安全，再联系一位可信任的人聊聊。"
    elif risk_level == "中风险":
        suggestion = "先把最压你的一件事拆小，再给自己一个短休息，按一步一步来。"
    else:
        suggestion = "整体状态比较平稳，继续按自己的节奏记录和表达就好。"

    weather = "晴"
    if status == "重点关注":
        weather = "暴雨预警"
    elif status == "有压力":
        weather = "多云"

    return {
        "has_data": True,
        "text": text_data,
        "audio": audio_data,
        "image": image_data,
        "status": status,
        "risk_level": risk_level,
        "weather": weather,
        "reason": reason,
        "suggestion": suggestion,
        "flow": "文字/语音/图像 → 多模态融合 → 综合状态",
    }


def _save_uploaded_file(file_storage, folder, prefix):
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("文件名无效")

    suffix = Path(filename).suffix.lower().lstrip(".")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{prefix}_{timestamp}_{Path(filename).stem}.{suffix}"
    save_dir = Path(current_app.root_path) / "uploads" / folder
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / final_name
    file_storage.save(save_path)
    return final_name, save_path


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normalize_confidence(value):
    confidence = _safe_float(value, 0.0)
    if confidence > 1:
        confidence = confidence / 100.0
    return max(0.0, min(1.0, confidence))


def _normalize_remote_image_result(payload):
    if not isinstance(payload, dict):
        return None
    if not bool(payload.get("success")):
        return None

    emotion = str(payload.get("emotion", "") or "").strip().lower()
    if not emotion:
        return None

    emotion_cn = str(payload.get("emotion_cn", "") or "").strip()
    if not emotion_cn:
        emotion_cn = REMOTE_EMOTION_CN_MAP.get(emotion, "平静")

    return {
        "emotion": emotion,
        "emotion_cn": emotion_cn,
        "confidence": _normalize_confidence(payload.get("confidence", 0)),
        "source": str(payload.get("source", "") or "deepface_remote").strip() or "deepface_remote",
        "warning": "",
    }


def _call_remote_deepface_api(image_path):
    api_url = str(current_app.config.get("DEEPFACE_API_URL", "") or "").strip()
    if not api_url:
        return None

    timeout_seconds = max(3.0, _safe_float(current_app.config.get("DEEPFACE_TIMEOUT_SECONDS", 30), 30))
    try:
        with open(image_path, "rb") as image_handle:
            response = requests.post(
                api_url,
                files={"file": (Path(image_path).name, image_handle)},
                timeout=timeout_seconds,
            )
    except requests.RequestException as error:
        current_app.logger.warning("DeepFace 远程调用失败：%s", error)
        return None

    if not response.ok:
        current_app.logger.warning(
            "DeepFace 远程调用返回非成功状态：status=%s",
            response.status_code,
        )
        return None

    try:
        payload = response.json()
    except ValueError:
        current_app.logger.warning("DeepFace 远程调用返回非 JSON 内容")
        return None

    return _normalize_remote_image_result(payload)


def _call_local_deepface_if_enabled(image_path):
    if not bool(current_app.config.get("LOCAL_DEEPFACE_ENABLED", False)):
        return None

    local_result = analyze_image(str(image_path))
    if not isinstance(local_result, dict):
        return None

    source = str(local_result.get("source", "") or "").strip().lower()
    if source == "mock":
        # mock 表示本地 DeepFace 不可用，不作为有效回退结果。
        return None

    return {
        "emotion": str(local_result.get("emotion", "") or "neutral").strip().lower(),
        "emotion_cn": str(local_result.get("emotion_cn", "") or "平静").strip(),
        "confidence": _normalize_confidence(local_result.get("confidence", 0)),
        "source": "deepface_local",
        "warning": "",
    }


def _get_image_analysis_result(image_path):
    remote_result = _call_remote_deepface_api(image_path)
    if remote_result:
        return remote_result
    return _call_local_deepface_if_enabled(image_path)


def _parse_photo_user_context(raw_context):
    if isinstance(raw_context, list):
        return raw_context
    if not raw_context:
        return []
    try:
        parsed = json.loads(str(raw_context))
        if isinstance(parsed, list):
            return parsed
    except Exception:
        return []
    return []


def _build_photo_fallback_reply(image_result, risk_level):
    emotion_cn = str(image_result.get("emotion_cn", "平静") or "平静")
    if risk_level in {"高风险", "中高风险"}:
        return (
            f"这张照片里你看起来有点{emotion_cn}，像在硬撑着。"
            "不过照片只能记录一个瞬间，未必等于你全部感受。"
            "先确认自己在安全的位置，再找一个你信任的人说说现在的状态，好吗？"
        )
    return (
        f"这张照片给人的感觉偏{emotion_cn}，不过表情只能作为参考。"
        "真正的感受还是你自己最清楚。"
        "如果你愿意，可以补充一句你现在最真实的心情。"
    )


def _contains_unsafe_photo_reply(text):
    content = str(text or "")
    return any(term in content for term in UNSAFE_COMPANION_LLM_TERMS)


def _build_voice_fallback_reply(audio_result, risk_level):
    emotion_cn = str(audio_result.get("emotion_cn", "平稳") or "平稳")
    if risk_level in {"高风险", "中高风险"}:
        return (
            f"听起来你刚刚这段声音里有点{emotion_cn}，像是一直在用力撑着。"
            "声音只能作为参考，但如果你现在确实很绷着，先暂停一下，确认自己在安全的位置，"
            "再联系一位你信任的人说说现在的状态。"
        )
    return (
        f"听起来你刚刚的状态有点{emotion_cn}，不过声音只能作为参考。"
        "真正的感受还是你自己最清楚。你愿意补充一句，现在最明显的感受是什么吗？"
    )


@app_bp.route("/app")
def app_home():
    records = _load_records()
    latest_record = records[0] if records else None

    latest_summary = None
    if latest_record:
        latest_summary = {
            "emotion": (
                latest_record.get("emotion_cn", "")
                or latest_record.get("emotion", "")
                or "未知情绪"
            ).strip(),
            "risk_level": (latest_record.get("risk_level", "") or "未知").strip(),
            "time": (latest_record.get("time", "") or "").strip(),
        }

    today_status = _build_today_status(latest_record)
    mood_weather = _status_to_weather(today_status["label"], latest_record=latest_record)
    music_recommend = _build_music_recommendations(latest_record)

    return render_template(
        "app_home.html",
        latest_summary=latest_summary,
        today_status=today_status,
        mood_weather=mood_weather,
        music_recommend=music_recommend,
        companion_line=_pick_companion_line(today_status["label"]),
        recent_records=_build_recent_records(records, 3),
        nav_active="home",
    )


@app_bp.route("/app/onboarding")
def app_onboarding_page():
    return render_template("app_onboarding.html", nav_active="profile")


@app_bp.route("/app/sessions")
def app_sessions_page():
    return render_template("app_sessions.html", nav_active="chat")


@app_bp.route("/app/voice")
def app_voice_page():
    return render_template("app_voice.html", nav_active="chat")


@app_bp.route("/app/photo")
def app_photo_page():
    return render_template("app_photo.html", nav_active="home")


@app_bp.route("/app/multimodal")
def app_multimodal_page():
    records = _load_records()
    return render_template(
        "app_multimodal.html",
        multimodal=_build_multimodal_result(records),
        nav_active="home",
    )


@app_bp.route("/app/demo")
def app_demo_page():
    records = _load_records()
    multimodal = _build_multimodal_result(records)
    return render_template(
        "app_demo.html",
        multimodal=multimodal,
        today_status=_build_today_status(records[0] if records else None),
        nav_active="home",
    )


@app_bp.route("/app/relax/music")
def app_relax_music_page():
    records = _load_records()
    latest_record = records[0] if records else None
    cards = _build_music_recommendations(latest_record)
    status_label = _build_today_status(latest_record)["label"]
    return render_template(
        "app_relax_music.html",
        music_cards=cards,
        status_label=status_label,
        nav_active="relax",
    )


@app_bp.route("/app/privacy")
def app_privacy_page():
    return render_template("app_privacy.html", nav_active="profile")


@app_bp.route("/app/usage")
def app_usage_page():
    return render_template("app_usage.html", nav_active="profile")


@app_bp.route("/app/ready")
def app_ready_page():
    return render_template(
        "app_ready.html",
        checks=_build_ready_checks(),
        nav_active="profile",
    )


@app_bp.route("/app/call")
def app_call_page():
    return render_template("app_call.html", nav_active="chat")


@app_bp.route("/app/journal")
def app_journal_page():
    records = _load_records()
    journal_rows = _build_journal_records(records, 200)
    return render_template(
        "app_journal.html",
        journal_records=journal_rows,
        today_summary=_build_journal_today_summary(journal_rows),
        focus_rows=_build_journal_focus_rows(journal_rows, 3),
        nav_active="journal",
    )


@app_bp.route("/app/profile")
def app_profile_page():
    records = _load_records()
    return render_template(
        "app_profile.html",
        profile=_calculate_profile_stats(records),
        nav_active="profile",
    )


@app_bp.route("/api/app/photo_analyze", methods=["POST"])
def app_photo_analyze_api():
    image_file = request.files.get("image_file")
    if image_file is None or image_file.filename == "":
        return jsonify({"ok": False, "error": "请先上传图片。"}), 400

    suffix = Path(image_file.filename).suffix.lower().lstrip(".")
    if suffix not in PHOTO_ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "error": "仅支持 jpg、jpeg、png 图片。"}), 400

    try:
        final_name, save_path = _save_uploaded_file(image_file, "images", "app_photo")
    except Exception:
        return jsonify({"ok": False, "error": "图片保存失败，请稍后重试。"}), 500

    image_result = _get_image_analysis_result(str(save_path))
    if not image_result:
        try:
            Path(save_path).unlink(missing_ok=True)
        except Exception:
            pass
        return jsonify({"ok": False, "error": "这次没有识别出来，可以换一张更清楚的照片。"}), 200

    risk_result = evaluate_image_risk(image_result["emotion"], image_result["confidence"])
    suggestion = generate_suggestion(
        input_type="图像",
        emotion_cn=image_result["emotion_cn"],
        risk_level=risk_result["risk_level"],
        risk_score=risk_result["risk_score"],
    )

    user_context = _parse_photo_user_context(request.form.get("conversation_history"))
    llm_result = {
        "reply": "",
        "llm_emotion": "",
        "llm_intent": "",
        "llm_reason": "",
        "source": "local",
        "warning": "",
    }
    reply_source = "本地模板"

    if bool(current_app.config.get("ENABLE_LLM_ADVISOR", False)):
        llm_result = generate_photo_companion_reply(
            photo_result=image_result,
            risk_result={
                "risk_level": risk_result["risk_level"],
                "risk_score": risk_result["risk_score"],
                "suggestion": suggestion,
            },
            user_context=user_context,
        )

    companion_reply = str(llm_result.get("reply", "") or "").strip()
    warning = str(llm_result.get("warning", "") or "").strip()
    llm_emotion = str(llm_result.get("llm_emotion", "") or "")
    llm_intent = str(llm_result.get("llm_intent", "") or "普通聊天")
    llm_reason = str(llm_result.get("llm_reason", "") or "")

    if companion_reply and not _contains_unsafe_photo_reply(companion_reply):
        reply_source = "MiMo AI"
        warning = ""
    else:
        companion_reply = _build_photo_fallback_reply(image_result, risk_result["risk_level"])
        reply_source = "本地模板"
        if warning:
            warning = "已切换为本地模板回复"

    add_record(
        csv_path=Path(current_app.root_path) / "data" / "records.csv",
        input_type="photo",
        emotion=image_result["emotion"],
        emotion_cn=image_result["emotion_cn"],
        confidence=image_result["confidence"],
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
        suggestion=suggestion,
        file_path=str(save_path),
    )

    return jsonify(
        {
            "ok": True,
            "result": {
                "emotion": image_result["emotion"],
                "emotion_cn": image_result["emotion_cn"],
                "confidence": image_result["confidence"],
                "risk_score": risk_result["risk_score"],
                "risk_level": risk_result["risk_level"],
                "suggestion": suggestion,
                "reply": companion_reply,
                "llm_emotion": llm_emotion or image_result["emotion_cn"],
                "llm_intent": llm_intent,
                "llm_reason": llm_reason or "结合图像参考结果生成陪伴回复。",
                "reply_source": reply_source,
                "image_url": url_for("image.serve_uploaded_image", filename=final_name),
                "source": image_result.get("source", "deepface_remote"),
                "warning": warning,
            },
        }
    )


@app_bp.route("/api/app/voice_analyze", methods=["POST"])
def app_voice_analyze_api():
    audio_blob = request.files.get("audio_blob")
    if audio_blob is None or audio_blob.filename == "":
        return jsonify({"ok": False, "error": "请先上传语音。"}), 400

    suffix = Path(audio_blob.filename).suffix.lower().lstrip(".")
    if suffix not in VOICE_ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "error": "语音格式不支持。"}), 400

    try:
        _, save_path = _save_uploaded_file(audio_blob, "audio", "app_voice")
    except Exception:
        return jsonify({"ok": False, "error": "语音保存失败，请稍后重试。"}), 500

    audio_result = analyze_audio_file(str(save_path))
    risk_result = evaluate_audio_risk(audio_result["emotion"], audio_result["audio_score"])
    suggestion = generate_suggestion(
        input_type="audio",
        emotion_cn=audio_result["emotion_cn"],
        risk_level=risk_result["risk_level"],
        risk_score=risk_result["risk_score"],
    )

    user_context = _parse_photo_user_context(request.form.get("conversation_history"))
    llm_result = {
        "reply": "",
        "llm_emotion": "",
        "llm_intent": "",
        "llm_reason": "",
        "source": "local",
        "warning": "",
    }
    reply_source = "本地模板"

    if bool(current_app.config.get("ENABLE_LLM_ADVISOR", False)):
        llm_result = generate_voice_companion_reply(
            voice_result=audio_result,
            risk_result={
                "risk_level": risk_result["risk_level"],
                "risk_score": risk_result["risk_score"],
                "suggestion": suggestion,
            },
            user_context=user_context,
        )

    companion_reply = str(llm_result.get("reply", "") or "").strip()
    warning = str(llm_result.get("warning", "") or "").strip()
    llm_emotion = str(llm_result.get("llm_emotion", "") or "")
    llm_intent = str(llm_result.get("llm_intent", "") or "普通聊天")
    llm_reason = str(llm_result.get("llm_reason", "") or "")

    if companion_reply and not _contains_unsafe_photo_reply(companion_reply):
        reply_source = "MiMo AI"
        warning = ""
    else:
        companion_reply = _build_voice_fallback_reply(audio_result, risk_result["risk_level"])
        reply_source = "本地模板"
        if warning:
            warning = "已切换为本地模板回复"

    add_record(
        csv_path=Path(current_app.root_path) / "data" / "records.csv",
        input_type="voice",
        emotion=audio_result["emotion"],
        emotion_cn=audio_result["emotion_cn"],
        confidence=audio_result["confidence"],
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
        suggestion=suggestion,
        file_path=str(save_path),
    )

    return jsonify(
        {
            "ok": True,
            "result": {
                "emotion": audio_result["emotion"],
                "emotion_cn": audio_result["emotion_cn"],
                "confidence": audio_result["confidence"],
                "features": audio_result["features"],
                "risk_score": risk_result["risk_score"],
                "risk_level": risk_result["risk_level"],
                "suggestion": suggestion,
                "reply": companion_reply,
                "llm_emotion": llm_emotion or audio_result["emotion_cn"],
                "llm_intent": llm_intent,
                "llm_reason": llm_reason or "结合语音参考结果生成陪伴回复。",
                "reply_source": reply_source,
                "source": "audio_rule_engine",
                "transcript": None,
                "warning": warning or audio_result.get("warning", ""),
            },
        }
    )


@app_bp.route("/api/app/relax/mood_game", methods=["POST"])
def app_relax_mood_game_api():
    payload = request.get_json(silent=True) or {}
    mood = str(payload.get("mood", "") or "").strip()
    weather = str(payload.get("weather", "") or "").strip()
    note = str(payload.get("note", "") or "").strip()

    if not mood:
        return jsonify({"ok": False, "error": "请先选择一个心情。"}), 400

    mood_to_level = {
        "晴": ("平静", "低风险", 22, "保持这个节奏，也给自己一点轻松时间。"),
        "多云": ("疲惫", "中风险", 48, "先暂停一下，把最压你的那件事拆小一点。"),
        "小雨": ("难过", "中风险", 56, "先照顾一下呼吸和节奏，再做一个很小的动作。"),
        "暴雨预警": ("高压状态", "高风险", 80, "先确认自己在安全位置，尽快联系一位可信任的人聊聊。"),
    }
    emotion_cn, risk_level, risk_score, suggestion = mood_to_level.get(
        weather or "多云",
        ("疲惫", "中风险", 48, "先给自己一点缓冲，再做一个小步骤。"),
    )

    add_record(
        csv_path=Path(current_app.root_path) / "data" / "records.csv",
        input_type="relax",
        emotion=emotion_cn,
        emotion_cn=emotion_cn,
        confidence=1.0,
        risk_score=risk_score,
        risk_level=risk_level,
        suggestion=f"{suggestion}（情绪星球记录：{mood}）",
        file_path=note or "mood_game",
    )

    return jsonify(
        {
            "ok": True,
            "result": {
                "emotion_cn": emotion_cn,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "suggestion": suggestion,
            },
        }
    )


@app_bp.route("/api/app/relax/music_done", methods=["POST"])
def app_relax_music_done_api():
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "") or "").strip()
    keyword = str(payload.get("keyword", "") or "").strip()

    if not title:
        title = "放松音乐"

    add_record(
        csv_path=Path(current_app.root_path) / "data" / "records.csv",
        input_type="relax_music",
        emotion="放松练习",
        emotion_cn="放松练习",
        confidence=1.0,
        risk_score=20,
        risk_level="低风险",
        suggestion="已完成一次放松音乐练习",
        file_path=keyword or title,
    )
    return jsonify({"ok": True})
