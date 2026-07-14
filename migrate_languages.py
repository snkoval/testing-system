import os
import sys

from app import create_app, db
from app.config import Config


def migrate():
    config = Config()
    app = create_app(config)

    with app.app_context():
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)

        columns = [c['name'] for c in inspector.get_columns('lesson')]
        if 'allowed_languages' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE lesson ADD COLUMN allowed_languages VARCHAR(20) NOT NULL DEFAULT 'python,cpp'"
                ))
                conn.commit()
            print('Колонка lesson.allowed_languages добавлена.')
        else:
            print('Колонка lesson.allowed_languages уже существует.')


if __name__ == '__main__':
    migrate()
