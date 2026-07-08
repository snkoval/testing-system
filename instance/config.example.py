# Конфигурация конкретного сервера.
# Скопируйте этот файл: cp instance/config.example.py instance/config.py
# и отредактируйте значения под свою среду.

import os

# Секретный ключ для подписи сессий (ОБЯЗАТЕЛЬНО замените в production).
# Сгенерировать: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.environ.get('SECRET_KEY', 'replace-this-with-random-secret')

# База данных SQLite (абсолютный путь).
_SQLITE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_SQLITE_DIR, 'testing.db')

# Лимиты по умолчанию для задач.
DEFAULT_TIME_LIMIT = 1
DEFAULT_MEMORY_LIMIT = 256

# Пути к интерпретаторам и компиляторам.
PYTHON_EXEC = os.environ.get('PYTHON_EXEC', 'python')
CPP_COMPILER = os.environ.get('CPP_COMPILER', 'g++')

# Учётные данные учителя (создаётся init_db.py).
TEACHER_USERNAME = os.environ.get('TEACHER_USERNAME', 'admin')
TEACHER_PASSWORD = os.environ.get('TEACHER_PASSWORD', 'change-this-password')

# Включить CSRF-защиту (рекомендуется в production).
CSRF_PROTECTION_ENABLED = True
