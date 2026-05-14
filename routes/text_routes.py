"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from pathlib import Path

from flask import Blueprint, current_app, render_template, request

from modules.record_manager import add_record
from modules.risk_engine import evaluate_text_risk
from modules.suggestion_engine import generate_suggestion
from modules.text_emotion import analyze_text


text_bp = Blueprint("text", __name__)


@text_bp.route("/text", methods=["GET", "POST"])
def text_page():
    error_message = None
    result = None
    input_text = ""

    if request.method == "POST":
        input_text = request.form.get("input_text", "").strip()
        if not input_text:
            error_message = "请输入要分析的中文文本内容。"
        else:
            text_result = analyze_text(input_text)
            risk_result = evaluate_text_risk(
                text_emotion=text_result["emotion"], score=text_result["text_score"]
            )
            suggestion = generate_suggestion(
                input_type="text",
                emotion_cn=text_result["emotion_cn"],
                risk_level=risk_result["risk_level"],
                risk_score=risk_result["risk_score"],
            )
            confidence = text_result["text_score"] / 100
            add_record(
                csv_path=Path(current_app.root_path) / "data" / "records.csv",
                input_type="text",
                emotion=text_result["emotion"],
                emotion_cn=text_result["emotion_cn"],
                confidence=confidence,
                risk_score=risk_result["risk_score"],
                risk_level=risk_result["risk_level"],
                suggestion=suggestion,
                file_path="text_input",
            )
            result = {
                "emotion": text_result["emotion"],
                "emotion_cn": text_result["emotion_cn"],
                "matched_keywords": text_result["matched_keywords"],
                "text_score": text_result["text_score"],
                "risk_score": risk_result["risk_score"],
                "risk_level": risk_result["risk_level"],
                "reason": risk_result["reason"],
                "suggestion": suggestion,
            }

    return render_template(
        "text.html",
        error_message=error_message,
        result=result,
        input_text=input_text,
    )
