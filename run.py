"""应用入口：创建 Flask 应用并注册所有蓝图路由。"""

from flask import Flask

from config import Config
from routes.app_chat_routes import app_chat_bp
from routes.app_relax_routes import app_relax_bp
from routes.app_routes import app_bp
from routes.audio_routes import audio_bp
from routes.camera_routes import camera_bp
from routes.history_routes import history_bp
from routes.home_routes import home_bp
from routes.image_routes import image_bp
from routes.multimodal_routes import multimodal_bp
from routes.report_routes import report_bp
from routes.text_routes import text_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(home_bp)
    app.register_blueprint(app_bp)
    app.register_blueprint(app_chat_bp)
    app.register_blueprint(app_relax_bp)
    app.register_blueprint(audio_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(image_bp)
    app.register_blueprint(multimodal_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(text_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)
