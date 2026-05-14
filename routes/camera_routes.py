"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from flask import Blueprint, Response, jsonify, render_template, url_for

from modules.camera_service import camera_service


camera_bp = Blueprint("camera", __name__)


@camera_bp.route("/camera")
def camera_page():
    return render_template(
        "camera.html",
        video_feed_url=url_for("camera.video_feed"),
        status_url=url_for("camera.camera_status"),
    )


@camera_bp.route("/camera/video_feed")
def video_feed():
    return Response(
        camera_service.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.route("/camera/status")
def camera_status():
    return jsonify(camera_service.get_status())
