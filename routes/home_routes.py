"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from collections import Counter
from pathlib import Path

from flask import Blueprint, current_app, render_template

from modules.record_manager import read_records


home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    csv_path = Path(current_app.root_path) / "data" / "records.csv"
    records = read_records(csv_path)

    total_count = len(records)
    high_risk_count = sum(1 for row in records if row.get("risk_level", "") == "高风险")
    latest_record = records[0] if records else {}
    latest_risk_level = latest_record.get("risk_level", "暂无") if records else "暂无"
    latest_emotion = (
        latest_record.get("emotion_cn", "") or latest_record.get("emotion", "") or "暂无"
    ).strip() or "暂无"
    latest_time = latest_record.get("time", "暂无") if records else "暂无"

    if not records:
        latest_status_note = "当前尚无检测数据，系统已准备就绪，可开始多模态检测。"
    elif latest_risk_level == "高风险":
        latest_status_note = "最近一次结果为高风险，建议优先复核并结合历史记录及时干预。"
    elif latest_risk_level == "中风险":
        latest_status_note = "最近一次结果为中风险，建议继续跟踪并增加后续检测频率。"
    elif latest_risk_level == "低风险":
        latest_status_note = "最近一次结果为低风险，当前整体状态平稳，可维持常规监测。"
    else:
        latest_status_note = "最近一次检测已完成，建议结合多模态结果进行综合研判。"

    emotion_counter = Counter()
    for row in records:
        emotion_name = (row.get("emotion_cn", "") or row.get("emotion", "")).strip()
        if emotion_name:
            emotion_counter[emotion_name] += 1
    top_emotion = emotion_counter.most_common(1)[0][0] if emotion_counter else "暂无"

    type_labels = {"image": "图像识别", "text": "文本分析", "audio": "语音识别"}
    recent_records = []
    for row in records[:5]:
        input_type = (row.get("input_type", "") or "").strip()
        recent_records.append(
            {
                "time": row.get("time", ""),
                "input_type": type_labels.get(input_type, input_type or "未知类型"),
                "emotion_cn": row.get("emotion_cn", ""),
                "risk_level": row.get("risk_level", ""),
                "risk_score": row.get("risk_score", ""),
            }
        )

    return render_template(
        "index.html",
        dashboard={
            "total_count": total_count,
            "high_risk_count": high_risk_count,
            "latest_risk_level": latest_risk_level,
            "latest_emotion": latest_emotion,
            "latest_time": latest_time,
            "latest_status_note": latest_status_note,
            "top_emotion": top_emotion,
            "recent_records": recent_records,
        },
    )
