"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename

from modules.audio_emotion import analyze_audio_file
from modules.record_manager import add_record
from modules.risk_engine import evaluate_audio_risk
from modules.suggestion_engine import generate_suggestion


audio_bp = Blueprint("audio", __name__)
ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "webm"}


def _is_allowed_file(filename):
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def _save_upload(file_storage, prefix):
    safe_name = secure_filename(file_storage.filename or "")
    if not safe_name:
        raise ValueError("文件名无效，请重新上传。")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{prefix}_{timestamp}_{safe_name}"
    upload_dir = Path(current_app.root_path) / "uploads" / "audio"
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / final_name
    file_storage.save(save_path)
    return final_name, save_path


def _build_analysis_result(save_path):
    audio_result = analyze_audio_file(str(save_path))
    risk_result = evaluate_audio_risk(audio_result["emotion"], audio_result["audio_score"])
    suggestion = generate_suggestion(
        input_type="audio",
        emotion_cn=audio_result["emotion_cn"],
        risk_level=risk_result["risk_level"],
        risk_score=risk_result["risk_score"],
    )

    add_record(
        csv_path=Path(current_app.root_path) / "data" / "records.csv",
        input_type="audio",
        emotion=audio_result["emotion"],
        emotion_cn=audio_result["emotion_cn"],
        confidence=audio_result["confidence"],
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
        suggestion=suggestion,
        file_path=str(save_path),
    )

    return {
        "emotion": audio_result["emotion"],
        "emotion_cn": audio_result["emotion_cn"],
        "confidence": audio_result["confidence"],
        "audio_score": audio_result["audio_score"],
        "features": audio_result["features"],
        "warning": audio_result.get("warning", ""),
        "risk_score": risk_result["risk_score"],
        "risk_level": risk_result["risk_level"],
        "risk_reason": risk_result["reason"],
        "suggestion": suggestion,
    }


@audio_bp.route("/audio", methods=["GET", "POST"])
def audio_page():
    upload_result = None
    uploaded_filename = None
    error_message = None

    if request.method == "POST":
        audio_file = request.files.get("audio_file")
        if audio_file is None:
            error_message = "未检测到上传文件，请重新选择音频文件。"
        elif audio_file.filename == "":
            error_message = "未选择文件，请先选择 wav 音频文件。"
        elif not _is_allowed_file(audio_file.filename):
            error_message = "文件格式不支持，仅支持 wav、mp3、m4a、webm。"
        else:
            extension = audio_file.filename.rsplit(".", 1)[1].lower()
            if extension in {"mp3", "m4a", "webm"}:
                error_message = "当前版本建议使用网页录音或 wav 文件。"
            else:
                try:
                    uploaded_filename, save_path = _save_upload(audio_file, "upload")
                    upload_result = _build_analysis_result(save_path)
                except OSError:
                    error_message = "音频保存失败，请检查目录权限后重试。"
                except Exception as e:
                    error_message = f"音频读取或分析失败：{e}"

    return render_template(
        "audio.html",
        upload_result=upload_result,
        uploaded_filename=uploaded_filename,
        error_message=error_message,
    )


@audio_bp.route("/audio/record", methods=["POST"])
def audio_record():
    audio_blob = request.files.get("audio_blob")
    if audio_blob is None:
        return jsonify({"ok": False, "error": "未接收到录音数据。"}), 400

    original_name = audio_blob.filename or "record.webm"
    if "." not in original_name:
        original_name = "record.webm"
    ext = original_name.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "error": "录音格式不支持，请使用浏览器默认录音格式。"}), 400

    try:
        audio_blob.filename = original_name
        saved_name, save_path = _save_upload(audio_blob, "record")
        result = _build_analysis_result(save_path)
        result["filename"] = saved_name
        return jsonify({"ok": True, "result": result})
    except OSError:
        return jsonify({"ok": False, "error": "录音文件保存失败，请稍后重试。"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": f"录音分析失败：{e}"}), 500
