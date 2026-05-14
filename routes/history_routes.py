"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from modules.record_manager import clear_records, read_records


history_bp = Blueprint("history", __name__)

INPUT_TYPE_LABELS = {
    "image": "图像识别",
    "text": "文本分析",
    "audio": "语音识别",
}


@history_bp.route("/history", methods=["GET", "POST"])
def history_page():
    csv_path = Path(current_app.root_path) / "data" / "records.csv"
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "clear":
            clear_records(csv_path)
            return redirect(url_for("history.history_page", cleared="1"))

    rows = []
    high_risk_count = 0
    image_count = 0
    text_count = 0

    for item in read_records(csv_path):
        input_type = item.get("input_type", "")
        if input_type == "image":
            image_count += 1
        elif input_type == "text":
            text_count += 1
        if item.get("risk_level", "") == "高风险":
            high_risk_count += 1

        rows.append(
            {
                "time": item.get("time", ""),
                "input_type": INPUT_TYPE_LABELS.get(input_type, input_type or "未知类型"),
                "emotion": item.get("emotion", ""),
                "emotion_cn": item.get("emotion_cn", ""),
                "confidence": item.get("confidence", ""),
                "risk_score": item.get("risk_score", ""),
                "risk_level": item.get("risk_level", ""),
                "suggestion": item.get("suggestion", ""),
                "file_path": item.get("file_path", ""),
            }
        )

    stats = {
        "total": len(rows),
        "image": image_count,
        "text": text_count,
        "high_risk": high_risk_count,
    }
    cleared = request.args.get("cleared") == "1"
    return render_template("history.html", rows=rows, stats=stats, cleared=cleared)
