"""路由文件：负责处理页面访问与接口请求，并组织业务模块返回结果。"""

from flask import Blueprint, render_template


app_relax_bp = Blueprint("app_relax", __name__)


@app_relax_bp.route("/app/relax")
def app_relax_page():
    return render_template("app_relax.html", nav_active="relax")


@app_relax_bp.route("/app/relax/breath")
def app_breath_page():
    return render_template("app_breath.html", nav_active="relax")


@app_relax_bp.route("/app/relax/bubble")
def app_bubble_page():
    return render_template("app_bubble.html", nav_active="relax")


@app_relax_bp.route("/app/relax/focus")
def app_focus_page():
    return render_template("app_focus.html", nav_active="relax")


@app_relax_bp.route("/app/relax/mood_game")
def app_mood_game_page():
    return render_template("app_mood_game.html", nav_active="relax")
