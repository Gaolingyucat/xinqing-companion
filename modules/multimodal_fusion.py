"""功能模块：封装具体业务能力，供路由层调用。"""

from pathlib import Path

from modules.record_manager import read_records
from modules.risk_engine import get_risk_level


MODALITY_LABELS = {
    "image": "图像",
    "text": "文本",
    "audio": "语音",
}


BASE_WEIGHT_MAP = {
    frozenset({"image", "text", "audio"}): {"image": 0.4, "text": 0.35, "audio": 0.25},
    frozenset({"image", "text"}): {"image": 0.55, "text": 0.45},
    frozenset({"image", "audio"}): {"image": 0.6, "audio": 0.4},
    frozenset({"text", "audio"}): {"text": 0.55, "audio": 0.45},
}


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _latest_records_by_type(records):
    latest = {"image": None, "text": None, "audio": None}
    for row in records:
        input_type = (row.get("input_type", "") or "").strip()
        if input_type in latest and latest[input_type] is None:
            latest[input_type] = row
        if all(latest.values()):
            break
    return latest


def _build_modality_data(row):
    if not row:
        return None
    return {
        "time": row.get("time", ""),
        "emotion": row.get("emotion", ""),
        "emotion_cn": row.get("emotion_cn", ""),
        "confidence": _safe_float(row.get("confidence", 0)),
        "risk_score": _safe_float(row.get("risk_score", 0)),
        "risk_level": row.get("risk_level", ""),
        "suggestion": row.get("suggestion", ""),
    }


def _normalize_weights(weights):
    total = sum(weights.values())
    if total <= 0:
        return {k: 0.0 for k in weights}
    return {k: v / total for k, v in weights.items()}


def fuse_multimodal(csv_path):
    path = Path(csv_path)
    records = read_records(path) if path.exists() else []
    latest = _latest_records_by_type(records)
    modality_data = {k: _build_modality_data(v) for k, v in latest.items()}

    present = [k for k, v in modality_data.items() if v is not None]
    if not present:
        return {
            "has_data": False,
            "modalities": modality_data,
            "participating_modalities": [],
            "raw_scores": {},
            "weights": {},
            "fused_score": 0,
            "fused_level": "低风险",
            "status_text": "暂无可用的图像/文本/语音记录，无法进行多模态融合评估。",
            "advice": "请先完成至少一种模态检测后再进行融合评估。",
            "weight_note": "暂无权重调整。",
            "conflict_results": ["暂无可评估模态，冲突检测未触发。"],
            "fusion_explanation": "系统等待可用的多模态记录后再进行融合。",
        }

    if len(present) == 1:
        only = present[0]
        score = modality_data[only]["risk_score"]
        level = get_risk_level(score)
        return {
            "has_data": True,
            "modalities": modality_data,
            "participating_modalities": [MODALITY_LABELS[only]],
            "raw_scores": {only: score},
            "weights": {only: 1.0},
            "fused_score": round(score, 2),
            "fused_level": level,
            "status_text": "当前仅有单一模态数据，综合结果等同于该模态风险评估。",
            "advice": "建议补充其他模态数据，以提升评估完整性与稳定性。",
            "weight_note": "单模态场景无需权重调整。",
            "conflict_results": ["单模态场景未触发跨模态冲突规则。"],
            "fusion_explanation": "当前仅采纳单一模态风险分数作为融合结果。",
        }

    key = frozenset(present)
    weights = dict(BASE_WEIGHT_MAP.get(key, {m: 1.0 / len(present) for m in present}))
    weight_notes = []
    explain_parts = []
    explain_parts.append(f"基础权重采用 {', '.join([f'{MODALITY_LABELS[m]}={weights[m]:.2f}' for m in present])}。")

    for mod in present:
        conf = modality_data[mod]["confidence"]
        if conf < 0.55:
            weights[mod] *= 0.7
            weight_notes.append(
                f"{MODALITY_LABELS[mod]}置信度 {conf:.2f} < 0.55，权重下调后再归一化。"
            )

    weights = _normalize_weights(weights)
    explain_parts.append(
        "置信度校正后权重为 "
        + ", ".join([f"{MODALITY_LABELS[m]}={weights[m]:.2f}" for m in present])
        + "。"
    )
    raw_scores = {mod: modality_data[mod]["risk_score"] for mod in present}
    fused_score = sum(weights[mod] * raw_scores[mod] for mod in present)
    explain_parts.append(f"加权融合初始分数为 {fused_score:.2f}。")

    medium_or_high_count = 0
    has_high_70 = False
    conflict_results = []
    for mod in present:
        level = modality_data[mod]["risk_level"]
        score = modality_data[mod]["risk_score"]
        if level in {"中风险", "高风险"}:
            medium_or_high_count += 1
        if level == "高风险" and score >= 70:
            has_high_70 = True
            conflict_results.append(
                f"{MODALITY_LABELS[mod]}为高风险且分数≥70，综合风险不低于中风险。"
            )

    if medium_or_high_count >= 2:
        fused_score += 5
        conflict_results.append("两个及以上模态为中风险或高风险，综合分数额外 +5。")

    if has_high_70:
        fused_score = max(fused_score, 31)

    image_data = modality_data.get("image")
    text_data = modality_data.get("text")
    if image_data and text_data:
        if image_data["risk_level"] == "低风险" and text_data["risk_level"] == "高风险":
            fused_score = max(fused_score, 31)
            conflict_results.append("图像低风险但文本高风险，综合风险至少为中风险。")

    if not conflict_results:
        conflict_results.append("未触发冲突修正规则。")

    fused_score = max(0.0, min(100.0, fused_score))
    fused_level = get_risk_level(fused_score)
    explain_parts.append(f"冲突修正后综合分数为 {fused_score:.2f}，对应 {fused_level}。")

    if fused_level == "高风险":
        status_text = "多模态结果显示近期存在较明显风险波动，建议重点关注状态变化。"
        advice = "建议及时减负、短时休息，并与老师或同伴沟通当前压力与状态。"
    elif fused_level == "中风险":
        status_text = "多模态结果显示存在一定压力信号，建议保持观察并优化节奏。"
        advice = "建议减少连续高负荷任务，增加休息间隔，并在稍后复测。"
    else:
        status_text = "多模态结果整体较稳定，可继续保持当前节奏。"
        advice = "建议持续观察日常状态，并保持规律作息。"

    return {
        "has_data": True,
        "modalities": modality_data,
        "participating_modalities": [MODALITY_LABELS[m] for m in present],
        "raw_scores": raw_scores,
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "fused_score": round(fused_score, 2),
        "fused_level": fused_level,
        "status_text": status_text,
        "advice": advice,
        "weight_note": "；".join(weight_notes) if weight_notes else "各模态置信度满足阈值，采用基础权重融合。",
        "conflict_results": conflict_results,
        "fusion_explanation": " ".join(explain_parts),
    }
