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

        columns = [c['name'] for c in inspector.get_columns('task')]
        if 'show_examples' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE task ADD COLUMN show_examples INTEGER NOT NULL DEFAULT 2"
                ))
                conn.commit()
            print('Колонка task.show_examples добавлена.')
        else:
            print('Колонка task.show_examples уже существует.')


if __name__ == '__main__':
    migrate()
