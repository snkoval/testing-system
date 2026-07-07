import os

from flask import Flask, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy

from app.config import Config, TestConfig
from app.utils import is_lesson_accessible, generate_csrf_token, validate_csrf_token

db = SQLAlchemy()


def create_app(config_class=Config):
    instance_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'instance')
    app = Flask(__name__, instance_path=instance_path,
                instance_relative_config=True)
    app.config.from_object(config_class)
    app.config.from_pyfile('config.py', silent=True)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    @app.context_processor
    def inject_globals():
        return {
            'is_lesson_accessible': is_lesson_accessible,
            'csrf_token': generate_csrf_token,
        }

    if app.config.get('CSRF_PROTECTION_ENABLED', False):
        @app.before_request
        def _check_csrf():
            if request.method in ('POST', 'PUT', 'DELETE'):
                validate_csrf_token()

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.teacher import bp as teacher_bp
    app.register_blueprint(teacher_bp)

    from app.student import bp as student_bp
    app.register_blueprint(student_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    @app.route('/')
    def index():
        return render_template('base.html')

    return app
