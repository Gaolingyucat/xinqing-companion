"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from pathlib import Path

from flask import Blueprint, current_app, render_template

from modules.multimodal_fusion import fuse_multimodal


multimodal_bp = Blueprint("multimodal", __name__)


@multimodal_bp.route("/multimodal")
def multimodal_page():
    csv_path = Path(current_app.root_path) / "data" / "records.csv"
    fusion = fuse_multimodal(csv_path)
    return render_template("multimodal.html", fusion=fusion)
