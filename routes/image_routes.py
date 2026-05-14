"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from modules.image_emotion import analyze_image
from modules.record_manager import add_record
from modules.risk_engine import evaluate_image_risk
from modules.suggestion_engine import generate_suggestion


image_bp = Blueprint("image", __name__)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def _is_allowed_file(filename):
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


@image_bp.route("/uploads/images/<path:filename>")
def serve_uploaded_image(filename):
    directory = Path(current_app.root_path) / "uploads" / "images"
    return send_from_directory(str(directory), filename)


@image_bp.route("/image", methods=["GET", "POST"])
def image_page():
    error_message = None
    result = None
    image_url = None
    uploaded_filename = None

    if request.method == "POST":
        image_file = request.files.get("image_file")
        if image_file is None:
            error_message = "未检测到上传文件，请重新选择图片。"
        elif image_file.filename == "":
            error_message = "未选择文件，请先选择 jpg、jpeg 或 png 图片。"
        elif "." not in image_file.filename:
            error_message = "文件格式不支持，请上传带扩展名的 jpg、jpeg 或 png 图片。"
        elif not _is_allowed_file(image_file.filename):
            error_message = "文件格式不支持，仅支持 jpg、jpeg、png。"
        else:
            safe_name = secure_filename(image_file.filename)
            if "." not in safe_name:
                error_message = "文件名无有效扩展名，请上传 jpg、jpeg 或 png 图片。"
                return render_template(
                    "image.html",
                    error_message=error_message,
                    result=result,
                    image_url=image_url,
                    uploaded_filename=uploaded_filename,
                )

            base_name = Path(safe_name).stem
            extension = Path(safe_name).suffix.lower()
            if extension not in {".jpg", ".jpeg", ".png"}:
                error_message = "文件格式不支持，仅支持 jpg、jpeg、png。"
                return render_template(
                    "image.html",
                    error_message=error_message,
                    result=result,
                    image_url=image_url,
                    uploaded_filename=uploaded_filename,
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_name = f"{timestamp}_{base_name}{extension}"
            upload_dir = Path(current_app.root_path) / "uploads" / "images"
            upload_dir.mkdir(parents=True, exist_ok=True)
            save_path = upload_dir / final_name
            try:
                image_file.save(save_path)
            except OSError:
                error_message = "文件保存失败，请检查目录权限后重试。"
            else:
                uploaded_filename = final_name
                emotion_result = analyze_image(str(save_path))
                risk_result = evaluate_image_risk(
                    emotion_result["emotion"], emotion_result["confidence"]
                )
                suggestion = generate_suggestion(
                    input_type="图像",
                    emotion_cn=emotion_result["emotion_cn"],
                    risk_level=risk_result["risk_level"],
                    risk_score=risk_result["risk_score"],
                )
                add_record(
                    csv_path=Path(current_app.root_path) / "data" / "records.csv",
                    input_type="image",
                    emotion=emotion_result["emotion"],
                    emotion_cn=emotion_result["emotion_cn"],
                    confidence=emotion_result["confidence"],
                    risk_score=risk_result["risk_score"],
                    risk_level=risk_result["risk_level"],
                    suggestion=suggestion,
                    file_path=str(save_path),
                )
                image_url = url_for("image.serve_uploaded_image", filename=final_name)
                result = {
                    "emotion": emotion_result["emotion"],
                    "emotion_cn": emotion_result["emotion_cn"],
                    "confidence": emotion_result["confidence"],
                    "source": emotion_result.get("source", "mock"),
                    "warning": emotion_result.get("warning", ""),
                    "risk_score": risk_result["risk_score"],
                    "risk_level": risk_result["risk_level"],
                    "suggestion": suggestion,
                }

    return render_template(
        "image.html",
        error_message=error_message,
        result=result,
        image_url=image_url,
        uploaded_filename=uploaded_filename,
    )
