"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from modules.report_generator import generate_report_data, save_report_html


report_bp = Blueprint("report", __name__)


@report_bp.route("/report", methods=["GET", "POST"])
def report_page():
    csv_path = Path(current_app.root_path) / "data" / "records.csv"
    reports_dir = Path(current_app.root_path) / "reports"
    saved_filename = None

    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "refresh":
            return redirect(url_for("report.report_page"))
        if action == "save":
            report_data = generate_report_data(csv_path)
            if report_data["has_data"]:
                saved_filename, _ = save_report_html(report_data, reports_dir)

    report_data = generate_report_data(csv_path)
    return render_template(
        "report.html",
        report_data=report_data,
        saved_filename=saved_filename,
    )
