import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from app.config import Config, TestConfig

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.teacher import bp as teacher_bp
    app.register_blueprint(teacher_bp)

    from app.student import bp as student_bp
    app.register_blueprint(student_bp)

    @app.route('/')
    def index():
        return render_template('base.html')

    return app
