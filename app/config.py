import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, '..', 'instance', 'testing.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEFAULT_TIME_LIMIT = 1
    DEFAULT_MEMORY_LIMIT = 256

    PYTHON_EXEC = os.environ.get('PYTHON_EXEC', 'python')
    CPP_COMPILER = os.environ.get('CPP_COMPILER', 'g++')

    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    TESTS_FOLDER = os.path.join(BASE_DIR, '..', 'tests_files')

    PASSWORD_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%&*?'
    PASSWORD_LENGTH = 6

    TEACHER_USERNAME = os.environ.get('TEACHER_USERNAME', 'admin')
    TEACHER_PASSWORD = os.environ.get('TEACHER_PASSWORD', 'admin123')


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
