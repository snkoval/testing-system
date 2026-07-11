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

        if 'section' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                conn.execute(text('''
                    CREATE TABLE section (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(200) NOT NULL,
                        order_number INTEGER NOT NULL
                    )
                '''))
                conn.commit()
            print('Таблица section создана.')
        else:
            print('Таблица section уже существует.')

        if 'group_section' not in inspector.get_table_names():
            with db.engine.connect() as conn:
                conn.execute(text('''
                    CREATE TABLE group_section (
                        group_id INTEGER NOT NULL,
                        section_id INTEGER NOT NULL,
                        PRIMARY KEY(group_id, section_id),
                        FOREIGN KEY(group_id) REFERENCES "group" (id),
                        FOREIGN KEY(section_id) REFERENCES section (id)
                    )
                '''))
                conn.commit()
            print('Таблица group_section создана.')
        else:
            print('Таблица group_section уже существует.')

        columns = [c['name'] for c in inspector.get_columns('lesson')]
        if 'section_id' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE lesson ADD COLUMN section_id INTEGER REFERENCES section (id)'
                ))
                conn.commit()
            print('Колонка section_id добавлена в lesson.')
        else:
            print('Колонка section_id уже существует.')

        print('Миграция завершена.')


if __name__ == '__main__':
    migrate()
